#!/usr/bin/env python3
"""Build the Stanford uniform-synthetic RIFE cadence bake-off notebook."""

from __future__ import annotations

import ast
from pathlib import Path

import nbformat

import build_stanford_rife_bakeoff_colab as base


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "stanford_rife_uniform_synthetic_bakeoff_colab.ipynb"


TITLE = r'''
# Stanford RIFE uniform-synthetic cadence test

This short diagnostic tests one specific hypothesis from the previous bake-off:
the objectionable cadence comes from alternating sharp native frames with softer
RIFE midpoints.

The camera speed and duration stay unchanged. The comparison contains:

1. native 16 fps frames held at 32 fps;
2. conventional RIFE 4.26 at 32 fps, alternating originals and midpoints;
3. **uniform-synthetic RIFE 4.26** at 32 fps, using only the 25% and 75%
   positions between every native pair and discarding all native frames;
4. the same uniform-synthetic stream with one consistent, mild luma-only
   sharpening pass.

The uniform stream receives one duplicated synthetic boundary frame so every
candidate has the same 53-frame synchronized duration. No original frame appears
inside either uniform-synthetic candidate. No automatic winner is selected.

Use a Colab T4 GPU with standard RAM. Useful outputs are hash-verified on Google
Drive; the RIFE repository and model remain ephemeral. The runtime disconnects
after success or an uncaught error.
'''


SETTINGS = r'''
SOURCE_EXPERIMENT_ID = "stanford_wan21_flf2v_whip_720p_v2"
SOURCE_POSTPROCESS_ID = "stabilized_film32_whip_v3"
BAKEOFF_ID = "rife_uniform_synthetic_column_sweep_v1"

SOURCE_WIDTH, SOURCE_HEIGHT = 1280, 720
SOURCE_FPS = 16
OUTPUT_FPS = 32

# Same difficult foreground-column interval as the previous bake-off.
SEGMENT_START = 36
SEGMENT_END = 62

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

if SEGMENT_START < 0 or SEGMENT_END <= SEGMENT_START:
    raise ValueError("Invalid bake-off segment")
if SOURCE_FPS * 2 != OUTPUT_FPS:
    raise ValueError("This diagnostic expects exact 2x output")
if not (0.0 <= SHARPEN_AMOUNT <= 0.30):
    raise ValueError("Sharpening must stay deliberately mild")

print("Bake-off:", BAKEOFF_ID)
print("Native frames:", SEGMENT_START, "through", SEGMENT_END)
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
DRIVE_BAKEOFF = DRIVE_EXPERIMENT / "bakeoffs" / BAKEOFF_ID

RUNTIME_ROOT = Path("/content/stanford_rife_uniform_synthetic_bakeoff")
RUNTIME_OUTPUT = RUNTIME_ROOT / "outputs"
RUNTIME_MODELS = RUNTIME_ROOT / "models"
RIFE_REPO = RUNTIME_ROOT / "Practical-RIFE"

SOURCE_VIDEO = DRIVE_SOURCE_POST / "02_post_stabilization_720p16.mp4"
NATIVE_16 = RUNTIME_OUTPUT / "A_native_column_sweep_720p16.mp4"
NATIVE_HOLD_32 = RUNTIME_OUTPUT / "A_native_hold_column_sweep_720p32.mp4"
STANDARD_RIFE_32 = RUNTIME_OUTPUT / "B_standard_rife426_original_midpoint_720p32.mp4"
UNIFORM_SYNTHETIC_32 = RUNTIME_OUTPUT / "C_uniform_synthetic_rife426_720p32.mp4"
UNIFORM_SHARP_32 = RUNTIME_OUTPUT / "D_uniform_synthetic_rife426_mild_sharpen_720p32.mp4"
FOUR_UP = RUNTIME_OUTPUT / "E_four_up_uniform_synthetic_bakeoff_720p32.mp4"
CADENCE_SHEET = RUNTIME_OUTPUT / "uniform_synthetic_cadence_inspection.jpg"
DETAIL_SHEET = RUNTIME_OUTPUT / "uniform_synthetic_detail_inspection.jpg"
METRICS_PATH = RUNTIME_OUTPUT / "uniform_synthetic_metrics.json"
MANIFEST_PATH = RUNTIME_OUTPUT / "uniform_synthetic_manifest.json"

for path in (DRIVE_BAKEOFF, RUNTIME_OUTPUT, RUNTIME_MODELS):
    path.mkdir(parents=True, exist_ok=True)

probe = DRIVE_BAKEOFF / f".write-probe-{uuid.uuid4().hex}"
probe.write_text(f"uniform synthetic bakeoff {time.time_ns()}\n", encoding="utf-8")
if not probe.read_text(encoding="utf-8").startswith("uniform synthetic bakeoff"):
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
        (DRIVE_BAKEOFF / "runtime_shutdown.json").write_text(
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
    target=hard_cutoff, name="uniform-rife-bakeoff-cutoff", daemon=True
).start()

def disconnect_after_cell_error(result):
    failure = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
    if failure is not None and AUTO_DISCONNECT_ON_ERROR:
        disconnect_runtime("uncaught notebook error", failure=failure)

get_ipython().events.register("post_run_cell", disconnect_after_cell_error)

print("Source:", SOURCE_VIDEO)
print("Durable output:", DRIVE_BAKEOFF)
print("RIFE repository and weights remain ephemeral")
'''


