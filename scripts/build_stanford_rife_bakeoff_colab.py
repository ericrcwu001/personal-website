#!/usr/bin/env python3
"""Build the short Stanford RIFE interpolation bake-off Colab notebook."""

from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "stanford_rife_interpolation_bakeoff_colab.ipynb"


TITLE = r'''
# Stanford interpolation bake-off — native vs RIFE vs retimed shutter

This is a **short diagnostic**, not a full production pass. It takes the already
persisted, stabilized 16 fps Stanford clip and renders the difficult column-sweep
interval four ways:

1. native 16 fps, plus a 32 fps hold version for synchronized comparison;
2. Practical-RIFE 4.22-lite at 32 fps;
3. Practical-RIFE 4.26 at 32 fps;
4. RIFE 4.26 with an optical-flow-derived smooth time map and three-sample,
   linear-light 180-degree shutter integration.

The notebook creates a synchronized four-up video and full-resolution diagnostic
sheets. No method is automatically declared the winner: previous scalar motion
metrics failed to reveal objectionable neural pixel cadence, so Eric's visual
review is the gate.

Only diagnostic labels are baked into the four-up comparison. No website text is
added to any candidate clip. The two small RIFE model archives are downloaded to
ephemeral runtime storage and are not persisted to Drive.
'''


SETTINGS = r'''
SOURCE_EXPERIMENT_ID = "stanford_wan21_flf2v_whip_720p_v2"
SOURCE_POSTPROCESS_ID = "stabilized_film32_whip_v3"
BAKEOFF_ID = "rife_bakeoff_column_sweep_v1"

SOURCE_WIDTH, SOURCE_HEIGHT = 1280, 720
SOURCE_FPS = 16
OUTPUT_FPS = 32

# Inclusive native-frame interval. It covers approach, full foreground-column
# occlusion, and arcade reveal without spending time on the entire five seconds.
SEGMENT_START = 36
SEGMENT_END = 62

RIFE_REPO_URL = "https://github.com/hzwer/Practical-RIFE.git"
RIFE_REPO_COMMIT = "17d8c7a1005b37f4c97bfee04e316aaec7fdc536"
RIFE_MODELS = {
    "rife422lite": {
        "gdrive_id": "1Smy6gY7BkS_RzCjPCbMEy-TsX8Ma5B0R",
        "bytes": 19_878_007,
        "sha256": "5e123e7a9951940e607353906167a903443be4303ac091d6c6a35a43e35cf840",
    },
    "rife426": {
        "gdrive_id": "1gViYvvQrtETBgU1w8axZSsr7YUuw31uy",
        "bytes": 22_867_954,
        "sha256": "c2452dd2b244947d4be580156bbead60d6b72af5736860f7d6b3f99648c9c4cc",
    },
}

# The retimed variant uses three subframe samples across a 180-degree shutter.
SHUTTER_SAMPLES = 3
SHUTTER_ANGLE_DEGREES = 180
PROGRESS_SMOOTHING_WINDOW = 17

AUTO_DISCONNECT_ON_SUCCESS = True
AUTO_DISCONNECT_ON_ERROR = True
HARD_CUTOFF_HOURS = 1.0

if SEGMENT_START < 0 or SEGMENT_END <= SEGMENT_START:
    raise ValueError("Invalid bake-off segment")
if SOURCE_FPS * 2 != OUTPUT_FPS:
    raise ValueError("This bake-off expects exact 2x output")
if SHUTTER_SAMPLES < 1 or SHUTTER_SAMPLES % 2 == 0:
    raise ValueError("SHUTTER_SAMPLES must be a positive odd integer")
print("Bake-off:", BAKEOFF_ID, "| native frames", SEGMENT_START, "through", SEGMENT_END)
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

RUNTIME_ROOT = Path("/content/stanford_rife_bakeoff")
RUNTIME_OUTPUT = RUNTIME_ROOT / "outputs"
RUNTIME_MODELS = RUNTIME_ROOT / "models"
RIFE_REPO = RUNTIME_ROOT / "Practical-RIFE"

SOURCE_VIDEO = DRIVE_SOURCE_POST / "02_post_stabilization_720p16.mp4"
NATIVE_16 = RUNTIME_OUTPUT / "A_native_column_sweep_720p16.mp4"
NATIVE_HOLD_32 = RUNTIME_OUTPUT / "A_native_hold_column_sweep_720p32.mp4"
RIFE_422_32 = RUNTIME_OUTPUT / "B_rife422lite_column_sweep_720p32.mp4"
RIFE_426_32 = RUNTIME_OUTPUT / "C_rife426_column_sweep_720p32.mp4"
RIFE_RETIMED_32 = RUNTIME_OUTPUT / "D_rife426_retimed_shutter_column_sweep_720p32.mp4"
FOUR_UP = RUNTIME_OUTPUT / "E_four_up_interpolation_bakeoff_720p32.mp4"
MIDPOINT_SHEET = RUNTIME_OUTPUT / "rife_midpoint_inspection.jpg"
CADENCE_SHEET = RUNTIME_OUTPUT / "rife_cadence_inspection.jpg"
METRICS_PATH = RUNTIME_OUTPUT / "bakeoff_metrics.json"
MANIFEST_PATH = RUNTIME_OUTPUT / "bakeoff_manifest.json"

for path in (DRIVE_BAKEOFF, RUNTIME_OUTPUT, RUNTIME_MODELS):
    path.mkdir(parents=True, exist_ok=True)

probe = DRIVE_BAKEOFF / f".write-probe-{uuid.uuid4().hex}"
probe.write_text(f"rife bakeoff {time.time_ns()}\n", encoding="utf-8")
if not probe.read_text(encoding="utf-8").startswith("rife bakeoff"):
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

threading.Thread(target=hard_cutoff, name="rife-bakeoff-cutoff", daemon=True).start()

def disconnect_after_cell_error(result):
    failure = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
    if failure is not None and AUTO_DISCONNECT_ON_ERROR:
        disconnect_runtime("uncaught notebook error", failure=failure)

get_ipython().events.register("post_run_cell", disconnect_after_cell_error)

print("Source:", SOURCE_VIDEO)
print("Durable output:", DRIVE_BAKEOFF)
print("RIFE repositories and weights remain ephemeral")
'''


