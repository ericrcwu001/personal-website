#!/usr/bin/env python3
"""Build the standalone Wan Stanford stabilization/FILM Colab notebook."""

from __future__ import annotations

import ast
from pathlib import Path

import nbformat


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "wan21_stanford_whip_postprocess_colab.ipynb"


TITLE = r'''
# Stanford Wan post-processing — stabilization + FILM 32 fps scroll master

This notebook starts from the **already persisted** speed-ramped Wan 2.1 Stanford render. It
does not download or run Wan again.

It creates and persists the complete review chain:

1. the native-endpoint 16 fps clip **before** stabilization;
2. the same clip **after** constrained residual stabilization;
3. a side-by-side before/after review video;
4. the stabilized, Google FILM-interpolated 32 fps GOP-4 scroll master;
5. a FILM proof triptych, validation report, and worst-midpoint contact sheet.

The new whip generation keeps Wan's native first and last frames; it does not
inject exact photographs after generation, so no endpoint removal is needed.
Stabilization is deliberately capped so it corrects high-frequency shake without
flattening the intended rightward track and turn into the arcade. Google FILM
runs only after stabilization. FILM is a free, local TensorFlow model trained for
large motion and disocclusions; no paid API is called and the model is not saved
to Drive.

Unlike FFmpeg `minterpolate`, every even frame in the 32 fps working sequence is
an exact native frame from the persisted stabilized 16 fps master. Only the odd
midpoints are synthesized. The notebook automatically checks native-frame
preservation, temporal midpoint balance, block-boundary excess, edge inflation,
sharpness collapse, and forward/reverse FILM agreement on high-risk pairs.

No typography is baked into the video. `Stanford Class of 2029` and the social
icons remain accessible HTML/CSS elements in the website and can be masked by a
separate foreground matte.
'''


SETTINGS = r'''
# The completed Wan experiment already stored in Google Drive.
SOURCE_EXPERIMENT_ID = "stanford_wan21_flf2v_whip_720p_v2"
SOURCE_SEED = 95231
POSTPROCESS_ID = "stabilized_film32_whip_v3"
REMOVE_FORCED_ENDPOINTS = False

SOURCE_WIDTH, SOURCE_HEIGHT = 1280, 720
SOURCE_FPS = 16
OUTPUT_FPS = 32

# Official Google FILM model mirrored by Kaggle. The archive is downloaded only
# into the ephemeral runtime, verified byte-for-byte, and discarded with it.
FILM_MODEL_URL = "https://www.kaggle.com/api/v1/models/google/film/TensorFlow2/film/1/download"
FILM_MODEL_BYTES = 128_259_939
FILM_MODEL_SHA256 = "f1d044762913d2dba32a927c12b8b03384c04efe9bc9dd4cf6cbc13f98c3ded2"
FILM_ALIGNMENT = 64
REQUIRE_GPU = True

# Residual-only stabilization. These hard caps prevent the cleanup pass from
# fighting the intentional camera move.
SMOOTHING_WINDOW = 9
MAX_TRANSLATION_CORRECTION_PX = 3.5
MAX_ROTATION_CORRECTION_DEG = 0.18
# Scale correction and a permanent stabilization crop both increased measured
# translational jerk on the real Stanford shot. Keep them disabled; the sub-4px
# reflected border is hidden naturally by the website's full-bleed object-fit.
MAX_SCALE_CORRECTION = 0.0
EDGE_ZOOM = 1.0

# Billing protection. FILM needs a Colab GPU; T4 and A100 are both supported.
AUTO_DISCONNECT_ON_SUCCESS = True
AUTO_DISCONNECT_ON_ERROR = True
HARD_CUTOFF_HOURS = 1.5

if SOURCE_FPS * 2 != OUTPUT_FPS:
    raise ValueError("This notebook is validated for exact 2x interpolation")
if SMOOTHING_WINDOW < 5 or SMOOTHING_WINDOW % 2 == 0:
    raise ValueError("SMOOTHING_WINDOW must be an odd integer of at least 5")
print("Post-process:", SOURCE_EXPERIMENT_ID, "->", POSTPROCESS_ID)
'''