RIFE_SETUP = base.RIFE_SETUP.replace(
    "both official model archives", "the official RIFE 4.26 model archive"
)


GENERATE = r'''
def render_positions(model, positions, label, cache):
    output = []
    for index, position in enumerate(positions):
        output.append(rife_frame_at_position(model, segment_frames, position, cache))
        if index == 0 or (index + 1) % 10 == 0 or index + 1 == len(positions):
            print(f"{label}: {index + 1}/{len(positions)}")
    return output

# Conventional 2x RIFE: native positions 0, 1, 2... remain visible and the
# synthesized midpoint occupies each odd output frame.
standard_positions = np.arange(0.0, len(segment_frames) - 0.5, 0.5, dtype=np.float64)
expected_output_frames = 2 * len(segment_frames) - 1
if len(standard_positions) != expected_output_frames:
    raise RuntimeError("Standard RIFE position count is wrong")

# Uniform stream: all motion frames are synthetic. The spacing remains exactly
# half a native interval, so playback duration and camera speed do not change.
quarter_positions = np.asarray([
    pair + fraction
    for pair in range(len(segment_frames) - 1)
    for fraction in (0.25, 0.75)
], dtype=np.float64)
if len(quarter_positions) != expected_output_frames - 1:
    raise RuntimeError("Quarter-position count is wrong")
if np.any(np.isclose(quarter_positions, np.round(quarter_positions))):
    raise RuntimeError("Uniform stream unexpectedly contains a native position")

model_426 = load_rife(MODEL_DIRS["rife426"])
inference_cache = {}
standard_rife_frames = render_positions(
    model_426, standard_positions, "standard RIFE 4.26", inference_cache
)
uniform_core_frames = render_positions(
    model_426, quarter_positions, "uniform-synthetic RIFE 4.26", inference_cache
)
model_426 = dispose_rife(model_426)

# A one-frame synthetic boundary hold synchronizes the 52 quarter-position
# frames with the 53-frame baseline. It occurs before the camera move and never
# introduces native/synthetic alternation.
uniform_synthetic_frames = [uniform_core_frames[0].copy(), *uniform_core_frames]
if len(uniform_synthetic_frames) != expected_output_frames:
    raise RuntimeError("Uniform synchronized frame count is wrong")

def mild_luma_unsharp(frame, amount=SHARPEN_AMOUNT, sigma=SHARPEN_SIGMA):
    ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
    y = ycrcb[:, :, 0].astype(np.float32)
    blurred = cv2.GaussianBlur(y, (0, 0), sigmaX=sigma, sigmaY=sigma)
    ycrcb[:, :, 0] = np.clip(y + amount * (y - blurred), 0, 255).astype(np.uint8)
    return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

uniform_sharp_frames = [mild_luma_unsharp(frame) for frame in uniform_synthetic_frames]

encode_bgr(standard_rife_frames, OUTPUT_FPS, STANDARD_RIFE_32, crf=13, gop=4)
encode_bgr(uniform_synthetic_frames, OUTPUT_FPS, UNIFORM_SYNTHETIC_32, crf=13, gop=4)
encode_bgr(uniform_sharp_frames, OUTPUT_FPS, UNIFORM_SHARP_32, crf=13, gop=4)

print("Rendered standard and uniform-synthetic candidates")
'''