UTILITIES_AND_SOURCE = r'''
try:
    import cv2
    import numpy as np
    import torch
    import torch.nn.functional as F
    from scipy.signal import savgol_filter
except ImportError:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet",
        "opencv-python-headless>=4.10,<5", "scipy>=1.13,<2",
    ])
    import cv2
    import numpy as np
    import torch
    import torch.nn.functional as F
    from scipy.signal import savgol_filter

for binary in ("git", "ffmpeg", "ffprobe"):
    if shutil.which(binary) is None:
        raise RuntimeError(f"Missing binary: {binary}")
if not torch.cuda.is_available():
    raise RuntimeError("Select a Colab T4, L4, V100, or A100 GPU runtime and rerun")
print("GPU:", torch.cuda.get_device_name(0), "| VRAM GiB:", round(torch.cuda.get_device_properties(0).total_memory / 2**30, 2))

def sha256_file(path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()

def atomic_publish(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(source)
    temporary = destination.with_name(destination.name + f".part-{uuid.uuid4().hex}")
    shutil.copy2(source, temporary)
    if sha256_file(temporary) != digest:
        temporary.unlink(missing_ok=True)
        raise RuntimeError(f"Drive copy hash mismatch: {destination.name}")
    os.replace(temporary, destination)
    if sha256_file(destination) != digest:
        raise RuntimeError(f"Published Drive hash mismatch: {destination.name}")
    return digest

def run(command):
    print("+", " ".join(map(str, command)))
    return subprocess.run(list(map(str, command)), check=True, capture_output=True, text=True)

def probe_video(path):
    result = run([
        "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames,duration",
        "-of", "json", path,
    ])
    stream = json.loads(result.stdout)["streams"][0]
    numerator, denominator = map(int, stream["avg_frame_rate"].split("/"))
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "fps": numerator / denominator,
        "frames": int(stream["nb_read_frames"]),
        "duration": float(stream["duration"]),
    }

def decode_bgr(path):
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Cannot decode {path}")
    frames = []
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        frames.append(frame)
    capture.release()
    if not frames:
        raise RuntimeError(f"Decoded zero frames from {path}")
    return frames

def encode_bgr(frames, fps, destination, *, crf=14, gop=16):
    height, width = frames[0].shape[:2]
    command = [
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
        "-s", f"{width}x{height}", "-r", str(fps), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf),
        "-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0", "-bf", "0",
        "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(destination),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        for frame in frames:
            if frame.shape != frames[0].shape or frame.dtype != np.uint8:
                raise RuntimeError("Frame contract changed while encoding")
            process.stdin.write(np.ascontiguousarray(frame).tobytes())
        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        return_code = process.wait()
    except Exception:
        process.kill()
        raise
    if return_code:
        raise RuntimeError(f"ffmpeg encoding failed ({return_code}):\n{stderr[-4000:]}")

if not SOURCE_VIDEO.is_file():
    raise RuntimeError(f"Missing persisted stabilized source: {SOURCE_VIDEO}")
source_probe = probe_video(SOURCE_VIDEO)
expected_source = (SOURCE_WIDTH, SOURCE_HEIGHT, SOURCE_FPS, 81)
actual_source = (
    source_probe["width"], source_probe["height"],
    round(source_probe["fps"]), source_probe["frames"],
)
if actual_source != expected_source:
    raise RuntimeError(f"Unexpected stabilized source contract: {source_probe}")

all_source_frames = decode_bgr(SOURCE_VIDEO)
segment_frames = all_source_frames[SEGMENT_START:SEGMENT_END + 1]
expected_segment_frames = SEGMENT_END - SEGMENT_START + 1
if len(segment_frames) != expected_segment_frames:
    raise RuntimeError("Could not extract complete bake-off segment")

encode_bgr(segment_frames, SOURCE_FPS, NATIVE_16, crf=13, gop=16)
native_hold_frames = []
for frame in segment_frames[:-1]:
    native_hold_frames.extend([frame, frame])
native_hold_frames.append(segment_frames[-1])
encode_bgr(native_hold_frames, OUTPUT_FPS, NATIVE_HOLD_32, crf=13, gop=4)
print("Segment native frames:", len(segment_frames), "| synchronized 32 fps frames:", len(native_hold_frames))
display(Video(str(NATIVE_16), embed=True, width=960))
'''