SETUP = r'''
# Mount Drive and establish durable/runtime paths.
from google.colab import drive
from google.colab import drive as colab_drive, runtime as colab_runtime
from pathlib import Path
from IPython.display import Image as IPImage, Video, display
import hashlib, json, math, os, platform, shutil, subprocess, sys, tarfile, threading, time, uuid, zipfile

drive.mount("/content/drive", force_remount=False)

DRIVE_ROOT = Path("/content/drive/MyDrive/Personal_Website_Wan21_FLF2V")
DRIVE_EXPERIMENT = DRIVE_ROOT / "experiments" / SOURCE_EXPERIMENT_ID
DRIVE_CANDIDATE = DRIVE_EXPERIMENT / "candidate" / str(SOURCE_SEED)
DRIVE_POST = DRIVE_EXPERIMENT / "postprocess" / POSTPROCESS_ID

RUNTIME_ROOT = Path("/content/wan21_stanford_postprocess")
RUNTIME_POST = RUNTIME_ROOT / POSTPROCESS_ID
DRIVE_POST.mkdir(parents=True, exist_ok=True)
RUNTIME_POST.mkdir(parents=True, exist_ok=True)

SOURCE_VIDEO = DRIVE_CANDIDATE / "stanford_wan21_flf2v_720p16.mp4"
PRE_STABILIZATION = RUNTIME_POST / "01_pre_stabilization_720p16.mp4"
POST_STABILIZATION = RUNTIME_POST / "02_post_stabilization_720p16.mp4"
COMPARISON = RUNTIME_POST / "03_before_after_stabilization_720p16.mp4"
SCROLL_MASTER = RUNTIME_POST / "04_stabilized_film_interpolated_scroll_gop4_720p32.mp4"
FILM_PROOF = RUNTIME_POST / "film_high_motion_proof_triptych.jpg"
FILM_VALIDATION = RUNTIME_POST / "film_midpoint_validation.json"
FILM_VALIDATION_SHEET = RUNTIME_POST / "film_worst_midpoints_contact_sheet.jpg"
DIAGNOSTIC_PLOT = RUNTIME_POST / "stabilization_diagnostics.png"
MANIFEST_PATH = RUNTIME_POST / "postprocess_manifest.json"

FILM_ARCHIVE = RUNTIME_ROOT / "film-tensorflow2-film-v1.tar.gz"
FILM_MODEL_DIR = RUNTIME_ROOT / "film_model"

probe = DRIVE_POST / f".write-probe-{uuid.uuid4().hex}"
probe.write_text(f"wan postprocess persistence {time.time_ns()}\n", encoding="utf-8")
if not probe.read_text(encoding="utf-8").startswith("wan postprocess persistence"):
    raise RuntimeError("Google Drive persistence check failed")
probe.unlink()

_shutdown_started = threading.Event()

def _disconnect(reason, *, failure=None):
    if _shutdown_started.is_set():
        return
    _shutdown_started.set()
    payload = {"reason": reason, "time": time.time()}
    if failure is not None:
        payload["failure"] = str(failure)
    try:
        (DRIVE_POST / "runtime_shutdown.json").write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        colab_drive.flush_and_unmount()
    finally:
        time.sleep(2)
        colab_runtime.unassign()

def _hard_cutoff():
    if _shutdown_started.wait(HARD_CUTOFF_HOURS * 3600):
        return
    _disconnect(f"hard cutoff after {HARD_CUTOFF_HOURS:.1f} hours")
threading.Thread(target=_hard_cutoff, name="postprocess-hard-cutoff", daemon=True).start()

def _disconnect_after_cell_error(result):
    failure = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
    if failure is not None and AUTO_DISCONNECT_ON_ERROR:
        _disconnect("uncaught notebook error", failure=failure)

get_ipython().events.register("post_run_cell", _disconnect_after_cell_error)

print("Source:", SOURCE_VIDEO)
print("Durable outputs:", DRIVE_POST)
print("FILM model cache is ephemeral; only media and reports persist")
'''


PREFLIGHT_AND_UTILITIES = r'''
# Verify the source and define integrity/video helpers.
try:
    import cv2
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.signal import savgol_filter
except ImportError:
    subprocess.check_call([
        sys.executable, "-m", "pip", "install", "--quiet",
        "opencv-python-headless>=4.10,<5", "scipy>=1.13,<2", "matplotlib>=3.8,<4",
    ])
    import cv2
    import matplotlib.pyplot as plt
    import numpy as np
    from scipy.signal import savgol_filter

for binary in ("ffmpeg", "ffprobe"):
    if shutil.which(binary) is None:
        raise RuntimeError(f"Missing binary: {binary}")
if not SOURCE_VIDEO.is_file():
    raise RuntimeError(
        "Missing completed Wan source video:\n"
        f"{SOURCE_VIDEO}\n"
        "The generation notebook must finish and persist its candidate first."
    )

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

def maximum_keyframe_gap(path):
    result = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_frames",
        "-show_entries", "frame=key_frame", "-of", "json", path,
    ])
    frames = json.loads(result.stdout)["frames"]
    keyframes = [index for index, frame in enumerate(frames) if int(frame.get("key_frame", 0)) == 1]
    total = len(frames)
    boundaries = keyframes + [total]
    return max(b - a for a, b in zip(boundaries, boundaries[1:]))

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
                raise RuntimeError("Frame shape/dtype changed during encoding")
            process.stdin.write(np.ascontiguousarray(frame).tobytes())
        process.stdin.close()
        stderr = process.stderr.read().decode("utf-8", errors="replace")
        return_code = process.wait()
    except Exception:
        process.kill()
        raise
    if return_code:
        raise RuntimeError(f"ffmpeg encoding failed ({return_code}):\n{stderr[-4000:]}")

source_probe = probe_video(SOURCE_VIDEO)
if (source_probe["width"], source_probe["height"], round(source_probe["fps"]), source_probe["frames"]) != (
    SOURCE_WIDTH, SOURCE_HEIGHT, SOURCE_FPS, 81
):
    raise RuntimeError(f"Unexpected source contract: {source_probe}")
print("Source verified:", json.dumps(source_probe, indent=2))
print("OpenCV:", cv2.__version__, "| NumPy:", np.__version__)
'''


TRIM_AND_PERSIST = r'''
# Keep native model endpoints (or trim legacy injected endpoints when explicitly requested) and persist the pre-stabilization master.
source_frames = decode_bgr(SOURCE_VIDEO)
trimmed_frames = source_frames[1:-1] if REMOVE_FORCED_ENDPOINTS else source_frames
expected_pre_frames = 79 if REMOVE_FORCED_ENDPOINTS else 81
if len(trimmed_frames) != expected_pre_frames:
    raise RuntimeError(f"Expected {expected_pre_frames} pre-stabilization frames; found {len(trimmed_frames)}")

encode_bgr(trimmed_frames, SOURCE_FPS, PRE_STABILIZATION, crf=13, gop=16)
pre_probe = probe_video(PRE_STABILIZATION)
if pre_probe["frames"] != expected_pre_frames or round(pre_probe["fps"]) != SOURCE_FPS:
    raise RuntimeError(f"Invalid pre-stabilization master: {pre_probe}")

pre_digest = atomic_publish(PRE_STABILIZATION, DRIVE_POST / PRE_STABILIZATION.name)
# Stabilize the exact decoded pixels of the persisted pre-stabilization master.
# This keeps the before/after motion estimate on one codec baseline instead of
# deriving corrections from a slightly different in-memory source decode.
trimmed_frames = decode_bgr(PRE_STABILIZATION)
print("Persisted before stabilization:", DRIVE_POST / PRE_STABILIZATION.name)
display(Video(str(PRE_STABILIZATION), embed=True, width=960))
'''