COMPARE_AND_QA = r'''
candidate_frames = {
    "A  Native 16 fps (held)": native_hold_frames,
    "B  Standard RIFE 4.26": standard_rife_frames,
    "C  Uniform synthetic": uniform_synthetic_frames,
    "D  Uniform + mild sharpen": uniform_sharp_frames,
}
if len({len(frames) for frames in candidate_frames.values()}) != 1:
    raise RuntimeError("Candidate lengths differ")

def labeled_panel(frame, label, width=640, height=360):
    panel = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    cv2.rectangle(panel, (0, 0), (width, 38), (13, 13, 13), -1)
    cv2.putText(
        panel, label, (14, 26), cv2.FONT_HERSHEY_SIMPLEX,
        0.68, (255, 255, 255), 1, cv2.LINE_AA,
    )
    return panel

labels = list(candidate_frames)
four_up_frames = []
for index in range(expected_output_frames):
    panels = [labeled_panel(candidate_frames[label][index], label) for label in labels]
    four_up_frames.append(np.vstack([np.hstack(panels[:2]), np.hstack(panels[2:])]))
encode_bgr(four_up_frames, OUTPUT_FPS, FOUR_UP, crf=15, gop=4)

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

def candidate_metrics(frames):
    speeds = flow_speed_series(frames)
    sharpness = np.asarray([
        float(cv2.Laplacian(analysis_gray(frame, 480), cv2.CV_32F).var())
        for frame in frames
    ])
    motion_alternation = np.abs(np.diff(speeds)) / (
        0.5 * (speeds[:-1] + speeds[1:]) + 1e-6
    )
    sharp_curvature = np.abs(
        sharpness[1:-1] - 0.5 * (sharpness[:-2] + sharpness[2:])
    ) / (0.5 * (sharpness[:-2] + sharpness[2:]) + 1e-6)
    odd_neighbor_ratios = sharpness[1:-1:2] / (
        0.5 * (sharpness[:-2:2] + sharpness[2::2]) + 1e-6
    )
    return {
        "frames": len(frames),
        "median_flow": float(np.median(speeds)),
        "p95_flow": float(np.percentile(speeds, 95)),
        "median_flow_alternation": float(np.median(motion_alternation)),
        "median_sharpness": float(np.median(sharpness)),
        "median_sharpness_curvature": float(np.median(sharp_curvature)),
        "median_odd_to_neighbor_sharpness_ratio": float(np.median(odd_neighbor_ratios)),
    }

metrics = {
    "status": "visual_review_required",
    "warning": "Metrics cannot certify neural interpolation quality; judge the full-speed video and detail sheet.",
    "source_segment": {
        "first_native_frame": SEGMENT_START,
        "last_native_frame": SEGMENT_END,
    },
    "uniform_method": {
        "positions_per_native_pair": [0.25, 0.75],
        "native_frames_in_motion_stream": 0,
        "synthetic_boundary_hold_frames": 1,
        "duration_or_speed_change": False,
    },
    "candidates": {
        label: candidate_metrics(frames)
        for label, frames in candidate_frames.items()
    },
}
METRICS_PATH.write_text(
    json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8"
)

# Consecutive frames around the moving column expose any remaining cadence.
center = expected_output_frames // 2
inspection_indices = list(range(center - 5, center + 6))
cadence_rows = []
for label in labels:
    panels = [
        labeled_panel(candidate_frames[label][index], f"{label} | {index}", 240, 135)
        for index in inspection_indices
    ]
    cadence_rows.append(np.hstack(panels))
cadence_sheet = np.vstack(cadence_rows)
if not cv2.imwrite(str(CADENCE_SHEET), cadence_sheet, [cv2.IMWRITE_JPEG_QUALITY, 96]):
    raise RuntimeError("Could not write cadence sheet")

# Larger crops retain enough detail to see stone and church texture behavior.
detail_indices = [center - 6, center - 2, center + 2, center + 6]
detail_rows = []
for label in labels:
    panels = []
    for index in detail_indices:
        crop = candidate_frames[label][index][:, 160:1120]
        panels.append(labeled_panel(crop, f"{label} | {index}", 480, 360))
    detail_rows.append(np.hstack(panels))
detail_sheet = np.vstack(detail_rows)
if not cv2.imwrite(str(DETAIL_SHEET), detail_sheet, [cv2.IMWRITE_JPEG_QUALITY, 97]):
    raise RuntimeError("Could not write detail sheet")

print(json.dumps(metrics, indent=2))
display(IPImage(filename=str(CADENCE_SHEET)))
display(IPImage(filename=str(DETAIL_SHEET)))
display(Video(str(FOUR_UP), embed=True, width=1000))
'''


