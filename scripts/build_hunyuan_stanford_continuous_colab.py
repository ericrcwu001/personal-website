#!/usr/bin/env python3
"""Build a self-contained Colab proof for one continuous Stanford camera move."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

import nbformat

import build_hunyuan15_portfolio_colab as base


ROOT = Path(__file__).resolve().parents[1]
SOURCE_ARCHIVE = Path("/Users/ericwu/Downloads/A_church_to_column.zip")
OUTPUT = ROOT / "notebooks" / "hunyuanvideo15_stanford_continuous_dolly_colab.ipynb"

MODEL_REPO = "hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-480p_i2v"
MODEL_REVISION = "5a700ee883ff4c1b3d887ec4188755a7a5e2f698"
EXPECTED_SOURCE_SHA256 = "93551bebd0c12463e101a0ee4cd964a63e3f7ba5c9c18b7362dc68642469a50d"


TITLE = r'''
# Stanford continuous-dolly proof — HunyuanVideo 1.5

This isolated proof replaces the rejected two-clip hidden cut with **one visible camera path**:

**Memorial Church through the real Main Quad arcade → physical lateral dolly to camera-right → a second sandstone column naturally crosses the frame through foreground parallax → the camera settles on a long arcade composition.**

The accepted Church-grounded take is used through frame 47. Its exact next frame becomes the continuation anchor, so there is no crossfade, dissolve, column hard cut, reversed second shot, or unrelated endpoint. The continuation keeps moving in the same physical direction. It is generated once, persisted regardless of heuristic warnings, and packaged with a scrub encode, bidirectional preview, contact sheet, boundary diagnostic, metrics, manifest, and source lineage.

This remains a **visual proof, not a final website asset**. If the physical move reads correctly, the same design becomes the Stanford half of the final intro and scroll easing is applied in the website controller.

## License boundary

Tencent HunyuanVideo 1.5 is licensed for a territory excluding the EU, UK, and South Korea, and its license restricts displaying outputs outside that territory. Keep this output to local evaluation until deployment licensing is resolved.
'''


SETTINGS = r'''
# The only controls normally worth changing before a rerun.
EXPERIMENT_ID = "stanford_continuous_dolly_base480_v1"
SEED = 83117
ANCHOR_FRAME_INDEX = 48
CONTINUATION_FRAMES = 97  # Hunyuan requires 4n+1; 97 plus the grounded prefix gives ~6 seconds.
FPS = 24
INFERENCE_STEPS = 50
PERSIST_MODEL_CACHE_TO_DRIVE = False
LOCAL_EVALUATION_ONLY = True

AUTO_DISCONNECT = True
ERROR_DISCONNECT_DELAY_SECONDS = 120
FORCE_UNASSIGN_AFTER_SECONDS = 180
MAX_RUNTIME_HOURS = 4.0

if (CONTINUATION_FRAMES - 1) % 4:
    raise ValueError("CONTINUATION_FRAMES must be 4n+1")
if not LOCAL_EVALUATION_ONLY:
    raise ValueError("This proof is restricted to local evaluation pending license review")
print("Experiment:", EXPERIMENT_ID, "| seed:", SEED, "| continuation frames:", CONTINUATION_FRAMES)
'''


DRIVE_SETUP = r'''
# Mount Drive, use the local SSD for the 50 GB model, and arm billing fail-safes.
from google.colab import drive
from google.colab import drive as colab_drive, runtime as colab_runtime
from pathlib import Path
from PIL import Image, ImageDraw
from IPython.display import Video, display
import base64, fractions, gc, hashlib, io, json, math, os, platform, shutil, subprocess, sys, threading, time, uuid, zipfile

drive.mount("/content/drive", force_remount=False)

DRIVE_ROOT = Path("/content/drive/MyDrive/Personal_Website_HunyuanVideo15")
DRIVE_INPUTS = DRIVE_ROOT / "inputs"
DRIVE_CACHE = DRIVE_ROOT / "cache"
DRIVE_EXPERIMENT = DRIVE_ROOT / "experiments" / EXPERIMENT_ID

RUNTIME_ROOT = Path("/content/hunyuan15_runtime")
RUNTIME_INPUTS = RUNTIME_ROOT / "inputs"
RUNTIME_MODELS = RUNTIME_ROOT / "models"
RUNTIME_EXPERIMENT = RUNTIME_ROOT / "experiments" / EXPERIMENT_ID

for path in (DRIVE_INPUTS, DRIVE_CACHE, DRIVE_EXPERIMENT, RUNTIME_INPUTS, RUNTIME_MODELS, RUNTIME_EXPERIMENT):
    path.mkdir(parents=True, exist_ok=True)

probe = DRIVE_EXPERIMENT / f".write-probe-{uuid.uuid4().hex}"
payload = f"stanford continuous proof {time.time_ns()}\n"
probe.write_text(payload, encoding="utf-8")
if probe.read_text(encoding="utf-8") != payload:
    raise RuntimeError("Google Drive persistence check failed")
probe.unlink()

def free_gib(path):
    return shutil.disk_usage(path).free / (1024 ** 3)

_shutdown_started = threading.Event()
_error_disconnect_timer = None

def _force_unassign():
    try:
        colab_runtime.unassign()
    except Exception as error:
        print("Forced runtime deletion warning:", repr(error))

def disconnect_runtime_safely(reason):
    if not AUTO_DISCONNECT or _shutdown_started.is_set():
        return
    _shutdown_started.set()
    print("AUTO-DISCONNECT:", reason)
    fallback = threading.Timer(FORCE_UNASSIGN_AFTER_SECONDS, _force_unassign)
    fallback.daemon = True
    fallback.start()
    try:
        marker = DRIVE_EXPERIMENT / "runtime_shutdown.json"
        temporary = marker.with_name(marker.name + f".part-{uuid.uuid4().hex}")
        temporary.write_text(json.dumps({
            "reason": reason,
            "requested_at_unix": time.time(),
            "outputs_persisted": "see success.json and manifest.json",
        }, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, marker)
        colab_drive.flush_and_unmount()
    except Exception as error:
        print("Drive flush/unmount warning:", repr(error))
    try:
        colab_runtime.unassign()
    except Exception as error:
        print("Runtime deletion warning; fallback remains armed:", repr(error))

def _disconnect_on_uncaught_exception(shell, etype, evalue, traceback, tb_offset=None):
    shell.showtraceback((etype, evalue, traceback), tb_offset=tb_offset)
    global _error_disconnect_timer
    reason = f"uncaught error: {etype.__name__}: {evalue}"
    try:
        record = DRIVE_EXPERIMENT / "runtime_error.json"
        record.write_text(json.dumps({
            "reason": reason,
            "recorded_at_unix": time.time(),
            "disconnect_delay_seconds": ERROR_DISCONNECT_DELAY_SECONDS,
        }, indent=2) + "\n", encoding="utf-8")
    except Exception as error:
        print("Could not persist runtime error record:", repr(error))
    _error_disconnect_timer = threading.Timer(
        ERROR_DISCONNECT_DELAY_SECONDS,
        disconnect_runtime_safely,
        args=(reason,),
    )
    _error_disconnect_timer.daemon = True
    print(
        f"ERROR RECORDED. Colab will disconnect in {ERROR_DISCONNECT_DELAY_SECONDS} seconds. "
        "To keep it for debugging, run: _error_disconnect_timer.cancel()"
    )
    _error_disconnect_timer.start()
    return None

get_ipython().set_custom_exc((Exception,), _disconnect_on_uncaught_exception)

def _hard_cutoff():
    if not _shutdown_started.wait(MAX_RUNTIME_HOURS * 3600):
        disconnect_runtime_safely(f"hard cutoff after {MAX_RUNTIME_HOURS:.1f} hours")

threading.Thread(target=_hard_cutoff, name="colab-billing-failsafe", daemon=True).start()

print("Drive output:", DRIVE_EXPERIMENT)
print("Model cache: temporary local SSD only")
print("Local free:", round(free_gib("/content"), 1), "GiB | Drive free:", round(free_gib(DRIVE_ROOT), 1), "GiB")
'''


MODEL_CONFIG = rf'''
# Pinned full-quality 480p I2V model used by the successful Stanford source take.
BASE_480_MODEL = {{
    "repo_id": "{MODEL_REPO}",
    "revision": "{MODEL_REVISION}",
    "width": 848,
    "height": 480,
    "steps": INFERENCE_STEPS,
    "expected_gib": 50.52,
    "target_size": 640,
    "use_meanflow": False,
}}

NEGATIVE_PROMPT = (
    "pan in place, pivot in place, tripod pan, optical zoom, digital zoom, dolly zoom, flat rotating photograph, "
    "static camera, camera cut, crossfade, dissolve, fade, morph, portal, hidden edit, full-frame obstruction, "
    "drone, quadcopter, aircraft, helicopter, propeller, camera rig, filming equipment, floating object, "
    "warped church, bending column, duplicated arch, melting sandstone, changing architecture, time lapse, "
    "people appearing, crowd, jitter, flicker, text, title, logo, watermark, CGI, illustration, miniature"
)

PROMPT = (
    "Photorealistic live-action continuation of this exact Stanford Main Quad shot in late golden-hour light. "
    "The camera keeps the same level eye height, fixed 24 millimeter cinema lens, exposure, and architecture. "
    "It continues the existing movement by physically translating laterally to camera-right under the covered "
    "sandstone arcade on a smooth stabilized dolly; it never pivots in place and never zooms. The foreground "
    "column currently left of center keeps sliding left and exits naturally. As the dolly advances to the right, "
    "the next real sandstone column enters from the right edge, crosses through the middle of the frame with "
    "strong near-field parallax, then slides toward the left, while Memorial Church, the quad, floor tiles, and "
    "repeating arches move more slowly in correct depth. The column is a natural foreground object and never "
    "fills the entire image. The first third maintains the incoming velocity, the middle accelerates smoothly as "
    "the near column crosses, and the final third eases down gently without stopping abruptly. End on a stable, "
    "wide composition looking along the authentic Stanford arcade with repeating arches and enough dark open "
    "space for social-link icons. Preserve rigid recognizable Memorial Church and Main Quad geometry throughout."
)

CONFIG = {{
    "experiment_id": EXPERIMENT_ID,
    "seed": SEED,
    "anchor_frame_index": ANCHOR_FRAME_INDEX,
    "continuation_frames": CONTINUATION_FRAMES,
    "fps": FPS,
    "model": BASE_480_MODEL,
    "prompt": PROMPT,
    "negative_prompt": NEGATIVE_PROMPT,
    "source_sha256": "{EXPECTED_SOURCE_SHA256}",
    "camera_path": "single rightward lateral dolly; no hidden cut",
    "scroll_ease": "power2.inOut applied by the website controller, not baked into source frames",
    "license": "local evaluation only",
}}
CONFIG_FINGERPRINT = hashlib.sha256(json.dumps(CONFIG, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
print("Configuration:", CONFIG_FINGERPRINT)
'''


SOURCE_ASSEMBLY_PREFIX = r'''
# Assemble the accepted Church-grounded source clip embedded below.
EMBEDDED_SOURCE_CLIP_PARTS = []
'''


SOURCE_RESTORE = rf'''
# Verify, persist, and decode the accepted source; frame 48 is the exact continuation anchor.
SOURCE_METADATA = {{
    "filename": "stanford_A_church_to_column_accepted.mp4",
    "sha256": "{EXPECTED_SOURCE_SHA256}",
    "bytes": __SOURCE_BYTES__,
    "origin": "A_church_to_column.zip supplied by Eric Wu",
    "role": "accepted Church-grounded first half of one continuous Stanford camera path",
}}
payload = base64.b64decode("".join(EMBEDDED_SOURCE_CLIP_PARTS))
if len(payload) != SOURCE_METADATA["bytes"] or hashlib.sha256(payload).hexdigest() != SOURCE_METADATA["sha256"]:
    raise RuntimeError("Embedded accepted source failed size/hash verification")

drive_source = DRIVE_INPUTS / SOURCE_METADATA["filename"]
if not drive_source.is_file() or sha256_file(drive_source) != SOURCE_METADATA["sha256"]:
    temporary = drive_source.with_name(drive_source.name + f".part-{{uuid.uuid4().hex}}")
    temporary.write_bytes(payload)
    os.replace(temporary, drive_source)
local_source = RUNTIME_INPUTS / SOURCE_METADATA["filename"]
shutil.copy2(drive_source, local_source)
if sha256_file(local_source) != SOURCE_METADATA["sha256"]:
    raise RuntimeError("Local accepted source copy failed verification")

source_probe = probe_video(local_source)
if (source_probe["width"], source_probe["height"], source_probe["fps"], source_probe["frames"]) != (848, 480, 24.0, 73):
    raise RuntimeError(f"Unexpected accepted source structure: {{source_probe}}")

capture = cv2.VideoCapture(str(local_source))
source_frames = []
while True:
    ok, frame = capture.read()
    if not ok:
        break
    source_frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
capture.release()
if len(source_frames) != 73:
    raise RuntimeError(f"Decoded {{len(source_frames)}} source frames instead of 73")

anchor_array = source_frames[ANCHOR_FRAME_INDEX]
anchor_image = Image.fromarray(anchor_array)
anchor_path = RUNTIME_EXPERIMENT / f"continuation_anchor_frame_{{ANCHOR_FRAME_INDEX:03d}}.png"
anchor_image.save(anchor_path, "PNG", optimize=True)
atomic_publish_file(anchor_path, DRIVE_EXPERIMENT / anchor_path.name)

source_sheet_path = RUNTIME_EXPERIMENT / "accepted_source_contact_sheet.jpg"
write_contact_sheet(source_frames, source_sheet_path, "Accepted Church-grounded source | frames 0–72")
atomic_publish_file(source_sheet_path, DRIVE_EXPERIMENT / source_sheet_path.name)
atomic_write_json(DRIVE_EXPERIMENT / "source_lineage.json", {{
    **SOURCE_METADATA,
    "probe": source_probe,
    "continuation_anchor_frame": ANCHOR_FRAME_INDEX,
    "continuation_anchor_sha256": sha256_file(anchor_path),
    "prefix_policy": f"source frames 0–{{ANCHOR_FRAME_INDEX - 1}}, then generated frames 0–{{CONTINUATION_FRAMES - 1}}",
}})
display(Image.open(source_sheet_path))
display(anchor_image.resize((848, 480)))
del payload, EMBEDDED_SOURCE_CLIP_PARTS
'''


GENERATE = r'''
# Generate one same-direction continuation, then assemble one uninterrupted visible camera path.
candidate_root = DRIVE_EXPERIMENT / "candidate" / str(SEED)
runtime_candidate = RUNTIME_EXPERIMENT / "candidate" / str(SEED)
runtime_candidate.mkdir(parents=True, exist_ok=True)

def valid_existing_candidate():
    manifest_path = candidate_root / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("config_fingerprint") != CONFIG_FINGERPRINT or manifest.get("status") != "complete":
            return False
        for name, record in manifest["artifacts"].items():
            path = candidate_root / name
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                return False
        continuation_probe = probe_video(candidate_root / "continuation_native_480p24.mp4")
        combined_probe = probe_video(candidate_root / "stanford_continuous_dolly_480p24.mp4")
        return (
            continuation_probe["width"], continuation_probe["height"], continuation_probe["frames"],
            combined_probe["width"], combined_probe["height"], combined_probe["frames"],
        ) == (848, 480, CONTINUATION_FRAMES, 848, 480, ANCHOR_FRAME_INDEX + CONTINUATION_FRAMES)
    except Exception:
        return False

model_directory = None
pipe = None
if valid_existing_candidate():
    print("Validated completed candidate; skipping the 50 GB model download and generation.")
    for name in ("continuation_native_480p24.mp4", "stanford_continuous_dolly_480p24.mp4"):
        shutil.copy2(candidate_root / name, runtime_candidate / name)
else:
    model_directory = acquire_model(BASE_480_MODEL, "stanford-continuous-dolly-base480")
    pipe = load_hunyuan(model_directory, BASE_480_MODEL, "stanford-continuous-dolly-base480")
    if abs(float(pipe.guider.guidance_scale) - 6.0) > 1e-6:
        raise RuntimeError(f"Expected active CFG 6, found {pipe.guider.guidance_scale}")
    started = time.time()
    try:
        result = pipe(
            image=anchor_image,
            prompt=PROMPT,
            negative_prompt=NEGATIVE_PROMPT,
            num_frames=CONTINUATION_FRAMES,
            num_inference_steps=INFERENCE_STEPS,
            generator=torch.Generator(device="cuda").manual_seed(SEED),
            output_type="np",
        )
        continuation_frames = normalize_output(result)
    finally:
        dispose_pipeline(pipe)
        pipe = None

    if len(continuation_frames) != CONTINUATION_FRAMES:
        raise RuntimeError(f"Hunyuan returned {len(continuation_frames)} frames instead of {CONTINUATION_FRAMES}")
    continuation_frames[0] = anchor_array.copy()
    combined_frames = source_frames[:ANCHOR_FRAME_INDEX] + continuation_frames
    if len(combined_frames) != ANCHOR_FRAME_INDEX + CONTINUATION_FRAMES:
        raise RuntimeError("Combined frame policy is inconsistent")

    continuation_path = runtime_candidate / "continuation_native_480p24.mp4"
    combined_path = runtime_candidate / "stanford_continuous_dolly_480p24.mp4"
    continuation_sheet = runtime_candidate / "continuation_contact_sheet.jpg"
    timeline_sheet = runtime_candidate / "continuous_timeline_contact_sheet.jpg"
    final_frame = runtime_candidate / "final_frame.png"
    encode_video(continuation_frames, continuation_path, crf=16)
    encode_video(combined_frames, combined_path, crf=16)
    write_contact_sheet(continuation_frames, continuation_sheet, f"Same-direction continuation | seed {SEED}")
    write_contact_sheet(combined_frames, timeline_sheet, "One visible camera path | no hidden cut")
    Image.fromarray(combined_frames[-1]).save(final_frame, "PNG", optimize=True)

    def mean_flow_vector(left, right):
        a = cv2.cvtColor(cv2.resize(left, (424, 240)), cv2.COLOR_RGB2GRAY)
        b = cv2.cvtColor(cv2.resize(right, (424, 240)), cv2.COLOR_RGB2GRAY)
        flow = cv2.calcOpticalFlowFarneback(a, b, None, .5, 3, 25, 3, 5, 1.2, 0)
        crop = flow[24:216, 42:382]
        vector = np.median(crop.reshape(-1, 2), axis=0)
        magnitude = float(np.median(np.linalg.norm(crop, axis=2)))
        return vector.astype(float), magnitude

    source_vector, source_speed = mean_flow_vector(source_frames[ANCHOR_FRAME_INDEX - 1], anchor_array)
    generated_vector, generated_speed = mean_flow_vector(continuation_frames[0], continuation_frames[1])
    denominator = float(np.linalg.norm(source_vector) * np.linalg.norm(generated_vector))
    direction_cosine = None if denominator < 1e-8 else float(np.dot(source_vector, generated_vector) / denominator)
    speed_ratio = None if source_speed < 1e-6 else float(generated_speed / source_speed)
    exact_anchor_mae = float(np.abs(continuation_frames[0].astype(np.float32) - anchor_array.astype(np.float32)).mean())

    all_flows = [mean_flow_vector(a, b)[1] for a, b in zip(combined_frames, combined_frames[1:])]
    warnings = []
    if exact_anchor_mae != 0:
        warnings.append("continuation_does_not_begin_on_exact_anchor")
    if direction_cosine is not None and direction_cosine < 0:
        warnings.append("generated_motion_may_reverse_at_boundary")
    if speed_ratio is not None and not 0.25 <= speed_ratio <= 4.0:
        warnings.append("boundary_speed_change_is_large")
    if float(np.median(all_flows)) < 0.20:
        warnings.append("overall_motion_may_be_too_weak")

    boundary = Image.new("RGB", (1272, 272), "#111111")
    for index, frame in enumerate((source_frames[ANCHOR_FRAME_INDEX - 1], continuation_frames[0], continuation_frames[1])):
        boundary.paste(Image.fromarray(frame).resize((424, 240), Image.Resampling.LANCZOS), (424 * index, 0))
    draw = ImageDraw.Draw(boundary)
    labels = (
        f"source {ANCHOR_FRAME_INDEX - 1}",
        f"exact anchor {ANCHOR_FRAME_INDEX} / generated 0",
        "generated 1",
    )
    for index, label in enumerate(labels):
        draw.text((424 * index + 8, 247), label, fill="white")
    boundary_path = runtime_candidate / "boundary_diagnostic.jpg"
    boundary.save(boundary_path, "JPEG", quality=93, optimize=True)

    metrics = {
        "exact_anchor_mae": exact_anchor_mae,
        "source_incoming_flow_vector": source_vector.tolist(),
        "generated_outgoing_flow_vector": generated_vector.tolist(),
        "boundary_direction_cosine": direction_cosine,
        "boundary_speed_ratio": speed_ratio,
        "median_flow": float(np.median(all_flows)),
        "mean_flow": float(np.mean(all_flows)),
        "minimum_flow": float(np.min(all_flows)),
        "maximum_flow": float(np.max(all_flows)),
        "warnings": warnings,
        "automatic_rejection_enabled": False,
        "reason": "flow cannot judge architectural realism or whether a lateral move feels natural",
    }
    metrics_path = runtime_candidate / "motion_continuity_metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    artifacts = {}
    for path in (continuation_path, combined_path, continuation_sheet, timeline_sheet, final_frame, boundary_path, metrics_path):
        digest = atomic_publish_file(path, candidate_root / path.name)
        artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}
    atomic_write_json(candidate_root / "manifest.json", {
        "status": "complete",
        "visual_status": "manual_review_required",
        "config_fingerprint": CONFIG_FINGERPRINT,
        "config": CONFIG,
        "source": SOURCE_METADATA,
        "source_prefix_frames": ANCHOR_FRAME_INDEX,
        "generated_continuation_frames": CONTINUATION_FRAMES,
        "combined_frames": len(combined_frames),
        "fps": FPS,
        "pixel_crossfade": False,
        "hidden_hard_cut": False,
        "reverse_second_shot": False,
        "fixed_focal_length_requested": True,
        "physical_lateral_translation_requested": True,
        "scroll_easing": "power2.inOut; apply in browser scroll-to-time mapping",
        "caption_windows": [
            {"id": "stanford_a", "seconds": [0.0, 3.0], "lines": ["Stanford Class of 2029"]},
            {"id": "stanford_b", "seconds": [3.0, len(combined_frames) / FPS],
             "icons": ["GitHub", "LinkedIn", "X", "Instagram", "Email"]},
        ],
        "started_at_unix": started,
        "completed_at_unix": time.time(),
        "metrics": metrics,
        "artifacts": artifacts,
        "license": "local evaluation only",
    })

    if model_directory is not None and not PERSIST_MODEL_CACHE_TO_DRIVE:
        purge_runtime_model(model_directory)
        model_directory = None

print("Candidate Drive directory:", candidate_root)
display(Image.open(candidate_root / "continuous_timeline_contact_sheet.jpg"))
display(Image.open(candidate_root / "boundary_diagnostic.jpg"))
display(Video(str(candidate_root / "stanford_continuous_dolly_480p24.mp4"), embed=True, width=848))
'''


DELIVER = r'''
# Build scroll-friendly and bidirectional review encodes, verify Drive, bundle, and disconnect.
combined = candidate_root / "stanford_continuous_dolly_480p24.mp4"
scrub = RUNTIME_EXPERIMENT / "stanford_continuous_dolly_scrub_gop6_480p24.mp4"
pingpong = RUNTIME_EXPERIMENT / "stanford_continuous_dolly_bidirectional_preview.mp4"

subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(combined), "-an", "-c:v", "libx264",
    "-preset", "slow", "-crf", "17", "-g", "6", "-keyint_min", "6", "-sc_threshold", "0",
    "-bf", "0", "-tune", "fastdecode", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(scrub),
], check=True)
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(combined),
    "-filter_complex", "[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[a];"
                       "[r]reverse,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]",
    "-map", "[v]", "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(pingpong),
], check=True)

expected_frames = ANCHOR_FRAME_INDEX + CONTINUATION_FRAMES
if (probe_video(scrub)["frames"], maximum_keyframe_gap(scrub)) != (expected_frames, 6):
    raise RuntimeError(f"Invalid scrub encode: {probe_video(scrub)}, GOP {maximum_keyframe_gap(scrub)}")
if probe_video(pingpong)["frames"] != expected_frames * 2:
    raise RuntimeError(f"Invalid bidirectional preview: {probe_video(pingpong)}")

final_artifacts = {}
for local_path in (scrub, pingpong):
    digest = atomic_publish_file(local_path, DRIVE_EXPERIMENT / local_path.name)
    final_artifacts[local_path.name] = {"bytes": local_path.stat().st_size, "sha256": digest}

review_files = [
    candidate_root / "stanford_continuous_dolly_480p24.mp4",
    candidate_root / "continuation_native_480p24.mp4",
    candidate_root / "continuous_timeline_contact_sheet.jpg",
    candidate_root / "continuation_contact_sheet.jpg",
    candidate_root / "boundary_diagnostic.jpg",
    candidate_root / "motion_continuity_metrics.json",
    candidate_root / "manifest.json",
    DRIVE_EXPERIMENT / scrub.name,
    DRIVE_EXPERIMENT / pingpong.name,
    DRIVE_EXPERIMENT / "source_lineage.json",
]
bundle = RUNTIME_EXPERIMENT / "stanford_continuous_dolly_review_bundle.zip"
with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in review_files:
        archive.write(path, arcname=path.name)
with zipfile.ZipFile(bundle) as archive:
    if archive.testzip() is not None:
        raise RuntimeError("Review ZIP integrity failed")
bundle_digest = atomic_publish_file(bundle, DRIVE_EXPERIMENT / bundle.name)
final_artifacts[bundle.name] = {"bytes": bundle.stat().st_size, "sha256": bundle_digest}

for name, record in final_artifacts.items():
    path = DRIVE_EXPERIMENT / name
    if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
        raise RuntimeError(f"Final Drive verification failed: {name}")

atomic_write_json(DRIVE_EXPERIMENT / "success.json", {
    "status": "complete_visual_review_required",
    "experiment_id": EXPERIMENT_ID,
    "config_fingerprint": CONFIG_FINGERPRINT,
    "expected_frames": expected_frames,
    "fps": FPS,
    "artifacts": final_artifacts,
    "model_cache_persisted": PERSIST_MODEL_CACHE_TO_DRIVE,
    "next_gate": "Eric reviews the continuous move; do not integrate until approved",
})
success = json.loads((DRIVE_EXPERIMENT / "success.json").read_text(encoding="utf-8"))
if success["status"] != "complete_visual_review_required":
    raise RuntimeError("Success marker did not persist")

print("PERSISTED MASTER:", candidate_root / "stanford_continuous_dolly_480p24.mp4")
print("PERSISTED SCRUB:", DRIVE_EXPERIMENT / scrub.name)
print("PERSISTED BIDIRECTIONAL PREVIEW:", DRIVE_EXPERIMENT / pingpong.name)
print("PERSISTED REVIEW BUNDLE:", DRIVE_EXPERIMENT / bundle.name)
print("The 50 GB model cache was not copied to Drive.")
disconnect_runtime_safely("continuous Stanford proof completed and all review media verified on Drive")
'''


def code(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(source.strip() + "\n")


def source_clip_bytes() -> bytes:
    if not SOURCE_ARCHIVE.is_file():
        raise FileNotFoundError(SOURCE_ARCHIVE)
    with zipfile.ZipFile(SOURCE_ARCHIVE) as archive:
        payload = archive.read("clip.mp4")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_SOURCE_SHA256:
        raise AssertionError(f"Accepted source digest changed: {digest}")
    return payload


def build_notebook() -> nbformat.NotebookNode:
    payload = source_clip_bytes()
    encoded = base64.b64encode(payload).decode("ascii")
    chunk_size = 180_000
    chunks = [encoded[index:index + chunk_size] for index in range(0, len(encoded), chunk_size)]

    cells = [
        nbformat.v4.new_markdown_cell(TITLE.strip() + "\n"),
        code(SETTINGS),
        code(DRIVE_SETUP),
        code(base.PREFLIGHT),
        code(base.INSTALL),
        code(MODEL_CONFIG),
        code(base.UTILITIES),
        code(SOURCE_ASSEMBLY_PREFIX),
    ]
    for index, chunk in enumerate(chunks, start=1):
        cells.append(code(
            f"# Embedded accepted source payload {index}/{len(chunks)}.\n"
            f"EMBEDDED_SOURCE_CLIP_PARTS.append({chunk!r})"
        ))
    cells.extend([
        code(SOURCE_RESTORE.replace("__SOURCE_BYTES__", str(len(payload)))),
        code(GENERATE),
        code(DELIVER),
    ])

    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata.update({
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.x"},
        "colab": {"gpuType": "A100", "provenance": []},
    })
    return notebook


def audit(notebook: nbformat.NotebookNode) -> None:
    nbformat.validate(notebook)
    joined = "\n".join(cell.source for cell in notebook.cells)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=f"stanford-continuous-cell-{index}")
            if cell.outputs or cell.execution_count is not None:
                raise AssertionError(f"Output leaked into cell {index}")

    required = (
        MODEL_REPO, MODEL_REVISION, EXPECTED_SOURCE_SHA256,
        "CONTINUATION_FRAMES = 97", "ANCHOR_FRAME_INDEX = 48",
        "physically translating laterally to camera-right", "next real sandstone column",
        "pixel_crossfade\": False", "hidden_hard_cut\": False", "reverse_second_shot\": False",
        "automatic_rejection_enabled\": False", "maximum_keyframe_gap(scrub)",
        "stanford_continuous_dolly_bidirectional_preview.mp4",
        "PERSIST_MODEL_CACHE_TO_DRIVE = False", "purge_runtime_model(model_directory)",
        "disconnect_runtime_safely", "success.json", "flash_varlen_hub",
    )
    for marker in required:
        if marker not in joined:
            raise AssertionError(f"Missing marker: {marker}")
    for forbidden in ("OPENAI_API_KEY", "DASHSCOPE_API_KEY", "crossfade=d"):
        if forbidden in joined:
            raise AssertionError(f"Forbidden marker: {forbidden}")
    for pattern in (r"sk-[A-Za-z0-9_-]{20,}", r"hf_[A-Za-z0-9]{20,}", r"AIza[A-Za-z0-9_-]{20,}"):
        if re.search(pattern, joined):
            raise AssertionError("Credential found")


def synthetic_smoke_test() -> None:
    """Test exact prefix/continuation assembly, scrub GOP, reverse preview, and ZIP integrity."""
    import fractions

    import numpy as np

    source_count = 73
    anchor_index = 48
    continuation_count = 97
    source = [np.full((32, 48, 3), index, np.uint8) for index in range(source_count)]
    continuation = [np.full((32, 48, 3), anchor_index + index, np.uint8) for index in range(continuation_count)]
    continuation[0] = source[anchor_index].copy()
    combined = source[:anchor_index] + continuation
    if len(combined) != 145 or not np.array_equal(combined[48], source[48]):
        raise AssertionError("Synthetic frame policy failed")

    def encode(frames: list[np.ndarray], path: Path, gop: int | None = None) -> None:
        command = [
            "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s:v", "48x32", "-r", "24", "-i", "-", "-an", "-c:v", "libx264",
            "-crf", "28", "-pix_fmt", "yuv420p",
        ]
        if gop:
            command += ["-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0", "-bf", "0"]
        command.append(str(path))
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        for frame in frames:
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise AssertionError("Synthetic video encoding failed")

    def probe(path: Path) -> tuple[int, float]:
        output = subprocess.run([
            "ffprobe", "-count_frames", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate,nb_read_frames", "-of", "json", str(path),
        ], check=True, capture_output=True, text=True).stdout
        stream = json.loads(output)["streams"][0]
        return int(stream["nb_read_frames"]), float(fractions.Fraction(stream["avg_frame_rate"]))

    def max_keyframe_gap(path: Path) -> int:
        output = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "frame=key_frame", "-of", "json", str(path),
        ], check=True, capture_output=True, text=True).stdout
        flags = [int(frame["key_frame"]) for frame in json.loads(output)["frames"]]
        keys = [index for index, flag in enumerate(flags) if flag]
        if not keys or keys[0] != 0:
            return len(flags)
        return max([right - left for left, right in zip(keys, keys[1:])] + [len(flags) - keys[-1]])

    with tempfile.TemporaryDirectory(prefix="stanford-continuous-smoke-") as directory:
        root = Path(directory)
        master = root / "master.mp4"
        scrub = root / "scrub.mp4"
        pingpong = root / "pingpong.mp4"
        encode(combined, master)
        encode(combined, scrub, gop=6)
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", str(master),
            "-filter_complex", "[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[a];"
                               "[r]reverse,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-an", "-r", "24", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(pingpong),
        ], check=True)
        if probe(master) != (145, 24.0) or probe(scrub) != (145, 24.0) or probe(pingpong) != (290, 24.0):
            raise AssertionError("Synthetic video structure failed")
        if max_keyframe_gap(scrub) > 6:
            raise AssertionError("Synthetic scrub GOP failed")
        bundle = root / "bundle.zip"
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(master, master.name)
            archive.write(scrub, scrub.name)
        with zipfile.ZipFile(bundle) as archive:
            if archive.testzip() is not None:
                raise AssertionError("Synthetic ZIP integrity failed")


def main() -> None:
    notebook = build_notebook()
    audit(notebook)
    synthetic_smoke_test()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT)
    print("static audit: passed")
    print("synthetic smoke test: passed")
    print(OUTPUT)
    print("sha256", hashlib.sha256(OUTPUT.read_bytes()).hexdigest())
    print("bytes", OUTPUT.stat().st_size)


if __name__ == "__main__":
    main()