STABILIZE = r'''
# Estimate the camera path, smooth only its high-frequency residual, and hard-cap corrections.
def estimate_frame_motion(previous_bgr, current_bgr, analysis_width=640):
    source_height, source_width = previous_bgr.shape[:2]
    analysis_height = round(source_height * analysis_width / source_width)
    previous = cv2.resize(previous_bgr, (analysis_width, analysis_height), interpolation=cv2.INTER_AREA)
    current = cv2.resize(current_bgr, (analysis_width, analysis_height), interpolation=cv2.INTER_AREA)
    previous_gray = cv2.cvtColor(previous, cv2.COLOR_BGR2GRAY)
    current_gray = cv2.cvtColor(current, cv2.COLOR_BGR2GRAY)

    points = cv2.goodFeaturesToTrack(
        previous_gray, maxCorners=1400, qualityLevel=0.008, minDistance=7, blockSize=7
    )
    if points is None or len(points) < 40:
        return None, {"tracked": 0, "inliers": 0, "inlier_ratio": 0.0}

    moved, status, error = cv2.calcOpticalFlowPyrLK(
        previous_gray, current_gray, points, None,
        winSize=(25, 25), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 40, 0.01),
    )
    valid = (
        (status.reshape(-1) == 1)
        & np.isfinite(moved.reshape(-1, 2)).all(axis=1)
        & np.isfinite(error.reshape(-1))
        & (error.reshape(-1) < 30.0)
    )
    old = points.reshape(-1, 2)[valid]
    new = moved.reshape(-1, 2)[valid]
    if len(old) < 30:
        return None, {"tracked": int(len(old)), "inliers": 0, "inlier_ratio": 0.0}

    matrix, inlier_mask = cv2.estimateAffinePartial2D(
        old, new, method=cv2.RANSAC, ransacReprojThreshold=2.0,
        maxIters=3000, confidence=0.995, refineIters=20,
    )
    if matrix is None:
        return None, {"tracked": int(len(old)), "inliers": 0, "inlier_ratio": 0.0}

    inliers = int(inlier_mask.sum()) if inlier_mask is not None else 0
    ratio = inliers / max(len(old), 1)
    a, b = float(matrix[0, 0]), float(matrix[1, 0])
    scale = max(math.hypot(a, b), 1e-6)
    angle = math.atan2(b, a)
    scale_x = source_width / analysis_width
    scale_y = source_height / analysis_height
    motion = np.array([
        float(matrix[0, 2]) * scale_x,
        float(matrix[1, 2]) * scale_y,
        angle,
        math.log(scale),
    ], dtype=np.float64)
    plausible = (
        ratio >= 0.12
        and abs(motion[0]) <= source_width * 0.22
        and abs(motion[1]) <= source_height * 0.22
        and abs(math.degrees(motion[2])) <= 12.0
        and abs(motion[3]) <= math.log(1.12)
    )
    return (motion if plausible else None), {
        "tracked": int(len(old)), "inliers": inliers, "inlier_ratio": float(ratio)
    }

raw_motion = []
tracking_quality = []
fallback_count = 0
for index in range(1, len(trimmed_frames)):
    motion, quality = estimate_frame_motion(trimmed_frames[index - 1], trimmed_frames[index])
    if motion is None:
        fallback_count += 1
        if raw_motion:
            motion = np.median(np.asarray(raw_motion[-min(3, len(raw_motion)):]), axis=0)
        else:
            motion = np.zeros(4, dtype=np.float64)
        quality["fallback"] = True
    else:
        quality["fallback"] = False
    raw_motion.append(motion)
    tracking_quality.append(quality)

raw_motion = np.asarray(raw_motion, dtype=np.float64)
trajectory = np.vstack([np.zeros((1, 4), dtype=np.float64), np.cumsum(raw_motion, axis=0)])
window = min(SMOOTHING_WINDOW, len(trajectory) if len(trajectory) % 2 else len(trajectory) - 1)
smoothed_trajectory = savgol_filter(trajectory, window_length=window, polyorder=2, axis=0, mode="interp")
correction = smoothed_trajectory - trajectory

correction[:, 0] = np.clip(
    correction[:, 0], -MAX_TRANSLATION_CORRECTION_PX, MAX_TRANSLATION_CORRECTION_PX
)
correction[:, 1] = np.clip(
    correction[:, 1], -MAX_TRANSLATION_CORRECTION_PX, MAX_TRANSLATION_CORRECTION_PX
)
translation_norm = np.linalg.norm(correction[:, :2], axis=1)
translation_scale = np.minimum(
    1.0,
    MAX_TRANSLATION_CORRECTION_PX / np.maximum(translation_norm, 1e-9),
)
correction[:, :2] *= translation_scale[:, None]
rotation_limit = math.radians(MAX_ROTATION_CORRECTION_DEG)
correction[:, 2] = np.clip(correction[:, 2], -rotation_limit, rotation_limit)
correction[:, 3] = np.clip(correction[:, 3], -MAX_SCALE_CORRECTION, MAX_SCALE_CORRECTION)

def apply_correction(frame, adjustment):
    height, width = frame.shape[:2]
    dx, dy, angle, log_scale = map(float, adjustment)
    total_scale = EDGE_ZOOM * math.exp(log_scale)
    matrix = cv2.getRotationMatrix2D(
        # estimateAffinePartial2D uses [[cos, -sin], [sin, cos]], while
        # getRotationMatrix2D's image-coordinate convention has the opposite
        # off-diagonal sign. Negate here so the applied residual cancels the
        # measured high-frequency rotation instead of amplifying it.
        (width / 2.0, height / 2.0), -math.degrees(angle), total_scale
    )
    matrix[0, 2] += dx
    matrix[1, 2] += dy
    return cv2.warpAffine(
        frame, matrix, (width, height), flags=cv2.INTER_LANCZOS4,
        borderMode=cv2.BORDER_REFLECT_101,
    )

stabilized_frames = [
    apply_correction(frame, adjustment)
    for frame, adjustment in zip(trimmed_frames, correction)
]
encode_bgr(stabilized_frames, SOURCE_FPS, POST_STABILIZATION, crf=13, gop=16)
post_probe = probe_video(POST_STABILIZATION)
if post_probe["frames"] != expected_pre_frames or round(post_probe["fps"]) != SOURCE_FPS:
    raise RuntimeError(f"Invalid post-stabilization master: {post_probe}")

post_digest = atomic_publish(POST_STABILIZATION, DRIVE_POST / POST_STABILIZATION.name)

translation_correction = np.linalg.norm(correction[:, :2], axis=1)
rotation_correction_deg = np.abs(np.degrees(correction[:, 2]))
stabilization_metrics = {
    "frames": len(stabilized_frames),
    "smoothing_window": window,
    "fallback_motion_estimates": fallback_count,
    "median_tracking_inlier_ratio": float(np.median([q["inlier_ratio"] for q in tracking_quality])),
    "median_translation_correction_px": float(np.median(translation_correction)),
    "maximum_translation_correction_px": float(np.max(translation_correction)),
    "median_rotation_correction_deg": float(np.median(rotation_correction_deg)),
    "maximum_rotation_correction_deg": float(np.max(rotation_correction_deg)),
    "edge_zoom": EDGE_ZOOM,
    "note": "Corrections are hard-capped; local AI geometry morphing is not treated as camera shake.",
}

fig, axes = plt.subplots(3, 1, figsize=(12, 8), sharex=True)
frame_axis = np.arange(len(trajectory))
axes[0].plot(frame_axis, trajectory[:, 0], alpha=0.45, label="raw x path")
axes[0].plot(frame_axis, smoothed_trajectory[:, 0], label="smoothed x path")
axes[0].set_ylabel("x (px)"); axes[0].legend()
axes[1].plot(frame_axis, trajectory[:, 1], alpha=0.45, label="raw y path")
axes[1].plot(frame_axis, smoothed_trajectory[:, 1], label="smoothed y path")
axes[1].set_ylabel("y (px)"); axes[1].legend()
axes[2].plot(frame_axis, translation_correction, label="applied translation correction")
axes[2].axhline(MAX_TRANSLATION_CORRECTION_PX, color="red", linestyle="--", alpha=0.5)
axes[2].set_ylabel("correction (px)"); axes[2].set_xlabel("frame"); axes[2].legend()
fig.suptitle("Constrained residual stabilization diagnostics")
fig.tight_layout()
fig.savefig(DIAGNOSTIC_PLOT, dpi=160)
plt.close(fig)
atomic_publish(DIAGNOSTIC_PLOT, DRIVE_POST / DIAGNOSTIC_PLOT.name)

print(json.dumps(stabilization_metrics, indent=2))
print("Persisted after stabilization:", DRIVE_POST / POST_STABILIZATION.name)
display(Video(str(POST_STABILIZATION), embed=True, width=960))
'''


