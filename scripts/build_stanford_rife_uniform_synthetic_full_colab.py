#!/usr/bin/env python3
"""Build the full Stanford uniform-synthetic RIFE production notebook."""

from __future__ import annotations

import ast
from pathlib import Path

import nbformat

import build_stanford_rife_bakeoff_colab as base


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "stanford_rife_uniform_synthetic_full_colab.ipynb"


TITLE = r'''
# Stanford full uniform-synthetic RIFE pass

This notebook applies the approved bake-off treatment to the complete stabilized
Stanford shot:

- RIFE 4.26 samples only the 25% and 75% positions between native frames;
- every native motion frame is discarded, removing native/synthetic cadence;
- one synthetic boundary hold is added at each end, preserving the original
  5.0625-second duration at 32 fps;
- the accepted luma-only mild sharpening pass is applied consistently;
- both a high-quality master and GOP-4 scrub-optimized web version are saved.

All useful media, QA metrics, provenance, and a review bundle persist to Google
Drive. The RIFE repository and model remain ephemeral. The runtime disconnects
after success or an uncaught error.

Use a Colab T4 GPU with standard RAM. L4 or A100 also work but are unnecessary.
'''


SETTINGS = r'''
SOURCE_EXPERIMENT_ID = "stanford_wan21_flf2v_whip_720p_v2"
SOURCE_POSTPROCESS_ID = "stabilized_film32_whip_v3"
POSTPROCESS_ID = "rife_uniform_synthetic_full_v1"

SOURCE_WIDTH, SOURCE_HEIGHT = 1280, 720
SOURCE_FPS = 16
OUTPUT_FPS = 32
SEGMENT_START = 0
SEGMENT_END = 80

RIFE_REPO_URL = "https://github.com/hzwer/Practical-RIFE.git"
RIFE_REPO_COMMIT = "17d8c7a1005b37f4c97bfee04e316aaec7fdc536"
RIFE_MODELS = {
    "rife426": {
        "gdrive_id": "1gViYvvQrtETBgU1w8axZSsr7YUuw31uy",
        "bytes": 22_867_954,
        "sha256": "c2452dd2b244947d4be580156bbead60d6b72af5736860f7d6b3f99648c9c4cc",
    },
}

SHARPEN_AMOUNT = 0.14
SHARPEN_SIGMA = 0.85

AUTO_DISCONNECT_ON_SUCCESS = True
AUTO_DISCONNECT_ON_ERROR = True
HARD_CUTOFF_HOURS = 1.0

if SOURCE_FPS * 2 != OUTPUT_FPS:
    raise ValueError("This production pass expects exact 2x output")
if SEGMENT_START != 0 or SEGMENT_END != 80:
    raise ValueError("The approved full source contract is exactly frames 0 through 80")
if not (0.0 <= SHARPEN_AMOUNT <= 0.30):
    raise ValueError("Sharpening must stay deliberately mild")

print("Production pass:", POSTPROCESS_ID)
'''