FINALIZE = r'''
expected_32_frames = 2 * expected_segment_frames - 1
video_contracts = {
    NATIVE_16: (SOURCE_FPS, expected_segment_frames),
    NATIVE_HOLD_32: (OUTPUT_FPS, expected_32_frames),
    STANDARD_RIFE_32: (OUTPUT_FPS, expected_32_frames),
    UNIFORM_SYNTHETIC_32: (OUTPUT_FPS, expected_32_frames),
    UNIFORM_SHARP_32: (OUTPUT_FPS, expected_32_frames),
    FOUR_UP: (OUTPUT_FPS, expected_32_frames),
}
probes = {}
for path, (fps, frames) in video_contracts.items():
    video_probe = probe_video(path)
    contract = (
        video_probe["width"], video_probe["height"],
        round(video_probe["fps"]), video_probe["frames"],
    )
    if contract != (SOURCE_WIDTH, SOURCE_HEIGHT, fps, frames):
        raise RuntimeError(f"Invalid output contract for {path.name}: {video_probe}")
    probes[path.name] = video_probe

deliverables = (
    NATIVE_16,
    NATIVE_HOLD_32,
    STANDARD_RIFE_32,
    UNIFORM_SYNTHETIC_32,
    UNIFORM_SHARP_32,
    FOUR_UP,
    CADENCE_SHEET,
    DETAIL_SHEET,
    METRICS_PATH,
)
artifacts = {}
for path in deliverables:
    digest = atomic_publish(path, DRIVE_BAKEOFF / path.name)
    artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}

manifest = {
    "status": "complete_visual_review_required",
    "source": {
        "path": str(SOURCE_VIDEO),
        "sha256": sha256_file(SOURCE_VIDEO),
        "probe": source_probe,
        "segment_inclusive": [SEGMENT_START, SEGMENT_END],
    },
    "rife": {
        "repository": RIFE_REPO_URL,
        "commit": RIFE_REPO_COMMIT,
        "license": "MIT",
        "models": RIFE_MODELS,
        "model_cache_persisted": False,
    },
    "uniform_synthetic": {
        "positions_per_native_pair": [0.25, 0.75],
        "all_native_motion_frames_discarded": True,
        "boundary_padding": "duplicate first synthetic frame once",
        "output_fps": OUTPUT_FPS,
        "duration_or_camera_speed_changed": False,
        "sharpen": {
            "candidate": UNIFORM_SHARP_32.name,
            "method": "luma-only Gaussian unsharp mask",
            "amount": SHARPEN_AMOUNT,
            "sigma": SHARPEN_SIGMA,
        },
    },
    "visual_review": {
        "four_up": FOUR_UP.name,
        "cadence_sheet": CADENCE_SHEET.name,
        "detail_sheet": DETAIL_SHEET.name,
        "automatic_winner": None,
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
manifest_digest = atomic_publish(MANIFEST_PATH, DRIVE_BAKEOFF / MANIFEST_PATH.name)

bundle = RUNTIME_OUTPUT / f"{BAKEOFF_ID}_review_bundle.zip"
with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in (*deliverables, MANIFEST_PATH):
        archive.write(path, arcname=path.name)
bundle_digest = atomic_publish(bundle, DRIVE_BAKEOFF / bundle.name)

success = DRIVE_BAKEOFF / "success.json"
success.write_text(json.dumps({
    "status": "complete_visual_review_required",
    "manifest_sha256": manifest_digest,
    "bundle": {
        "path": str(DRIVE_BAKEOFF / bundle.name),
        "sha256": bundle_digest,
    },
    "four_up_comparison": str(DRIVE_BAKEOFF / FOUR_UP.name),
    "models_persisted": False,
    "next_gate": "Eric judges whether uniform synthesis removes cadence without unacceptable warping",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

for path in (DRIVE_BAKEOFF / MANIFEST_PATH.name, DRIVE_BAKEOFF / bundle.name, success):
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Final persistence check failed: {path}")

print("COMPLETE:", DRIVE_BAKEOFF)
print("Four-up comparison:", DRIVE_BAKEOFF / FOUR_UP.name)
print("Review bundle:", DRIVE_BAKEOFF / bundle.name)

if AUTO_DISCONNECT_ON_SUCCESS:
    disconnect_runtime("Uniform-synthetic RIFE bake-off completed and verified on Drive")
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
        nbformat.v4.new_code_cell(COMPARE_AND_QA.strip()),
        nbformat.v4.new_code_cell(FINALIZE.strip()),
    ]
    nbformat.validate(notebook)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=f"cell-{index}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT)
    if OUTPUT.stat().st_size > 150_000:
        raise RuntimeError("Notebook unexpectedly large")
    return OUTPUT


if __name__ == "__main__":
    output = build()
    print(output)
    print(output.stat().st_size, "bytes")