INTERPOLATE_AND_ENCODE = r'''
# Persist a before/after stabilization review.
run([
    "ffmpeg", "-y", "-v", "error",
    "-i", PRE_STABILIZATION, "-i", POST_STABILIZATION,
    "-filter_complex",
    "[0:v]setpts=PTS-STARTPTS,scale=640:360[before];"
    "[1:v]setpts=PTS-STARTPTS,scale=640:360[after];"
    "[before][after]hstack=inputs=2",
    "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "16",
    "-g", "16", "-keyint_min", "16", "-sc_threshold", "0", "-bf", "0",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", COMPARISON,
])


# Download and verify the official FILM SavedModel in ephemeral runtime storage.
try:
    import requests
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "requests>=2.31,<3"])
    import requests

def download_verified(url, destination, expected_bytes, expected_sha256, attempts=5):
    destination = Path(destination)
    if destination.is_file() and destination.stat().st_size == expected_bytes:
        if sha256_file(destination) == expected_sha256:
            print("Using verified runtime FILM archive:", destination)
            return destination
        destination.unlink()

    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            offset = destination.stat().st_size if destination.exists() else 0
            headers = {"User-Agent": "wan-stanford-film-colab/1.0"}
            if offset:
                headers["Range"] = f"bytes={offset}-"
            with requests.get(
                url, headers=headers, stream=True, allow_redirects=True,
                timeout=(30, 300),
            ) as response:
                if offset and response.status_code != 206:
                    destination.unlink(missing_ok=True)
                    offset = 0
                response.raise_for_status()
                mode = "ab" if offset and response.status_code == 206 else "wb"
                with open(destination, mode) as handle:
                    for chunk in response.iter_content(chunk_size=8 * 1024 * 1024):
                        if chunk:
                            handle.write(chunk)
            if destination.stat().st_size != expected_bytes:
                raise RuntimeError(
                    f"FILM archive size mismatch: {destination.stat().st_size} != {expected_bytes}"
                )
            digest = sha256_file(destination)
            if digest != expected_sha256:
                destination.unlink(missing_ok=True)
                raise RuntimeError(f"FILM archive hash mismatch: {digest}")
            return destination
        except Exception as exc:
            last_error = exc
            if destination.exists() and destination.stat().st_size > expected_bytes:
                destination.unlink()
            if attempt < attempts:
                delay = 2 ** (attempt - 1)
                print(f"FILM download attempt {attempt} failed; retrying in {delay}s: {exc}")
                time.sleep(delay)
    raise RuntimeError(f"FILM download failed after {attempts} attempts: {last_error}")

download_verified(FILM_MODEL_URL, FILM_ARCHIVE, FILM_MODEL_BYTES, FILM_MODEL_SHA256)
if FILM_MODEL_DIR.exists():
    shutil.rmtree(FILM_MODEL_DIR)
FILM_MODEL_DIR.mkdir(parents=True)
with tarfile.open(FILM_ARCHIVE, "r:gz") as archive:
    root = FILM_MODEL_DIR.resolve()
    members = archive.getmembers()
    for member in members:
        target = (root / member.name).resolve()
        if target != root and root not in target.parents:
            raise RuntimeError(f"Unsafe path in FILM archive: {member.name}")
        if member.issym() or member.islnk():
            raise RuntimeError(f"Links are not allowed in FILM archive: {member.name}")
    try:
        archive.extractall(FILM_MODEL_DIR, members=members, filter="data")
    except TypeError:  # Python < 3.12 fallback after the explicit path/link audit above.
        archive.extractall(FILM_MODEL_DIR, members=members)
for required in ("saved_model.pb", "variables/variables.index", "variables/variables.data-00000-of-00001"):
    if not (FILM_MODEL_DIR / required).is_file():
        raise RuntimeError(f"Incomplete FILM SavedModel: missing {required}")

os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
try:
    import tensorflow as tf
except ImportError as exc:
    raise RuntimeError(
        "TensorFlow is missing from this Colab image. Start a standard Colab GPU runtime and rerun."
    ) from exc

gpus = tf.config.list_physical_devices("GPU")
for gpu in gpus:
    try:
        tf.config.experimental.set_memory_growth(gpu, True)
    except RuntimeError:
        pass
if REQUIRE_GPU and not gpus:
    raise RuntimeError("No TensorFlow GPU detected. Select a T4 or A100 runtime and rerun.")
print("TensorFlow:", tf.__version__, "| GPUs:", [gpu.name for gpu in gpus])

film_model = tf.saved_model.load(str(FILM_MODEL_DIR))

def pad_to_align(batch, align):
    if batch.ndim != 4 or align <= 0:
        raise ValueError("FILM expects NHWC batches and a positive alignment")
    height, width = batch.shape[1:3]
    pad_h = (align - height % align) % align
    pad_w = (align - width % align) % align
    offset_h, offset_w = pad_h // 2, pad_w // 2
    padded = tf.image.pad_to_bounding_box(
        batch, offset_h, offset_w, height + pad_h, width + pad_w
    )
    crop = (offset_h, offset_w, height, width)
    return padded, crop

def film_midpoint_bgr(frame0_bgr, frame1_bgr):
    if frame0_bgr.shape != frame1_bgr.shape:
        raise ValueError("FILM endpoint shapes differ")
    rgb0 = cv2.cvtColor(frame0_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    rgb1 = cv2.cvtColor(frame1_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    batch0, crop = pad_to_align(rgb0[None, ...], FILM_ALIGNMENT)
    batch1, _ = pad_to_align(rgb1[None, ...], FILM_ALIGNMENT)
    result = film_model({
        "x0": batch0,
        "x1": batch1,
        "time": tf.constant([[0.5]], dtype=tf.float32),
    }, training=False)["image"]
    offset_h, offset_w, height, width = crop
    result = tf.image.crop_to_bounding_box(result, offset_h, offset_w, height, width)
    rgb = np.clip(result.numpy()[0] * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

# Decode the persisted post-stabilization master. These exact decoded frames
# become every even frame in the 32 fps working sequence.
post_master_frames = decode_bgr(POST_STABILIZATION)
if len(post_master_frames) != expected_pre_frames:
    raise RuntimeError(f"Unexpected persisted stabilized frame count: {len(post_master_frames)}")

def analysis_gray(frame, width=320):
    height = round(frame.shape[0] * width / frame.shape[1])
    small = cv2.resize(frame, (width, height), interpolation=cv2.INTER_AREA)
    return cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

adjacent_mae = [
    float(np.mean(np.abs(
        analysis_gray(post_master_frames[i]).astype(np.float32)
        - analysis_gray(post_master_frames[i + 1]).astype(np.float32)
    )))
    for i in range(len(post_master_frames) - 1)
]
proof_pair_index = int(np.argmax(adjacent_mae))
proof_midpoint = film_midpoint_bgr(
    post_master_frames[proof_pair_index], post_master_frames[proof_pair_index + 1]
)

def make_triptych(frame0, midpoint, frame1, pair_index, destination):
    target_width, target_height = 480, 270
    panels = []
    for label, frame in (("native A", frame0), ("FILM midpoint", midpoint), ("native B", frame1)):
        panel = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
        cv2.rectangle(panel, (0, 0), (target_width, 32), (18, 18, 18), -1)
        cv2.putText(panel, label, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (255, 255, 255), 1, cv2.LINE_AA)
        panels.append(panel)
    sheet = np.hstack(panels)
    cv2.putText(
        sheet, f"highest-motion pair {pair_index}->{pair_index + 1}",
        (980, 258), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA,
    )
    if not cv2.imwrite(str(destination), sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
        raise RuntimeError(f"Could not write FILM proof: {destination}")

make_triptych(
    post_master_frames[proof_pair_index], proof_midpoint,
    post_master_frames[proof_pair_index + 1], proof_pair_index, FILM_PROOF,
)
print("FILM proof passed shape/range checks on highest-motion pair:", proof_pair_index)
display(IPImage(filename=str(FILM_PROOF)))

# Synthesize exactly one midpoint for every adjacent pair. Native stabilized
# frames are inserted directly; the model never redraws them.
film_midpoints = []
for index in range(len(post_master_frames) - 1):
    midpoint = proof_midpoint if index == proof_pair_index else film_midpoint_bgr(
        post_master_frames[index], post_master_frames[index + 1]
    )
    if midpoint.shape != post_master_frames[index].shape or midpoint.dtype != np.uint8:
        raise RuntimeError(f"Invalid FILM midpoint contract at pair {index}")
    film_midpoints.append(midpoint)
    if index == 0 or (index + 1) % 10 == 0 or index + 1 == len(post_master_frames) - 1:
        print(f"FILM midpoint {index + 1}/{len(post_master_frames) - 1}")

interpolated_frames = []
for index, midpoint in enumerate(film_midpoints):
    interpolated_frames.extend([post_master_frames[index], midpoint])
interpolated_frames.append(post_master_frames[-1])

native_working_exact = all(
    np.array_equal(interpolated_frames[2 * index], frame)
    for index, frame in enumerate(post_master_frames)
)
if not native_working_exact:
    raise RuntimeError("Native stabilized frames changed inside the 32 fps working sequence")

# Automatic midpoint QA. These are conservative artifact proxies, followed by
# a persisted contact sheet of the worst-scoring pairs for human inspection.
def frame_mae(frame0, frame1):
    g0, g1 = analysis_gray(frame0), analysis_gray(frame1)
    return float(np.mean(np.abs(g0.astype(np.float32) - g1.astype(np.float32))))

def laplacian_variance(frame):
    return float(cv2.Laplacian(analysis_gray(frame), cv2.CV_32F).var())

def edge_density(frame):
    return float(np.mean(cv2.Canny(analysis_gray(frame), 80, 160) > 0))

def block_boundary_score(frame, block=8):
    gray = analysis_gray(frame).astype(np.float32)
    vertical = np.abs(np.diff(gray, axis=1))
    horizontal = np.abs(np.diff(gray, axis=0))

    def excess(gradient, axis_length):
        positions = np.arange(1, axis_length)
        boundary = (positions % block) == 0
        guard = boundary.copy()
        guard[:-1] |= boundary[1:]
        guard[1:] |= boundary[:-1]
        if gradient.ndim == 2 and gradient.shape[1] == len(positions):
            at_boundary = gradient[:, boundary]
            away = gradient[:, ~guard]
        else:
            at_boundary = gradient[boundary, :]
            away = gradient[~guard, :]
        return max(0.0, float(at_boundary.mean() - away.mean()) / (float(away.mean()) + 1e-6))

    return max(excess(vertical, gray.shape[1]), excess(horizontal, gray.shape[0]))

pair_metrics = []
for index, midpoint in enumerate(film_midpoints):
    left, right = post_master_frames[index], post_master_frames[index + 1]
    left_to_mid = frame_mae(left, midpoint)
    mid_to_right = frame_mae(midpoint, right)
    sharp_reference = math.sqrt(max(laplacian_variance(left) * laplacian_variance(right), 1e-9))
    block_reference = max(block_boundary_score(left), block_boundary_score(right))
    edge_reference = max(edge_density(left), edge_density(right), 1e-9)
    pair_metrics.append({
        "pair_index": index,
        "source_motion_mae": frame_mae(left, right),
        "midpoint_balance": abs(left_to_mid - mid_to_right) / (left_to_mid + mid_to_right + 1e-6),
        "block_excess": max(0.0, block_boundary_score(midpoint) - block_reference),
        "edge_inflation": edge_density(midpoint) / edge_reference,
        "sharpness_ratio": laplacian_variance(midpoint) / sharp_reference,
        "reverse_agreement_mae": None,
    })

risk_indices = []
for key in ("source_motion_mae", "midpoint_balance", "block_excess", "edge_inflation"):
    for item in sorted(pair_metrics, key=lambda row: row[key], reverse=True)[:4]:
        if item["pair_index"] not in risk_indices:
            risk_indices.append(item["pair_index"])
risk_indices = risk_indices[:12]
for index in risk_indices:
    reverse = film_midpoint_bgr(post_master_frames[index + 1], post_master_frames[index])
    pair_metrics[index]["reverse_agreement_mae"] = frame_mae(film_midpoints[index], reverse)

balances = np.asarray([item["midpoint_balance"] for item in pair_metrics])
block_excesses = np.asarray([item["block_excess"] for item in pair_metrics])
edge_inflations = np.asarray([item["edge_inflation"] for item in pair_metrics])
sharpness_ratios = np.asarray([item["sharpness_ratio"] for item in pair_metrics])
reverse_maes = np.asarray([
    item["reverse_agreement_mae"] for item in pair_metrics
    if item["reverse_agreement_mae"] is not None
])

validation_failures = []
if float(np.median(balances)) > 0.28:
    validation_failures.append("temporal_midpoint_imbalance")
if float(np.percentile(block_excesses, 95)) > 0.35:
    validation_failures.append("block_boundary_excess")
if float(np.percentile(edge_inflations, 95)) > 1.65:
    validation_failures.append("edge_inflation_ghosting_proxy")
if float(np.percentile(sharpness_ratios, 5)) < 0.30:
    validation_failures.append("sharpness_collapse_ghosting_proxy")
if len(reverse_maes) and float(np.max(reverse_maes)) > 12.0:
    validation_failures.append("forward_reverse_model_disagreement")

for item in pair_metrics:
    reverse_penalty = (item["reverse_agreement_mae"] or 0.0) / 12.0
    item["risk_score"] = float(
        item["midpoint_balance"]
        + 2.0 * item["block_excess"]
        + max(0.0, item["edge_inflation"] - 1.15)
        + max(0.0, 0.55 - item["sharpness_ratio"])
        + reverse_penalty
    )

worst = sorted(pair_metrics, key=lambda item: item["risk_score"], reverse=True)[:12]
tiles = []
for item in worst:
    index = item["pair_index"]
    panels = []
    for frame in (post_master_frames[index], film_midpoints[index], post_master_frames[index + 1]):
        panels.append(cv2.resize(frame, (300, 169), interpolation=cv2.INTER_AREA))
    tile = np.hstack(panels)
    cv2.rectangle(tile, (0, 0), (tile.shape[1], 28), (16, 16, 16), -1)
    label = (
        f"pair {index:02d}  balance {item['midpoint_balance']:.2f}  "
        f"block+ {item['block_excess']:.2f}  edge {item['edge_inflation']:.2f}x"
    )
    cv2.putText(tile, label, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1, cv2.LINE_AA)
    tiles.append(tile)
sheet_rows = [np.hstack(tiles[row:row + 2]) for row in range(0, len(tiles), 2)]
validation_sheet = np.vstack(sheet_rows)
if not cv2.imwrite(str(FILM_VALIDATION_SHEET), validation_sheet, [cv2.IMWRITE_JPEG_QUALITY, 94]):
    raise RuntimeError("Could not write FILM validation contact sheet")

film_validation = {
    "status": "automatic_pass" if not validation_failures else "automatic_warning_visual_review_required",
    "failures": validation_failures,
    "native_working_frames_exact": native_working_exact,
    "native_frames": len(post_master_frames),
    "synthesized_midpoints": len(film_midpoints),
    "highest_motion_pair": proof_pair_index,
    "summary": {
        "median_midpoint_balance": float(np.median(balances)),
        "p95_midpoint_balance": float(np.percentile(balances, 95)),
        "p95_block_excess": float(np.percentile(block_excesses, 95)),
        "p95_edge_inflation": float(np.percentile(edge_inflations, 95)),
        "p05_sharpness_ratio": float(np.percentile(sharpness_ratios, 5)),
        "maximum_reverse_agreement_mae": float(np.max(reverse_maes)) if len(reverse_maes) else None,
    },
    "risk_checked_with_reverse_inference": risk_indices,
    "pairs": pair_metrics,
    "interpretation": (
        "Automatic metrics are artifact proxies, not a substitute for reviewing the persisted "
        "worst-midpoint sheet at full size before website integration."
    ),
}
FILM_VALIDATION.write_text(json.dumps(film_validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")

# Encode the exact interleaved working sequence as the final short-GOP master.
encode_bgr(interpolated_frames, OUTPUT_FPS, SCROLL_MASTER, crf=14, gop=4)

comparison_digest = atomic_publish(COMPARISON, DRIVE_POST / COMPARISON.name)
scroll_digest = atomic_publish(SCROLL_MASTER, DRIVE_POST / SCROLL_MASTER.name)
proof_digest = atomic_publish(FILM_PROOF, DRIVE_POST / FILM_PROOF.name)
validation_digest = atomic_publish(FILM_VALIDATION, DRIVE_POST / FILM_VALIDATION.name)
validation_sheet_digest = atomic_publish(FILM_VALIDATION_SHEET, DRIVE_POST / FILM_VALIDATION_SHEET.name)
scroll_probe = probe_video(SCROLL_MASTER)
scroll_gop = maximum_keyframe_gap(SCROLL_MASTER)
if (scroll_probe["width"], scroll_probe["height"], round(scroll_probe["fps"])) != (
    SOURCE_WIDTH, SOURCE_HEIGHT, OUTPUT_FPS
):
    raise RuntimeError(f"Invalid 32 fps output contract: {scroll_probe}")
expected_interpolated_frames = 2 * expected_pre_frames - 1
if scroll_probe["frames"] != expected_interpolated_frames:
    raise RuntimeError(f"Unexpected interpolated frame count: {scroll_probe}")
if scroll_gop > 4:
    raise RuntimeError(f"Scrub master keyframe gap is {scroll_gop}, expected <= 4")

decoded_scroll = decode_bgr(SCROLL_MASTER)
native_encode_psnr = [
    float(cv2.PSNR(post_master_frames[index], decoded_scroll[2 * index]))
    for index in range(len(post_master_frames))
]
film_validation["h264_native_frame_psnr"] = {
    "minimum_db": float(np.min(native_encode_psnr)),
    "median_db": float(np.median(native_encode_psnr)),
    "note": "Working-sequence native frames are exact; this measures expected final H.264 codec loss.",
}
FILM_VALIDATION.write_text(json.dumps(film_validation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
validation_digest = atomic_publish(FILM_VALIDATION, DRIVE_POST / FILM_VALIDATION.name)
if float(np.min(native_encode_psnr)) < 32.0:
    raise RuntimeError(f"Final encode quality is unexpectedly low: {min(native_encode_psnr):.2f} dB")

print("Persisted comparison:", DRIVE_POST / COMPARISON.name)
print("Persisted final scroll master:", DRIVE_POST / SCROLL_MASTER.name)
print("Scroll master:", json.dumps(scroll_probe, indent=2), "| maximum GOP:", scroll_gop)
print("FILM validation:", json.dumps(film_validation["summary"], indent=2))
display(IPImage(filename=str(FILM_VALIDATION_SHEET)))
display(Video(str(COMPARISON), embed=True, width=1000))
display(Video(str(SCROLL_MASTER), embed=True, width=960))
'''