RIFE_SETUP = r'''
try:
    import gdown
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "gdown==6.1.0"])
    import gdown

def download_gdrive_model(name, record):
    archive = RUNTIME_MODELS / f"{name}.zip"
    if archive.is_file() and archive.stat().st_size == record["bytes"]:
        if sha256_file(archive) == record["sha256"]:
            print("Using verified runtime model:", name)
            return archive
        archive.unlink()
    for attempt in range(1, 5):
        try:
            archive.unlink(missing_ok=True)
            result = gdown.download(id=record["gdrive_id"], output=str(archive), quiet=False)
            if result is None or not archive.is_file():
                raise RuntimeError("gdown returned no model file")
            if archive.stat().st_size != record["bytes"]:
                raise RuntimeError(f"size {archive.stat().st_size} != {record['bytes']}")
            digest = sha256_file(archive)
            if digest != record["sha256"]:
                archive.unlink(missing_ok=True)
                raise RuntimeError(f"hash mismatch: {digest}")
            return archive
        except Exception as exc:
            if attempt == 4:
                raise RuntimeError(f"Could not acquire verified {name}: {exc}") from exc
            delay = 2 ** (attempt - 1)
            print(f"{name} download attempt {attempt} failed; retrying in {delay}s: {exc}")
            time.sleep(delay)

def safe_extract_zip(archive_path, destination):
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    root = destination.resolve()
    with zipfile.ZipFile(archive_path) as archive:
        for member in archive.infolist():
            target = (root / member.filename).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Unsafe model archive path: {member.filename}")
        archive.extractall(destination)
    train_log = destination / "train_log"
    for required in ("RIFE_HDv3.py", "IFNet_HDv3.py", "flownet.pkl"):
        if not (train_log / required).is_file():
            raise RuntimeError(f"{destination.name} is missing train_log/{required}")
    return destination

if RIFE_REPO.exists():
    shutil.rmtree(RIFE_REPO)
run(["git", "clone", "--quiet", RIFE_REPO_URL, RIFE_REPO])
run(["git", "-C", RIFE_REPO, "checkout", "--quiet", RIFE_REPO_COMMIT])
resolved_commit = run(["git", "-C", RIFE_REPO, "rev-parse", "HEAD"]).stdout.strip()
if resolved_commit != RIFE_REPO_COMMIT:
    raise RuntimeError(f"Practical-RIFE commit mismatch: {resolved_commit}")

MODEL_DIRS = {}
for name, record in RIFE_MODELS.items():
    archive = download_gdrive_model(name, record)
    MODEL_DIRS[name] = safe_extract_zip(archive, RUNTIME_MODELS / name)

sys.path.insert(0, str(RIFE_REPO))
torch.set_grad_enabled(False)
torch.backends.cudnn.enabled = True
torch.backends.cudnn.benchmark = True

def load_rife(model_root):
    for key in list(sys.modules):
        if key == "train_log" or key.startswith("train_log."):
            del sys.modules[key]
    sys.path.insert(0, str(model_root))
    importlib.invalidate_caches()
    module = importlib.import_module("train_log.RIFE_HDv3")
    model = module.Model()
    model.load_model(str(model_root / "train_log"), -1)
    model.eval()
    sys.path.remove(str(model_root))
    return model

def dispose_rife(model):
    model.flownet.to("cpu")
    for key in list(sys.modules):
        if key == "train_log" or key.startswith("train_log."):
            del sys.modules[key]
    del model
    gc.collect()
    torch.cuda.empty_cache()
    return None

def rife_frame_at_position(model, frames, position, cache=None):
    position = float(np.clip(position, 0.0, len(frames) - 1))
    left = min(int(math.floor(position)), len(frames) - 1)
    right = min(left + 1, len(frames) - 1)
    timestep = position - left
    if right == left or timestep < 1e-6:
        return frames[left].copy()
    if timestep > 1.0 - 1e-6:
        return frames[right].copy()
    key = (left, round(timestep, 6))
    if cache is not None and key in cache:
        return cache[key].copy()

    rgb0 = cv2.cvtColor(frames[left], cv2.COLOR_BGR2RGB)
    rgb1 = cv2.cvtColor(frames[right], cv2.COLOR_BGR2RGB)
    tensor0 = torch.from_numpy(np.ascontiguousarray(rgb0.transpose(2, 0, 1))).cuda().unsqueeze(0).float() / 255.0
    tensor1 = torch.from_numpy(np.ascontiguousarray(rgb1.transpose(2, 0, 1))).cuda().unsqueeze(0).float() / 255.0
    height, width = rgb0.shape[:2]
    multiple = 128
    padded_height = math.ceil(height / multiple) * multiple
    padded_width = math.ceil(width / multiple) * multiple
    padding = (0, padded_width - width, 0, padded_height - height)
    tensor0 = F.pad(tensor0, padding)
    tensor1 = F.pad(tensor1, padding)
    with torch.inference_mode():
        output = model.inference(tensor0, tensor1, timestep, 1.0)
    rgb = (
        output[0, :, :height, :width].clamp(0, 1).mul(255).add(0.5)
        .byte().cpu().numpy().transpose(1, 2, 0)
    )
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    if cache is not None:
        cache[key] = bgr.copy()
    return bgr

print("Practical-RIFE commit and both official model archives verified")
'''