SETUP = r'''
from google.colab import drive
from google.colab import drive as colab_drive, runtime as colab_runtime
from IPython.display import Image as IPImage, Video, display
from pathlib import Path
import gc, hashlib, importlib, json, math, os, platform, shutil, subprocess, sys, threading, time, uuid, zipfile

drive.mount("/content/drive", force_remount=False)

DRIVE_ROOT = Path("/content/drive/MyDrive/Personal_Website_Wan21_FLF2V")
DRIVE_EXPERIMENT = DRIVE_ROOT / "experiments" / SOURCE_EXPERIMENT_ID
DRIVE_SOURCE_POST = DRIVE_EXPERIMENT / "postprocess" / SOURCE_POSTPROCESS_ID
DRIVE_OUTPUT = DRIVE_EXPERIMENT / "postprocess" / POSTPROCESS_ID

RUNTIME_ROOT = Path("/content/stanford_rife_uniform_synthetic_full")
RUNTIME_OUTPUT = RUNTIME_ROOT / "outputs"
RUNTIME_MODELS = RUNTIME_ROOT / "models"
RIFE_REPO = RUNTIME_ROOT / "Practical-RIFE"

SOURCE_VIDEO = DRIVE_SOURCE_POST / "02_post_stabilization_720p16.mp4"
NATIVE_16 = RUNTIME_OUTPUT / "00_source_stabilized_720p16.mp4"
NATIVE_HOLD_32 = RUNTIME_OUTPUT / "00_source_hold_preview_720p32.mp4"
UNIFORM_RAW = RUNTIME_OUTPUT / "01_uniform_synthetic_rife426_full_720p32.mp4"
SHARP_MASTER = RUNTIME_OUTPUT / "02_uniform_synthetic_mild_sharpen_master_720p32.mp4"
SCROLL_GOP4 = RUNTIME_OUTPUT / "03_uniform_synthetic_mild_sharpen_scroll_gop4_720p32.mp4"
REVIEW_SIDE_BY_SIDE = RUNTIME_OUTPUT / "04_source_vs_final_review_720p32.mp4"
CONTACT_SHEET = RUNTIME_OUTPUT / "full_uniform_synthetic_contact_sheet.jpg"
CADENCE_SHEET = RUNTIME_OUTPUT / "full_uniform_synthetic_cadence_sheet.jpg"
START_POSTER = RUNTIME_OUTPUT / "stanford_start_poster.jpg"
END_POSTER = RUNTIME_OUTPUT / "stanford_end_poster.jpg"
METRICS_PATH = RUNTIME_OUTPUT / "full_uniform_synthetic_metrics.json"
MANIFEST_PATH = RUNTIME_OUTPUT / "full_uniform_synthetic_manifest.json"

for path in (DRIVE_OUTPUT, RUNTIME_OUTPUT, RUNTIME_MODELS):
    path.mkdir(parents=True, exist_ok=True)

probe = DRIVE_OUTPUT / f".write-probe-{uuid.uuid4().hex}"
probe.write_text(f"full uniform synthetic {time.time_ns()}\n", encoding="utf-8")
if not probe.read_text(encoding="utf-8").startswith("full uniform synthetic"):
    raise RuntimeError("Google Drive persistence check failed")
probe.unlink()

_shutdown_started = threading.Event()

def disconnect_runtime(reason, *, failure=None):
    if _shutdown_started.is_set():
        return
    _shutdown_started.set()
    payload = {"reason": reason, "time": time.time()}
    if failure is not None:
        payload["failure"] = str(failure)
    try:
        (DRIVE_OUTPUT / "runtime_shutdown.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        colab_drive.flush_and_unmount()
    finally:
        time.sleep(2)
        colab_runtime.unassign()

def hard_cutoff():
    if _shutdown_started.wait(HARD_CUTOFF_HOURS * 3600):
        return
    disconnect_runtime(f"hard cutoff after {HARD_CUTOFF_HOURS:.1f} hours")

threading.Thread(
    target=hard_cutoff, name="full-uniform-rife-cutoff", daemon=True
).start()

def disconnect_after_cell_error(result):
    failure = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
    if failure is not None and AUTO_DISCONNECT_ON_ERROR:
        disconnect_runtime("uncaught notebook error", failure=failure)

get_ipython().events.register("post_run_cell", disconnect_after_cell_error)

print("Source:", SOURCE_VIDEO)
print("Durable output:", DRIVE_OUTPUT)
print("RIFE repository and weights remain ephemeral")
'''


RIFE_SETUP = base.RIFE_SETUP.replace(
    "both official model archives", "the official RIFE 4.26 model archive"
)