FINALIZE = r'''
# Write a hashed manifest, bundle the compact deliverables, flush Drive, and disconnect.
artifacts = {}
deliverables = (
    PRE_STABILIZATION,
    POST_STABILIZATION,
    COMPARISON,
    SCROLL_MASTER,
    DIAGNOSTIC_PLOT,
    FILM_PROOF,
    FILM_VALIDATION,
    FILM_VALIDATION_SHEET,
)
for path in deliverables:
    durable = DRIVE_POST / path.name
    if not durable.is_file():
        raise RuntimeError(f"Missing durable artifact: {durable}")
    artifacts[path.name] = {
        "bytes": durable.stat().st_size,
        "sha256": sha256_file(durable),
    }

manifest = {
    "status": "complete_visual_review_required",
    "source": {
        "path": str(SOURCE_VIDEO),
        "sha256": sha256_file(SOURCE_VIDEO),
        "probe": source_probe,
        "removed_frames": [0, 80] if REMOVE_FORCED_ENDPOINTS else [],
        "endpoint_policy": (
            "legacy exact injected endpoints removed"
            if REMOVE_FORCED_ENDPOINTS
            else "native Wan endpoints retained; no photographs injected after generation"
        ),
    },
    "typography": "HTML/CSS only; no text or icons baked into generated media",
    "pre_stabilization": {"probe": pre_probe, "sha256": pre_digest},
    "post_stabilization": {
        "probe": post_probe,
        "sha256": post_digest,
        "metrics": stabilization_metrics,
    },
    "scroll_master": {
        "probe": scroll_probe,
        "sha256": scroll_digest,
        "maximum_keyframe_gap": scroll_gop,
        "interpolation": {
            "engine": "Google FILM TensorFlow2 v1",
            "license": "Apache-2.0",
            "model_source": FILM_MODEL_URL,
            "model_archive_bytes": FILM_MODEL_BYTES,
            "model_archive_sha256": FILM_MODEL_SHA256,
            "model_cache_persisted": False,
            "native_working_frames_exact": native_working_exact,
            "strategy": "one neural midpoint inserted between every adjacent stabilized native frame",
        },
        "validation": film_validation,
    },
    "artifacts": artifacts,
    "versions": {
        "python": platform.python_version(),
        "opencv": cv2.__version__,
        "numpy": np.__version__,
        "tensorflow": tf.__version__,
    },
    "completed_at": time.time(),
}
MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
manifest_digest = atomic_publish(MANIFEST_PATH, DRIVE_POST / MANIFEST_PATH.name)

bundle = RUNTIME_POST / f"{POSTPROCESS_ID}_review_bundle.zip"
with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in (*deliverables, MANIFEST_PATH):
        archive.write(path, arcname=path.name)
bundle_digest = atomic_publish(bundle, DRIVE_POST / bundle.name)

success = DRIVE_POST / "success.json"
success.write_text(json.dumps({
    "status": "complete_visual_review_required",
    "manifest_sha256": manifest_digest,
    "bundle": {"path": str(DRIVE_POST / bundle.name), "sha256": bundle_digest},
    "final_scroll_master": str(DRIVE_POST / SCROLL_MASTER.name),
    "original_wan_model_downloaded": False,
    "film_model_persisted": False,
    "film_automatic_validation": film_validation["status"],
    "next_gate": "review the FILM worst-midpoint sheet and scroll master before website integration",
}, indent=2, sort_keys=True) + "\n", encoding="utf-8")

for path in (DRIVE_POST / MANIFEST_PATH.name, DRIVE_POST / bundle.name, success):
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Final persistence check failed: {path}")

print("COMPLETE. Durable directory:", DRIVE_POST)
print("Final scroll master:", DRIVE_POST / SCROLL_MASTER.name)
print("Review bundle:", DRIVE_POST / bundle.name)

if AUTO_DISCONNECT_ON_SUCCESS:
    _disconnect("FILM post-process completed and all artifacts verified on Drive")
else:
    _shutdown_started.set()
'''


def build() -> Path:
    notebook = nbformat.v4.new_notebook()
    notebook.metadata = {
        "colab": {"name": OUTPUT.name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.x"},
    }
    notebook.cells = [
        nbformat.v4.new_markdown_cell(TITLE.strip()),
        nbformat.v4.new_code_cell(SETTINGS.strip()),
        nbformat.v4.new_code_cell(SETUP.strip()),
        nbformat.v4.new_code_cell(PREFLIGHT_AND_UTILITIES.strip()),
        nbformat.v4.new_code_cell(TRIM_AND_PERSIST.strip()),
        nbformat.v4.new_code_cell(STABILIZE.strip()),
        nbformat.v4.new_code_cell(INTERPOLATE_AND_ENCODE.strip()),
        nbformat.v4.new_code_cell(FINALIZE.strip()),
    ]
    nbformat.validate(notebook)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=f"cell-{index}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT)
    if OUTPUT.stat().st_size > 140_000:
        raise RuntimeError("Notebook unexpectedly large; keep it stable in the Colab editor")
    return OUTPUT


if __name__ == "__main__":
    output = build()
    print(output)
    print(output.stat().st_size, "bytes")