STANDARD_VARIANTS = r'''
standard_positions = np.linspace(0.0, len(segment_frames) - 1, 2 * len(segment_frames) - 1)

def render_positions(model, positions, label):
    cache = {}
    output = []
    for index, position in enumerate(positions):
        output.append(rife_frame_at_position(model, segment_frames, position, cache))
        if index == 0 or (index + 1) % 10 == 0 or index + 1 == len(positions):
            print(f"{label}: {index + 1}/{len(positions)}")
    return output

model_422 = load_rife(MODEL_DIRS["rife422lite"])
rife_422_frames = render_positions(model_422, standard_positions, "RIFE 4.22-lite")
model_422 = dispose_rife(model_422)
encode_bgr(rife_422_frames, OUTPUT_FPS, RIFE_422_32, crf=13, gop=4)

model_426 = load_rife(MODEL_DIRS["rife426"])
rife_426_frames = render_positions(model_426, standard_positions, "RIFE 4.26")
encode_bgr(rife_426_frames, OUTPUT_FPS, RIFE_426_32, crf=13, gop=4)

print("Standard candidates rendered. Keeping RIFE 4.26 loaded for retimed shutter pass.")
'''


RETIME_COMPARE_AND_QA = r'''
def analysis_gray(frame, width=480):
    height = round(frame.shape[0] * width / frame.shape[1])
    small = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

def robust_pair_motion(frame0, frame1):
    gray0, gray1 = analysis_gray(frame0), analysis_gray(frame1)
    points = cv2.goodFeaturesToTrack(gray0, maxCorners=1400, qualityLevel=0.008, minDistance=6, blockSize=7)
    if points is None or len(points) < 30:
        return float(np.mean(np.abs(gray0.astype(np.float32) - gray1.astype(np.float32))))
    moved, status, error = cv2.calcOpticalFlowPyrLK(
        gray0, gray1, points, None, winSize=(25, 25), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01),
    )
    valid = (status.reshape(-1) == 1) & (error.reshape(-1) < 30.0)
    old, new = points.reshape(-1, 2)[valid], moved.reshape(-1, 2)[valid]
    if len(old) < 24:
        return float(np.mean(np.abs(gray0.astype(np.float32) - gray1.astype(np.float32))))
    matrix, mask = cv2.estimateAffinePartial2D(
        old, new, method=cv2.RANSAC, ransacReprojThreshold=2.0,
        maxIters=3000, confidence=0.995, refineIters=20,
    )
    if matrix is None:
        return float(np.median(np.linalg.norm(new - old, axis=1)))
    a, b = float(matrix[0, 0]), float(matrix[1, 0])
    angle = abs(math.atan2(b, a))
    translation = math.hypot(float(matrix[0, 2]), float(matrix[1, 2]))
    return float(max(translation + angle * gray0.shape[1] * 0.35, 1e-4))

pair_motion = np.asarray([
    robust_pair_motion(all_source_frames[index], all_source_frames[index + 1])
    for index in range(len(all_source_frames) - 1)
], dtype=np.float64)
raw_progress = np.concatenate([[0.0], np.cumsum(np.maximum(pair_motion, 1e-4))])
window = min(PROGRESS_SMOOTHING_WINDOW, len(raw_progress) if len(raw_progress) % 2 else len(raw_progress) - 1)
smoothed_progress = savgol_filter(raw_progress, window_length=window, polyorder=3, mode="interp")
smoothed_progress = np.maximum.accumulate(smoothed_progress)

native_axis = np.arange(len(all_source_frames), dtype=np.float64)
segment_raw_start = raw_progress[SEGMENT_START]
segment_raw_end = raw_progress[SEGMENT_END]
segment_smooth_start = smoothed_progress[SEGMENT_START]
segment_smooth_end = smoothed_progress[SEGMENT_END]

def retimed_global_position(native_position):
    smooth_value = float(np.interp(native_position, native_axis, smoothed_progress))
    fraction = (smooth_value - segment_smooth_start) / max(segment_smooth_end - segment_smooth_start, 1e-9)
    desired_progress = segment_raw_start + np.clip(fraction, 0.0, 1.0) * (segment_raw_end - segment_raw_start)
    global_position = float(np.interp(desired_progress, raw_progress, native_axis))
    return float(np.clip(global_position, SEGMENT_START, SEGMENT_END))

def srgb_to_linear(image):
    image = image.astype(np.float32) / 255.0
    return np.where(image <= 0.04045, image / 12.92, ((image + 0.055) / 1.055) ** 2.4)

def linear_to_srgb(image):
    image = np.clip(image, 0.0, 1.0)
    srgb = np.where(image <= 0.0031308, image * 12.92, 1.055 * image ** (1 / 2.4) - 0.055)
    return np.clip(srgb * 255.0 + 0.5, 0, 255).astype(np.uint8)

retime_cache = {}
retimed_shutter_frames = []
output_count = 2 * len(segment_frames) - 1
output_native_positions = np.linspace(SEGMENT_START, SEGMENT_END, output_count)
output_step_native = SOURCE_FPS / OUTPUT_FPS
exposure_width_native = output_step_native * (SHUTTER_ANGLE_DEGREES / 360.0)
sample_offsets = np.linspace(-0.5, 0.5, SHUTTER_SAMPLES) * exposure_width_native

for output_index, native_position in enumerate(output_native_positions):
    samples_linear = []
    for offset in sample_offsets:
        sample_native_position = float(np.clip(native_position + offset, SEGMENT_START, SEGMENT_END))
        source_global_position = retimed_global_position(sample_native_position)
        source_segment_position = source_global_position - SEGMENT_START
        sample = rife_frame_at_position(model_426, segment_frames, source_segment_position, retime_cache)
        samples_linear.append(srgb_to_linear(sample))
    retimed_shutter_frames.append(linear_to_srgb(np.mean(samples_linear, axis=0)))
    if output_index == 0 or (output_index + 1) % 10 == 0 or output_index + 1 == output_count:
        print(f"RIFE 4.26 retimed shutter: {output_index + 1}/{output_count}")

model_426 = dispose_rife(model_426)
encode_bgr(retimed_shutter_frames, OUTPUT_FPS, RIFE_RETIMED_32, crf=13, gop=4)

candidate_frames = {
    "A  Native 16 fps (held)": native_hold_frames,
    "B  RIFE 4.22-lite": rife_422_frames,
    "C  RIFE 4.26": rife_426_frames,
    "D  RIFE 4.26 + retime + shutter": retimed_shutter_frames,
}
if len({len(frames) for frames in candidate_frames.values()}) != 1:
    raise RuntimeError("Candidate lengths differ")

def labeled_panel(frame, label, width=640, height=360):
    panel = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    cv2.rectangle(panel, (0, 0), (width, 38), (13, 13, 13), -1)
    cv2.putText(panel, label, (14, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (255, 255, 255), 1, cv2.LINE_AA)
    return panel

four_up_frames = []
labels = list(candidate_frames)
for index in range(output_count):
    panels = [labeled_panel(candidate_frames[label][index], label) for label in labels]
    four_up_frames.append(np.vstack([np.hstack(panels[:2]), np.hstack(panels[2:])]))
encode_bgr(four_up_frames, OUTPUT_FPS, FOUR_UP, crf=15, gop=4)

segment_pair_motion = pair_motion[SEGMENT_START:SEGMENT_END]
hard_pairs_local = np.argsort(segment_pair_motion)[-6:][::-1]
midpoint_rows = []
for local_pair in hard_pairs_local:
    output_mid = 2 * int(local_pair) + 1
    panels = []
    source_pair = f"source pair {SEGMENT_START + int(local_pair)}"
    for label in labels:
        panel = labeled_panel(candidate_frames[label][output_mid], f"{source_pair} | {label}", 400, 225)
        panels.append(panel)
    midpoint_rows.append(np.hstack(panels))
midpoint_sheet = np.vstack(midpoint_rows)
if not cv2.imwrite(str(MIDPOINT_SHEET), midpoint_sheet, [cv2.IMWRITE_JPEG_QUALITY, 96]):
    raise RuntimeError("Could not write midpoint sheet")

center_output = 2 * int(hard_pairs_local[0]) + 1
inspection_indices = list(range(max(0, center_output - 5), min(output_count, center_output + 6)))
cadence_rows = []
for label in labels:
    panels = [labeled_panel(candidate_frames[label][idx], f"{label} | frame {idx}", 240, 135) for idx in inspection_indices]
    cadence_rows.append(np.hstack(panels))
cadence_sheet = np.vstack(cadence_rows)
if not cv2.imwrite(str(CADENCE_SHEET), cadence_sheet, [cv2.IMWRITE_JPEG_QUALITY, 96]):
    raise RuntimeError("Could not write cadence sheet")

def flow_speed_series(frames):
    speeds = []
    for frame0, frame1 in zip(frames, frames[1:]):
        gray0 = analysis_gray(frame0, 320)
        gray1 = analysis_gray(frame1, 320)
        flow = cv2.calcOpticalFlowFarneback(gray0, gray1, None, 0.5, 4, 21, 4, 7, 1.5, 0)
        speeds.append(float(np.median(np.linalg.norm(flow, axis=2))))
    return np.asarray(speeds)

metrics = {
    "status": "visual_review_required",
    "warning": "Scalar metrics cannot certify neural interpolation quality; judge the full-speed four-up video and 1:1 sheets.",
    "source_segment": {"first_native_frame": SEGMENT_START, "last_native_frame": SEGMENT_END},
    "candidates": {},
}
for label, frames in candidate_frames.items():
    speeds = flow_speed_series(frames)
    alternation = np.abs(np.diff(speeds)) / (0.5 * (speeds[:-1] + speeds[1:]) + 1e-6)
    sharpness = np.asarray([float(cv2.Laplacian(analysis_gray(frame, 320), cv2.CV_32F).var()) for frame in frames])
    metrics["candidates"][label] = {
        "frames": len(frames),
        "median_flow": float(np.median(speeds)),
        "p95_flow": float(np.percentile(speeds, 95)),
        "median_flow_alternation": float(np.median(alternation)),
        "median_sharpness_step_ratio": float(np.median(np.abs(np.diff(sharpness)) / (sharpness[:-1] + 1e-6))),
    }

METRICS_PATH.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(metrics, indent=2))
display(IPImage(filename=str(MIDPOINT_SHEET)))
display(IPImage(filename=str(CADENCE_SHEET)))
display(Video(str(FOUR_UP), embed=True, width=1000))
'''