GENERATE = r'''
# Two non-native frames per source interval. Padding both ends with the nearest
# synthetic frame yields 162 frames: exactly 5.0625 seconds at 32 fps.
quarter_positions = np.asarray([
    pair + fraction
    for pair in range(len(segment_frames) - 1)
    for fraction in (0.25, 0.75)
], dtype=np.float64)
expected_core_frames = 2 * (len(segment_frames) - 1)
expected_output_frames = len(segment_frames) * 2

if len(quarter_positions) != expected_core_frames:
    raise RuntimeError("Quarter-position count is wrong")
if np.any(np.isclose(quarter_positions, np.round(quarter_positions))):
    raise RuntimeError("Production stream unexpectedly contains a native position")

model_426 = load_rife(MODEL_DIRS["rife426"])
uniform_core_frames = []
for index, position in enumerate(quarter_positions):
    uniform_core_frames.append(
        rife_frame_at_position(model_426, segment_frames, position, cache=None)
    )
    if index == 0 or (index + 1) % 20 == 0 or index + 1 == len(quarter_positions):
        print(f"Uniform-synthetic RIFE 4.26: {index + 1}/{len(quarter_positions)}")
model_426 = dispose_rife(model_426)

uniform_frames = [
    uniform_core_frames[0].copy(),
    *uniform_core_frames,
    uniform_core_frames[-1].copy(),
]
if len(uniform_frames) != expected_output_frames:
    raise RuntimeError("Full synchronized frame count is wrong")

def mild_luma_unsharp(frame, amount=SHARPEN_AMOUNT, sigma=SHARPEN_SIGMA):
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)
    blurred = cv2.GaussianBlur(y, (0, 0), sigmaX=sigma, sigmaY=sigma)
    ycrcb[:, :, 0] = np.clip(y + amount * (y - blurred), 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

sharpened_frames = [mild_luma_unsharp(frame) for frame in uniform_frames]

encode_bgr(uniform_frames, OUTPUT_FPS, UNIFORM_RAW, crf=12, gop=16)
encode_bgr(sharpened_frames, OUTPUT_FPS, SHARP_MASTER, crf=11, gop=32)
encode_bgr(sharpened_frames, OUTPUT_FPS, SCROLL_GOP4, crf=15, gop=4)

if not cv2.imwrite(str(START_POSTER), sharpened_frames[0], [cv2.IMWRITE_JPEG_QUALITY, 96]):
    raise RuntimeError("Could not write start poster")
if not cv2.imwrite(str(END_POSTER), sharpened_frames[-1], [cv2.IMWRITE_JPEG_QUALITY, 96]):
    raise RuntimeError("Could not write end poster")

print("Full uniform-synthetic master and scrub encode complete")
'''


REVIEW_AND_QA = r'''
def labeled_panel(frame, label, width=640, height=360):
    panel = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    cv2.rectangle(panel, (0, 0), (width, 38), (13, 13, 13), -1)
    cv2.putText(
        panel, label, (14, 26), cv2.FONT_HERSHEY_SIMPLEX,
        0.68, (255, 255, 255), 1, cv2.LINE_AA,
    )
    return panel

# Two holds per native source frame make a synchronized reference of the exact
# original duration. Labels exist only in this diagnostic review clip.
source_hold_frames = [frame for frame in segment_frames for _ in range(2)]
if len(source_hold_frames) != len(sharpened_frames):
    raise RuntimeError("Review streams are not synchronized")

review_frames = [
    np.hstack([
        labeled_panel(source_hold_frames[index], "Original stabilized 16 fps (held)"),
        labeled_panel(sharpened_frames[index], "Uniform synthetic + mild sharpen"),
    ])
    for index in range(len(sharpened_frames))
]
encode_bgr(review_frames, OUTPUT_FPS, REVIEW_SIDE_BY_SIDE, crf=15, gop=4)

def analysis_gray(frame, width=480):
    height = round(frame.shape[0] * width / frame.shape[1])
    small = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

def flow_speed_series(frames):
    speeds = []
    for frame0, frame1 in zip(frames, frames[1:]):
        gray0, gray1 = analysis_gray(frame0, 320), analysis_gray(frame1, 320)
        flow = cv2.calcOpticalFlowFarneback(
            gray0, gray1, None, 0.5, 4, 21, 4, 7, 1.5, 0
        )
        speeds.append(float(np.median(np.linalg.norm(flow, axis=2))))
    return np.asarray(speeds)

speeds = flow_speed_series(sharpened_frames)
sharpness = np.asarray([
    float(cv2.Laplacian(analysis_gray(frame, 480), cv2.CV_32F).var())
    for frame in sharpened_frames
])
sharp_curvature = np.abs(
    sharpness[1:-1] - 0.5 * (sharpness[:-2] + sharpness[2:])
) / (0.5 * (sharpness[:-2] + sharpness[2:]) + 1e-6)
odd_neighbor_ratios = sharpness[1:-1:2] / (
    0.5 * (sharpness[:-2:2] + sharpness[2::2]) + 1e-6
)
means = np.asarray([float(analysis_gray(frame, 320).mean()) for frame in sharpened_frames])
identical_pairs = [
    index for index, (left, right) in enumerate(zip(sharpened_frames, sharpened_frames[1:]))
    if np.array_equal(left, right)
]

metrics = {
    "status": "technical_contract_pass_visual_review_required",
    "frames": len(sharpened_frames),
    "fps": OUTPUT_FPS,
    "duration_seconds": len(sharpened_frames) / OUTPUT_FPS,
    "median_flow": float(np.median(speeds)),
    "p95_flow": float(np.percentile(speeds, 95)),
    "median_sharpness": float(np.median(sharpness)),
    "median_sharpness_curvature": float(np.median(sharp_curvature)),
    "median_odd_to_neighbor_sharpness_ratio": float(np.median(odd_neighbor_ratios)),
    "black_frame_count": int(np.count_nonzero(means < 5.0)),
    "identical_adjacent_pairs": identical_pairs,
    "expected_boundary_holds": [0, len(sharpened_frames) - 2],
    "warning": "Technical checks do not certify aesthetics; review the complete side-by-side video.",
}
if metrics["black_frame_count"] != 0:
    raise RuntimeError(f"Unexpected black output frames: {metrics['black_frame_count']}")
if identical_pairs != metrics["expected_boundary_holds"]:
    raise RuntimeError(f"Unexpected identical-frame positions: {identical_pairs}")

METRICS_PATH.write_text(
    json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)

# Twelve evenly spaced full-shot checkpoints.
contact_indices = np.linspace(0, len(sharpened_frames) - 1, 12).round().astype(int)
contact_panels = [
    labeled_panel(sharpened_frames[index], f"Final | frame {index}", 320, 180)
    for index in contact_indices
]
contact_sheet = np.vstack([
    np.hstack(contact_panels[:4]),
    np.hstack(contact_panels[4:8]),
    np.hstack(contact_panels[8:]),
])
if not cv2.imwrite(str(CONTACT_SHEET), contact_sheet, [cv2.IMWRITE_JPEG_QUALITY, 96]):
    raise RuntimeError("Could not write contact sheet")

# Consecutive frames around the strongest non-boundary motion change.
flow_delta = np.abs(np.diff(speeds))
center = int(np.argmax(flow_delta[2:-2])) + 3
cadence_indices = list(range(max(0, center - 5), min(len(sharpened_frames), center + 6)))
cadence_panels = [
    labeled_panel(sharpened_frames[index], f"Final | frame {index}", 240, 135)
    for index in cadence_indices
]
cadence_sheet = np.hstack(cadence_panels)
if not cv2.imwrite(str(CADENCE_SHEET), cadence_sheet, [cv2.IMWRITE_JPEG_QUALITY, 96]):
    raise RuntimeError("Could not write cadence sheet")

print(json.dumps(metrics, indent=2))
display(IPImage(filename=str(CONTACT_SHEET)))
display(IPImage(filename=str(CADENCE_SHEET)))
display(Video(str(REVIEW_SIDE_BY_SIDE), embed=True, width=1000))
'''