FINALIZE = r'''
expected_32_frames = 2 * expected_segment_frames - 1
video_contracts = {
    NATIVE_16: (SOURCE_FPS, expected_segment_frames),
    NATIVE_HOLD_32: (OUTPUT_FPS, expected_32_frames),
    RIFE_422_32: (OUTPUT_FPS, expected_32_frames),
    RIFE_426_32: (OUTPUT_FPS, expected_32_frames),
    RIFE_RETIMED_32: (OUTPUT_FPS, expected_32_frames),
    FOUR_UP: (OUTPUT_FPS, expected_32_frames),
}
probes = {}
for path, (fps, frames) in video_contracts.items():
    probe = probe_video(path)
    if (probe["width"], probe["height"], round(probe["fps"]), probe["frames"]) != (
        SOURCE_WIDTH, SOURCE_HEIGHT, fps, frames
    ):
        raise RuntimeError(f"Invalid output contract for {path.name}: {probe}")
    probes[path.name] = probe

deliverables = (
    NATIVE_16, NATIVE_HOLD_32, RIFE_422_32, RIFE_426_32,
    RIFE_RETIMED_32, FOUR_UP, MIDPOINT_SHEET, CADENCE_SHEET, METRICS_PATH,
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
    "retimed_shutter": {
        "model": "RIFE 4.26",
        "progress_smoothing_window": window,
        "shutter_samples": SHUTTER_SAMPLES,
        "shutter_angle_degrees": SHUTTER_ANGLE_DEGREES,
        "method": "monotonic optical-flow progress remap plus linear-light temporal integration",
    },
    "visual_review": {
        "four_up": FOUR_UP.name,
        "midpoint_sheet": MIDPOINT_SHEET.name,
        "cadence_sheet": CADENCE_SHEET.name,
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
MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
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
    "bundle": {"path": str(DRIVE_BAKEOFF / bundle.name), "sha256": bundle_digest},
    "four_up_comparison": str(DRIVE_BAKEOFF / FOUR_UP.name),
    "models_persisted": False,
    "next_gate": "Eric judges motion cadence and pixel stability; no automatic winner is selected",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

for path in (DRIVE_BAKEOFF / MANIFEST_PATH.name, DRIVE_BAKEOFF / bundle.name, success):
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Final persistence check failed: {path}")

print("COMPLETE:", DRIVE_BAKEOFF)
print("Four-up comparison:", DRIVE_BAKEOFF / FOUR_UP.name)
print("Review bundle:", DRIVE_BAKEOFF / bundle.name)

if AUTO_DISCONNECT_ON_SUCCESS:
    disconnect_runtime("RIFE bake-off completed and all artifacts verified on Drive")
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
        nbformat.v4.new_code_cell(UTILITIES_AND_SOURCE.strip()),
        nbformat.v4.new_code_cell(RIFE_SETUP.strip()),
        nbformat.v4.new_code_cell(STANDARD_VARIANTS.strip()),
        nbformat.v4.new_code_cell(RETIME_COMPARE_AND_QA.strip()),
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