FINALIZE = r'''
expected_output_frames = 162
video_contracts = {
    UNIFORM_RAW: (OUTPUT_FPS, expected_output_frames, SOURCE_WIDTH, SOURCE_HEIGHT),
    SHARP_MASTER: (OUTPUT_FPS, expected_output_frames, SOURCE_WIDTH, SOURCE_HEIGHT),
    SCROLL_GOP4: (OUTPUT_FPS, expected_output_frames, SOURCE_WIDTH, SOURCE_HEIGHT),
    REVIEW_SIDE_BY_SIDE: (OUTPUT_FPS, expected_output_frames, SOURCE_WIDTH, SOURCE_HEIGHT // 2),
}
probes = {}
for path, (fps, frames, width, height) in video_contracts.items():
    video_probe = probe_video(path)
    contract = (
        video_probe["width"], video_probe["height"],
        round(video_probe["fps"]), video_probe["frames"],
    )
    if contract != (width, height, fps, frames):
        raise RuntimeError(f"Invalid output contract for {path.name}: {video_probe}")
    probes[path.name] = video_probe

if abs(probes[SCROLL_GOP4.name]["duration"] - source_probe["duration"]) > 1e-6:
    raise RuntimeError("Final duration no longer matches the source")

deliverables = (
    UNIFORM_RAW,
    SHARP_MASTER,
    SCROLL_GOP4,
    REVIEW_SIDE_BY_SIDE,
    CONTACT_SHEET,
    CADENCE_SHEET,
    START_POSTER,
    END_POSTER,
    METRICS_PATH,
)
artifacts = {}
for path in deliverables:
    digest = atomic_publish(path, DRIVE_OUTPUT / path.name)
    artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}

manifest = {
    "status": "complete_visual_review_required",
    "source": {
        "path": str(SOURCE_VIDEO),
        "sha256": sha256_file(SOURCE_VIDEO),
        "probe": source_probe,
        "frames_inclusive": [SEGMENT_START, SEGMENT_END],
    },
    "rife": {
        "repository": RIFE_REPO_URL,
        "commit": RIFE_REPO_COMMIT,
        "license": "MIT",
        "models": RIFE_MODELS,
        "model_cache_persisted": False,
    },
    "method": {
        "positions_per_native_pair": [0.25, 0.75],
        "all_native_motion_frames_discarded": True,
        "boundary_padding": "duplicate first and last synthetic frames once each",
        "output_fps": OUTPUT_FPS,
        "duration_or_camera_speed_changed": False,
        "sharpen": {
            "method": "luma-only Gaussian unsharp mask",
            "amount": SHARPEN_AMOUNT,
            "sigma": SHARPEN_SIGMA,
        },
        "scroll_encode": {
            "file": SCROLL_GOP4.name,
            "keyframe_interval": 4,
            "b_frames": 0,
            "faststart": True,
        },
    },
    "visual_review": {
        "side_by_side": REVIEW_SIDE_BY_SIDE.name,
        "contact_sheet": CONTACT_SHEET.name,
        "cadence_sheet": CADENCE_SHEET.name,
        "automatic_aesthetic_approval": False,
    },
    "probes": probes,
    "metrics": metrics,
    "artifacts": artifacts,
    "versions": {
        "python": platform.python_version(),
        "torch": torch.__version__,
        "opencv": cv2.__version__,
        "numpy": np.__version__,
    },
    "completed_at": time.time(),
}
MANIFEST_PATH.write_text(
    json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)
manifest_digest = atomic_publish(MANIFEST_PATH, DRIVE_OUTPUT / MANIFEST_PATH.name)

bundle = RUNTIME_OUTPUT / f"{POSTPROCESS_ID}_review_bundle.zip"
with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in (*deliverables, MANIFEST_PATH):
        archive.write(path, arcname=path.name)
bundle_digest = atomic_publish(bundle, DRIVE_OUTPUT / bundle.name)

success = DRIVE_OUTPUT / "success.json"
success.write_text(json.dumps({
    "status": "complete_visual_review_required",
    "manifest_sha256": manifest_digest,
    "bundle": {"path": str(DRIVE_OUTPUT / bundle.name), "sha256": bundle_digest},
    "master": str(DRIVE_OUTPUT / SHARP_MASTER.name),
    "scroll_encode": str(DRIVE_OUTPUT / SCROLL_GOP4.name),
    "review": str(DRIVE_OUTPUT / REVIEW_SIDE_BY_SIDE.name),
    "models_persisted": False,
    "next_gate": "Eric reviews the full Stanford shot before website integration",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

for path in (DRIVE_OUTPUT / MANIFEST_PATH.name, DRIVE_OUTPUT / bundle.name, success):
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Final persistence check failed: {path}")

print("COMPLETE:", DRIVE_OUTPUT)
print("Master:", DRIVE_OUTPUT / SHARP_MASTER.name)
print("Scroll encode:", DRIVE_OUTPUT / SCROLL_GOP4.name)
print("Review bundle:", DRIVE_OUTPUT / bundle.name)

if AUTO_DISCONNECT_ON_SUCCESS:
    disconnect_runtime("Full uniform-synthetic Stanford pass completed and verified on Drive")
else:
    _shutdown_started.set()
'''


def build() -> Path:
    notebook = nbformat.v4.new_notebook()
    notebook.metadata = {
        "colab": {"name": OUTPUT.name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.x"},
        "accelerator": "GPU",
    }
    notebook.cells = [
        nbformat.v4.new_markdown_cell(TITLE.strip()),
        nbformat.v4.new_code_cell(SETTINGS.strip()),
        nbformat.v4.new_code_cell(SETUP.strip()),
        nbformat.v4.new_code_cell(base.UTILITIES_AND_SOURCE.strip()),
        nbformat.v4.new_code_cell(RIFE_SETUP.strip()),
        nbformat.v4.new_code_cell(GENERATE.strip()),
        nbformat.v4.new_code_cell(REVIEW_AND_QA.strip()),
        nbformat.v4.new_code_cell(FINALIZE.strip()),
    ]
    nbformat.validate(notebook)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=f"cell-{index}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT)
    if OUTPUT.stat().st_size > 170_000:
        raise RuntimeError("Notebook unexpectedly large")
    return OUTPUT


if __name__ == "__main__":
    output = build()
    print(output)
    print(output.stat().st_size, "bytes")
