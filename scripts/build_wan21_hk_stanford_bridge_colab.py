#!/usr/bin/env python3
"""Build the Wan 2.1 Hong Kong-to-Stanford atmospheric bridge notebook."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
import tempfile
import zipfile
from pathlib import Path

import nbformat

import build_stanford_rife_bakeoff_colab as rife_base


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "wan21_hk_to_stanford_atmospheric_bridge_colab.ipynb"

DIFFUSERS_COMMIT = "2919c50962c375e32b9fa40ae5fad50cd3251332"
MODEL_ID = "Wan-AI/Wan2.1-FLF2V-14B-720P-diffusers"
MODEL_REVISION = "17c30769b1e0b5dcaa1799b117bf20a9c31f59d7"


TITLE = r'''
# Hong Kong → Stanford atmospheric bridge — Wan 2.1 FLF2V

This is the next visual proof after approving the Stanford shot. It keeps the
stronger Hong Kong tower flight (SkyReels `S1_tower_flight`, seed `42211`) and
uses two first/last-frame-conditioned Wan shots:

1. the Hong Kong flight cranes hard upward until the city travels below frame;
2. the natural final sky frame from that generation becomes the reference for
   a continued crest-and-dive into the approved Memorial Church opening.

The shared handoff contains only sky and cloud. There is no crossfade, landmark
morph, flash, portal, visible drone, or baked typography. The two generations
are saved separately, so either half can be rerun without discarding the other.

After generation, the notebook assembles Hong Kong context, both bridge halves,
and the original approved 16 fps Stanford source. It then applies the accepted
uniform-synthetic RIFE 4.26 treatment once across the whole assembled timeline,
including its joins. Both the native proof and the 32 fps master/GOP-4 web
encode persist to Drive. Model caches remain temporary, and Colab disconnects
after success, an uncaught error, or the hard cutoff.

Run on a Colab **A100 80 GB High-RAM** runtime. Run all cells in order.
'''


SETTINGS = r'''
EXPERIMENT_ID = "hk_to_stanford_atmospheric_bridge_wan21_v1"

WIDTH, HEIGHT = 1280, 720
WAN_FRAMES = 81
NATIVE_FPS = 16
OUTPUT_FPS = 32
INFERENCE_STEPS = 50
GUIDANCE_SCALE = 5.5

# The model generates 81 frames per half. Editorial retiming selects 41 frames
# per half before the single RIFE pass, giving a punchier ~5.1-second bridge.
RETIME_FRAMES_PER_HALF = 41
HK_CONTEXT_SECONDS = 1.5
SEEDS = {"A_hk_to_sky": 73111, "B_sky_to_stanford": 73147}

RUN_RIFE_POSTPROCESS = True
SHARPEN_AMOUNT = 0.14
SHARPEN_SIGMA = 0.85
PERSIST_MODEL_CACHE_TO_DRIVE = False

AUTO_DISCONNECT_ON_SUCCESS = True
AUTO_DISCONNECT_ON_ERROR = True
HARD_CUTOFF_HOURS = 4.0

if (WAN_FRAMES - 1) % 4:
    raise ValueError("Wan requires 4n+1 frames")
if (WIDTH, HEIGHT, WAN_FRAMES, NATIVE_FPS) != (1280, 720, 81, 16):
    raise ValueError("This proof is locked to Wan FLF2V's native contract")
if RETIME_FRAMES_PER_HALF < 25 or RETIME_FRAMES_PER_HALF > WAN_FRAMES:
    raise ValueError("Bridge retime is outside the reviewed range")
if OUTPUT_FPS != 2 * NATIVE_FPS:
    raise ValueError("Uniform-synthetic postprocess requires exact 2x output")

print("Experiment:", EXPERIMENT_ID)
print("Bridge duration after retime:", round(2 * RETIME_FRAMES_PER_HALF / NATIVE_FPS, 3), "seconds")
'''


SETUP = r'''
from google.colab import drive
from google.colab import drive as colab_drive, runtime as colab_runtime
from IPython.display import Image as IPImage, Video, display
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
import fractions, gc, hashlib, importlib, inspect, json, math, os, platform
import shutil, subprocess, sys, threading, time, uuid, zipfile

drive.mount("/content/drive", force_remount=False)

BRIDGE_DRIVE_ROOT = Path("/content/drive/MyDrive/Personal_Website_HK_Stanford_Bridge")
DRIVE_EXPERIMENT = BRIDGE_DRIVE_ROOT / "experiments" / EXPERIMENT_ID
DRIVE_INPUTS = DRIVE_EXPERIMENT / "inputs"
DRIVE_SEGMENTS = DRIVE_EXPERIMENT / "segments"
DRIVE_OUTPUT = DRIVE_EXPERIMENT / "output"

RUNTIME_ROOT = Path("/content/hk_stanford_bridge_runtime")
RUNTIME_INPUTS = RUNTIME_ROOT / "inputs"
RUNTIME_MODEL = RUNTIME_ROOT / "wan_model"
RUNTIME_SEGMENTS = RUNTIME_ROOT / "segments"
RUNTIME_OUTPUT = RUNTIME_ROOT / "output"
RUNTIME_MODELS = RUNTIME_ROOT / "rife_models"
RIFE_REPO = RUNTIME_ROOT / "Practical-RIFE"

for path in (
    DRIVE_INPUTS, DRIVE_SEGMENTS, DRIVE_OUTPUT, RUNTIME_INPUTS,
    RUNTIME_MODEL, RUNTIME_SEGMENTS, RUNTIME_OUTPUT, RUNTIME_MODELS,
):
    path.mkdir(parents=True, exist_ok=True)

probe = DRIVE_EXPERIMENT / f".write-probe-{uuid.uuid4().hex}"
payload = f"bridge persistence {time.time_ns()}\n"
probe.write_text(payload, encoding="utf-8")
if probe.read_text(encoding="utf-8") != payload:
    raise RuntimeError("Google Drive persistence probe failed")
probe.unlink()

def free_gib(path):
    return shutil.disk_usage(path).free / 2**30

_shutdown_started = threading.Event()

def disconnect_runtime(reason, failure=None):
    if _shutdown_started.is_set():
        return
    _shutdown_started.set()
    payload = {"reason": reason, "time": time.time()}
    if failure is not None:
        payload["failure"] = str(failure)
    try:
        (DRIVE_EXPERIMENT / "runtime_shutdown.json").write_text(
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

threading.Thread(target=hard_cutoff, name="bridge-hard-cutoff", daemon=True).start()

def disconnect_after_cell_error(result):
    failure = getattr(result, "error_in_exec", None) or getattr(result, "error_before_exec", None)
    if failure is not None and AUTO_DISCONNECT_ON_ERROR:
        disconnect_runtime("uncaught notebook error", failure=failure)

get_ipython().events.register("post_run_cell", disconnect_after_cell_error)

print("Durable output:", DRIVE_EXPERIMENT)
print("Wan and RIFE caches: temporary local SSD only")
print("Local free:", round(free_gib("/content"), 1), "GiB | Drive free:", round(free_gib(BRIDGE_DRIVE_ROOT), 1), "GiB")
'''


PREFLIGHT_AND_INSTALL = rf'''
import torch

if not torch.cuda.is_available():
    raise RuntimeError("CUDA unavailable. Select an A100 80GB High-RAM runtime.")
gpu = torch.cuda.get_device_properties(0)
vram_gib = gpu.total_memory / 2**30
ram_gib = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30
if "A100" not in gpu.name or vram_gib < 75:
    raise RuntimeError(f"Need A100 80GB; found {{gpu.name}} with {{vram_gib:.1f}} GiB")
if ram_gib < 75:
    raise RuntimeError(f"Need High-RAM with at least 75 GiB; found {{ram_gib:.1f}} GiB")
if free_gib("/content") < 105:
    raise RuntimeError(f"Need 105 GiB local free; found {{free_gib('/content'):.1f}} GiB")
if free_gib(BRIDGE_DRIVE_ROOT) < 8:
    raise RuntimeError(f"Need 8 GiB Drive free; found {{free_gib(BRIDGE_DRIVE_ROOT):.1f}} GiB")
for binary in ("git", "ffmpeg", "ffprobe"):
    if shutil.which(binary) is None:
        raise RuntimeError(f"Missing binary: {{binary}}")

DIFFUSERS_COMMIT = "{DIFFUSERS_COMMIT}"
packages = [
    f"git+https://github.com/huggingface/diffusers.git@{{DIFFUSERS_COMMIT}}",
    "transformers==5.14.1", "accelerate==1.14.0", "huggingface-hub==1.24.0",
    "safetensors==0.8.0", "opencv-python-headless==4.12.0.88",
    "imageio==2.37.0", "imageio-ffmpeg==0.6.0", "ftfy==6.3.1",
    "gdown==6.1.0", "scipy>=1.13,<2",
]
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", *packages])

import accelerate, cv2, diffusers, huggingface_hub, numpy as np, safetensors, transformers
import torch.nn.functional as F
from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
from huggingface_hub import model_info, snapshot_download
from safetensors import safe_open
from transformers import CLIPVisionModel

signature = inspect.signature(WanImageToVideoPipeline.__call__)
if "last_image" not in signature.parameters:
    raise RuntimeError(f"Installed Wan pipeline lacks last_image conditioning: {{signature}}")

VERSIONS = {{
    "python": platform.python_version(), "torch": torch.__version__,
    "diffusers": diffusers.__version__, "transformers": transformers.__version__,
    "accelerate": accelerate.__version__, "opencv": cv2.__version__,
    "diffusers_commit": DIFFUSERS_COMMIT,
}}
print("GPU:", gpu.name, f"{{vram_gib:.1f}} GiB | RAM: {{ram_gib:.1f}} GiB")
print(json.dumps(VERSIONS, indent=2))
'''


UTILITIES = r'''
def sha256_file(path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()

def atomic_write_json(destination, payload):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + f".part-{uuid.uuid4().hex}")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, destination)

def atomic_publish(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(source)
    temporary = destination.with_name(destination.name + f".part-{digest[:12]}-{uuid.uuid4().hex}")
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
    return {
        "width": int(stream["width"]), "height": int(stream["height"]),
        "fps": float(fractions.Fraction(stream["avg_frame_rate"])),
        "frames": int(stream["nb_read_frames"]),
        "duration": float(stream.get("duration") or 0),
    }

def maximum_keyframe_gap(path):
    result = run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "frame=key_frame", "-of", "json", path,
    ])
    flags = [int(item["key_frame"]) for item in json.loads(result.stdout)["frames"]]
    keys = [index for index, flag in enumerate(flags) if flag]
    if not keys or keys[0] != 0:
        return len(flags)
    return max([b - a for a, b in zip(keys, keys[1:])] + [len(flags) - keys[-1]])

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
        raise RuntimeError(f"ffmpeg encode failed ({return_code}):\n{stderr[-4000:]}")

def frame_to_rgb(frame):
    if isinstance(frame, Image.Image):
        return np.asarray(frame.convert("RGB"), dtype=np.uint8)
    array = np.asarray(frame)
    if np.issubdtype(array.dtype, np.floating) and array.max(initial=0) <= 1.01:
        array = array * 255
    return np.clip(array, 0, 255).astype(np.uint8)[:, :, :3]

def normalize_wan_output(output):
    frames = output.frames[0]
    if isinstance(frames, np.ndarray) and frames.ndim == 4:
        frames = list(frames)
    return [frame_to_rgb(frame) for frame in frames]

def make_contact_sheet(frames_rgb, destination, label):
    indices = np.linspace(0, len(frames_rgb) - 1, 12).round().astype(int)
    sheet = Image.new("RGB", (1280, 660), "#111111")
    draw = ImageDraw.Draw(sheet)
    for position, index in enumerate(indices):
        tile = Image.fromarray(frames_rgb[index]).resize((320, 180), Image.Resampling.LANCZOS)
        x, y = (position % 4) * 320, (position // 4) * 210
        sheet.paste(tile, (x, y))
        draw.rectangle((x, y + 180, x + 320, y + 210), fill="#111111")
        draw.text((x + 8, y + 188), f"frame {index:03d}", fill="white")
    draw.rectangle((0, 630, 1280, 660), fill="black")
    draw.text((8, 638), label, fill="white")
    sheet.save(destination, "JPEG", quality=94, optimize=True)

def exact_retime(frames, output_count):
    indices = np.linspace(0, len(frames) - 1, output_count).round().astype(int)
    if len(np.unique(indices)) != output_count:
        raise RuntimeError("Retime unexpectedly duplicated a source frame")
    return [frames[index].copy() for index in indices], indices.tolist()
'''


SOURCES = r'''
# Resolve the already-persisted clips. No manual upload and no web download.
SKYREELS_ROOT = Path("/content/drive/MyDrive/Personal_Website_SkyReelsV2")
WAN_ROOT = Path("/content/drive/MyDrive/Personal_Website_Wan21_FLF2V")

hk_preferred = (
    SKYREELS_ROOT / "runs" / "intro_cinematic_v2_1_1p3b" / "stages" /
    "S1_tower_flight" / "candidates" / "42211" / "clip.mp4"
)
hk_matches = [hk_preferred] if hk_preferred.is_file() else sorted(
    SKYREELS_ROOT.glob("runs/*/stages/S1_tower_flight/candidates/42211/clip.mp4"),
    key=lambda path: path.stat().st_mtime,
    reverse=True,
)
if not hk_matches:
    raise RuntimeError(
        "Could not find persisted SkyReels S1 seed 42211. Expected a clip under "
        "/content/drive/MyDrive/Personal_Website_SkyReelsV2/runs/*/stages/"
        "S1_tower_flight/candidates/42211/clip.mp4"
    )
HK_SOURCE_VIDEO = hk_matches[0]

STANFORD_SOURCE_VIDEO = (
    WAN_ROOT / "experiments" / "stanford_wan21_flf2v_whip_720p_v2" /
    "postprocess" / "stabilized_film32_whip_v3" / "02_post_stabilization_720p16.mp4"
)
if not STANFORD_SOURCE_VIDEO.is_file():
    raise RuntimeError(f"Missing approved original Stanford source: {STANFORD_SOURCE_VIDEO}")

hk_probe = probe_video(HK_SOURCE_VIDEO)
stanford_probe = probe_video(STANFORD_SOURCE_VIDEO)
if (hk_probe["width"], hk_probe["height"], round(hk_probe["fps"]), hk_probe["frames"]) != (1280, 720, 24, 48):
    raise RuntimeError(f"Unexpected Hong Kong source contract: {hk_probe}")
if (stanford_probe["width"], stanford_probe["height"], round(stanford_probe["fps"]), stanford_probe["frames"]) != (1280, 720, 16, 81):
    raise RuntimeError(f"Unexpected Stanford source contract: {stanford_probe}")

hk_frames_bgr = decode_bgr(HK_SOURCE_VIDEO)
stanford_frames_bgr = decode_bgr(STANFORD_SOURCE_VIDEO)
hk_endpoint_rgb = cv2.cvtColor(hk_frames_bgr[-1], cv2.COLOR_BGR2RGB)
stanford_endpoint_rgb = cv2.cvtColor(stanford_frames_bgr[0], cv2.COLOR_BGR2RGB)

# A deterministic cloud-only anchor sampled from the narrow, architecture-free
# top band of the actual Hong Kong ending. It is only a color/cloud-direction
# anchor; Wan synthesizes the resolved moving atmosphere.
sky_crop = hk_endpoint_rgb[0:58, 300:1000]
sky_anchor_rgb = cv2.resize(sky_crop, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)
sky_anchor_rgb = cv2.GaussianBlur(sky_anchor_rgb, (0, 0), 0.70)

ENDPOINTS = {
    "hk": Image.fromarray(hk_endpoint_rgb),
    "sky": Image.fromarray(sky_anchor_rgb),
    "stanford": Image.fromarray(stanford_endpoint_rgb),
}

source_records = {}
for role, image in ENDPOINTS.items():
    local = RUNTIME_INPUTS / f"{role}_endpoint_1280x720.png"
    image.save(local, "PNG", optimize=True)
    digest = atomic_publish(local, DRIVE_INPUTS / local.name)
    source_records[role] = {"path": str(DRIVE_INPUTS / local.name), "sha256": digest}

source_records["hk_source_video"] = {
    "path": str(HK_SOURCE_VIDEO), "sha256": sha256_file(HK_SOURCE_VIDEO), "probe": hk_probe,
}
source_records["stanford_source_video"] = {
    "path": str(STANFORD_SOURCE_VIDEO), "sha256": sha256_file(STANFORD_SOURCE_VIDEO), "probe": stanford_probe,
}
atomic_write_json(DRIVE_INPUTS / "source_provenance.json", source_records)

endpoint_sheet = Image.new("RGB", (1280, 750), "#111111")
for column, role in enumerate(("hk", "sky", "stanford")):
    panel = ENDPOINTS[role].resize((426, 240), Image.Resampling.LANCZOS)
    endpoint_sheet.paste(panel, (column * 426, 0))
ImageDraw.Draw(endpoint_sheet).text(
    (12, 260),
    "HK final frame  →  cloud-only lighting anchor  →  approved Stanford opening frame",
    fill="white",
)
ImageDraw.Draw(endpoint_sheet).text(
    (12, 300),
    "The actual B start reference will be A's naturally generated final sky frame.",
    fill="white",
)
endpoint_sheet_path = RUNTIME_INPUTS / "bridge_endpoint_sheet.jpg"
endpoint_sheet.save(endpoint_sheet_path, "JPEG", quality=94, optimize=True)
atomic_publish(endpoint_sheet_path, DRIVE_INPUTS / endpoint_sheet_path.name)

print("Hong Kong:", HK_SOURCE_VIDEO)
print("Stanford:", STANFORD_SOURCE_VIDEO)
display(endpoint_sheet)
'''


CONFIG = rf'''
MODEL = {{
    "repo_id": "{MODEL_ID}", "revision": "{MODEL_REVISION}",
    "expected_snapshot_gib": 83.93, "license": "Apache-2.0",
}}

PROMPTS = {{
    "A_hk_to_sky": (
        "照片级写实香港航拍，同一个连续镜头，严格延续给定的香港终止画面。固定24毫米电影镜头，真实三维无人机摄影机路径，"
        "但画面中绝对不能出现无人机或摄影设备。镜头先以现有向前速度飞行，随后平滑但强烈加速并大幅垂直升高，同时持续向上俯仰。"
        "近处楼顶以最快速度向下穿过画面，中距离摩天楼和远处海港以不同视差速度向下移动，城市必须真实地从画面下边缘完全离开，"
        "不是变透明、不是融化。最后百分之二十只剩下暖金色天空、薄云和大气雾霭；云层仍持续向下流动，摄影机保持向上和向前速度，"
        "结尾不能减速或停在天空中。运动节奏为短暂稳定开场后爆发式上升，路径平滑，具有真实方向性运动模糊。"
    ),
    "B_sky_to_stanford": (
        "照片级写实电影摄影，同一个不间断镜头。严格从给定的香港镜头自然生成的最后天空画面开始，保持完全相同的云层方向、"
        "暖金色光线、曝光、24毫米镜头和向上向前速度。开始时天空充满画面，绝对不要停顿；摄影机快速越过上升轨迹顶点，"
        "以连续的缓入缓出曲线果断向下俯仰并下降。真实斯坦福校园树冠先从画面下边缘进入，随后斯坦福纪念教堂和主方院砂岩拱廊"
        "从下方升入画面，近处树叶和柱子具有强烈视差。建筑不能从云中变形出来，云层先向上离开，校园之后才从下边缘进入。"
        "中段下降快速有冲击力，最后百分之二十平滑减速并稳定落在给定的纪念教堂构图上。"
    ),
}}

NEGATIVE_PROMPT = (
    "交叉淡化，溶解，透明建筑，建筑变形，香港摩天楼变成教堂，云朵变成建筑，传送门，白色闪光，隐藏剪辑，跳切，"
    "照片平移，照片旋转，数码变焦，静止天空，结尾停顿，匀速移动，手持抖动，逐帧闪烁，弯曲柱子，重复拱门，"
    "无人机，四旋翼，螺旋桨，摄影设备，人物特写，卡通，插画，文字，字幕，标志，水印"
)

STABLE_CONFIG = {{
    "experiment_id": EXPERIMENT_ID, "model": MODEL, "seeds": SEEDS,
    "width": WIDTH, "height": HEIGHT, "wan_frames": WAN_FRAMES,
    "native_fps": NATIVE_FPS, "steps": INFERENCE_STEPS,
    "guidance_scale": GUIDANCE_SCALE, "prompts": PROMPTS,
    "negative_prompt": NEGATIVE_PROMPT,
    "bridge": "HK crane-up -> generated cloud handoff -> Stanford crest-and-dive",
    "crossfade": False, "forced_endpoint_pixels": False,
    "typography_baked_into_video": False,
}}
CONFIG_FINGERPRINT = hashlib.sha256(
    json.dumps(STABLE_CONFIG, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
atomic_write_json(DRIVE_EXPERIMENT / "generation_config.json", STABLE_CONFIG)
print("Configuration:", CONFIG_FINGERPRINT)
'''


GENERATE = r'''
def flow_series_rgb(frames):
    values = []
    for left, right in zip(frames, frames[1:]):
        a = cv2.cvtColor(cv2.resize(left, (320, 180)), cv2.COLOR_RGB2GRAY)
        b = cv2.cvtColor(cv2.resize(right, (320, 180)), cv2.COLOR_RGB2GRAY)
        flow = cv2.calcOpticalFlowFarneback(a, b, None, .5, 3, 21, 3, 5, 1.2, 0)
        values.append(float(np.median(np.linalg.norm(flow, axis=2))))
    return values

def segment_dir(segment_id):
    return DRIVE_SEGMENTS / segment_id / str(SEEDS[segment_id])

def valid_segment(segment_id, expected_first_sha, expected_last_sha):
    directory = segment_dir(segment_id)
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete":
            return False
        if manifest.get("config_fingerprint") != CONFIG_FINGERPRINT:
            return False
        if manifest.get("first_reference_sha256") != expected_first_sha:
            return False
        if manifest.get("last_reference_sha256") != expected_last_sha:
            return False
        for name, record in manifest["artifacts"].items():
            path = directory / name
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                return False
        probe = probe_video(directory / "clip_720p16.mp4")
        return (probe["width"], probe["height"], round(probe["fps"]), probe["frames"]) == (1280, 720, 16, 81)
    except Exception:
        return False

def image_sha(image):
    return hashlib.sha256(np.asarray(image.convert("RGB"), dtype=np.uint8).tobytes()).hexdigest()

hk_sha = image_sha(ENDPOINTS["hk"])
sky_reference_sha = image_sha(ENDPOINTS["sky"])
stanford_sha = image_sha(ENDPOINTS["stanford"])

a_valid = valid_segment("A_hk_to_sky", hk_sha, sky_reference_sha)
if a_valid:
    a_natural_last = Image.open(segment_dir("A_hk_to_sky") / "natural_last_frame.png").convert("RGB")
else:
    a_natural_last = None

b_valid = False
if a_natural_last is not None:
    b_valid = valid_segment("B_sky_to_stanford", image_sha(a_natural_last), stanford_sha)

need_model = not (a_valid and b_valid)
model_directory = None
pipe = None

def persist_segment(segment_id, frames, first_reference, last_reference, elapsed):
    local = RUNTIME_SEGMENTS / segment_id / str(SEEDS[segment_id])
    durable = segment_dir(segment_id)
    local.mkdir(parents=True, exist_ok=True)
    durable.mkdir(parents=True, exist_ok=True)

    clip = local / "clip_720p16.mp4"
    contact = local / "contact_sheet.jpg"
    first_frame = local / "natural_first_frame.png"
    last_frame = local / "natural_last_frame.png"
    metrics_path = local / "metrics.json"
    encode_bgr([cv2.cvtColor(frame, cv2.COLOR_RGB2BGR) for frame in frames], NATIVE_FPS, clip, crf=15, gop=16)
    make_contact_sheet(frames, contact, f"{segment_id} | seed {SEEDS[segment_id]} | native Wan output")
    Image.fromarray(frames[0]).save(first_frame, "PNG", optimize=True)
    Image.fromarray(frames[-1]).save(last_frame, "PNG", optimize=True)

    flows = flow_series_rgb(frames)
    first_array = np.asarray(first_reference, dtype=np.float32)
    last_array = np.asarray(last_reference, dtype=np.float32)
    metrics = {
        "natural_first_reference_mae": float(np.abs(frames[0].astype(np.float32) - first_array).mean()),
        "natural_last_reference_mae": float(np.abs(frames[-1].astype(np.float32) - last_array).mean()),
        "median_flow": float(np.median(flows)), "mean_flow": float(np.mean(flows)),
        "opening_flow": float(np.median(flows[:16])),
        "middle_flow": float(np.median(flows[24:56])),
        "closing_flow": float(np.median(flows[-16:])),
        "forced_endpoint_pixels": False,
        "automatic_aesthetic_rejection": False,
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    artifacts = {}
    for path in (clip, contact, first_frame, last_frame, metrics_path):
        digest = atomic_publish(path, durable / path.name)
        artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}
    atomic_write_json(durable / "manifest.json", {
        "status": "complete", "visual_status": "manual_review_required",
        "segment": segment_id, "seed": SEEDS[segment_id],
        "config_fingerprint": CONFIG_FINGERPRINT,
        "first_reference_sha256": image_sha(first_reference),
        "last_reference_sha256": image_sha(last_reference),
        "metrics": metrics, "artifacts": artifacts, "elapsed_seconds": elapsed,
        "model": MODEL, "versions": VERSIONS,
    })
    return Image.fromarray(frames[-1]).convert("RGB")

try:
    if need_model:
        info = model_info(MODEL["repo_id"], revision=MODEL["revision"], files_metadata=True)
        if info.sha != MODEL["revision"]:
            raise RuntimeError("Pinned Wan model revision changed")
        expected = {item.rfilename: item.size for item in info.siblings if item.size is not None}
        expected_bytes = sum(expected.values())
        if not 82 * 2**30 < expected_bytes < 86 * 2**30:
            raise RuntimeError(f"Unexpected Wan snapshot size: {expected_bytes / 2**30:.2f} GiB")
        if free_gib("/content") < expected_bytes / 2**30 + 15:
            raise RuntimeError("Insufficient local SSD for Wan plus reserve")

        model_directory = Path(snapshot_download(
            repo_id=MODEL["repo_id"], revision=MODEL["revision"],
            local_dir=str(RUNTIME_MODEL), max_workers=4,
        ))
        invalid = [name for name, size in expected.items()
                   if not (model_directory / name).is_file() or (model_directory / name).stat().st_size != size]
        if invalid:
            raise RuntimeError(f"Incomplete Wan snapshot: {invalid[:5]}")
        for path in model_directory.rglob("*.safetensors"):
            with safe_open(path, framework="pt", device="cpu") as handle:
                if not handle.keys():
                    raise RuntimeError(f"Empty safetensors file: {path}")

        image_encoder = CLIPVisionModel.from_pretrained(
            str(model_directory), subfolder="image_encoder", torch_dtype=torch.float32,
            local_files_only=True, low_cpu_mem_usage=True,
        )
        vae = AutoencoderKLWan.from_pretrained(
            str(model_directory), subfolder="vae", torch_dtype=torch.float32,
            local_files_only=True, low_cpu_mem_usage=True,
        )
        pipe = WanImageToVideoPipeline.from_pretrained(
            str(model_directory), image_encoder=image_encoder, vae=vae,
            torch_dtype=torch.bfloat16, local_files_only=True, low_cpu_mem_usage=True,
        )
        pipe.vae.enable_tiling()
        pipe.enable_model_cpu_offload()

    def generate_one(segment_id, first_reference, last_reference):
        started = time.time()
        output = pipe(
            image=first_reference, last_image=last_reference,
            prompt=PROMPTS[segment_id], negative_prompt=NEGATIVE_PROMPT,
            height=HEIGHT, width=WIDTH, num_frames=WAN_FRAMES,
            num_inference_steps=INFERENCE_STEPS, guidance_scale=GUIDANCE_SCALE,
            generator=torch.Generator(device="cuda").manual_seed(SEEDS[segment_id]),
            output_type="np",
        )
        frames = normalize_wan_output(output)
        if len(frames) != WAN_FRAMES:
            raise RuntimeError(f"Wan returned {len(frames)} frames for {segment_id}")
        return persist_segment(segment_id, frames, first_reference, last_reference, time.time() - started)

    if a_valid:
        print("Validated A_hk_to_sky; skipping generation.")
        a_natural_last = Image.open(segment_dir("A_hk_to_sky") / "natural_last_frame.png").convert("RGB")
    else:
        print("Generating A_hk_to_sky...")
        a_natural_last = generate_one("A_hk_to_sky", ENDPOINTS["hk"], ENDPOINTS["sky"])

    b_valid = valid_segment("B_sky_to_stanford", image_sha(a_natural_last), stanford_sha)
    if b_valid:
        print("Validated B_sky_to_stanford; skipping generation.")
    else:
        print("Generating B_sky_to_stanford from A's natural final sky frame...")
        generate_one("B_sky_to_stanford", a_natural_last, ENDPOINTS["stanford"])
finally:
    if pipe is not None:
        try:
            pipe.remove_all_hooks()
        except Exception:
            pass
        del pipe
        pipe = None
    gc.collect()
    torch.cuda.empty_cache()
    if model_directory is not None and not PERSIST_MODEL_CACHE_TO_DRIVE:
        shutil.rmtree(model_directory, ignore_errors=True)
        print("Released temporary Wan snapshot")

for segment_id in ("A_hk_to_sky", "B_sky_to_stanford"):
    display(IPImage(filename=str(segment_dir(segment_id) / "contact_sheet.jpg")))
    display(Video(str(segment_dir(segment_id) / "clip_720p16.mp4"), embed=True, width=960))
'''


ASSEMBLE = r'''
# Assemble at 16 fps before interpolation. No generated endpoint is overwritten.
a_frames_bgr = decode_bgr(segment_dir("A_hk_to_sky") / "clip_720p16.mp4")
b_frames_bgr = decode_bgr(segment_dir("B_sky_to_stanford") / "clip_720p16.mp4")
if len(a_frames_bgr) != WAN_FRAMES or len(b_frames_bgr) != WAN_FRAMES:
    raise RuntimeError("A persisted bridge segment has the wrong frame count")

hk_context_count = round(HK_CONTEXT_SECONDS * NATIVE_FPS)
hk_source_count = round(HK_CONTEXT_SECONDS * hk_probe["fps"])
hk_tail_source = hk_frames_bgr[-hk_source_count:]
hk_tail, hk_indices = exact_retime(hk_tail_source, hk_context_count)
a_retimed, a_indices = exact_retime(a_frames_bgr, RETIME_FRAMES_PER_HALF)
b_retimed, b_indices = exact_retime(b_frames_bgr, RETIME_FRAMES_PER_HALF)

assembled_native_frames = [*hk_tail, *a_retimed, *b_retimed, *stanford_frames_bgr]
SEAMS_NATIVE = {
    "hk_to_A": len(hk_tail),
    "A_to_B": len(hk_tail) + len(a_retimed),
    "B_to_stanford": len(hk_tail) + len(a_retimed) + len(b_retimed),
}

NATIVE_PROOF = RUNTIME_OUTPUT / "01_native_assembled_720p16.mp4"
encode_bgr(assembled_native_frames, NATIVE_FPS, NATIVE_PROOF, crf=12, gop=16)
native_probe = probe_video(NATIVE_PROOF)
expected_native_frames = hk_context_count + 2 * RETIME_FRAMES_PER_HALF + 81
if (native_probe["width"], native_probe["height"], round(native_probe["fps"]), native_probe["frames"]) != (
    WIDTH, HEIGHT, NATIVE_FPS, expected_native_frames,
):
    raise RuntimeError(f"Native assembly contract failed: {native_probe}")

native_digest = atomic_publish(NATIVE_PROOF, DRIVE_OUTPUT / NATIVE_PROOF.name)
atomic_write_json(DRIVE_OUTPUT / "native_assembly.json", {
    "status": "complete", "sha256": native_digest, "probe": native_probe,
    "seams_native": SEAMS_NATIVE, "hk_source_indices": hk_indices,
    "A_source_indices": a_indices, "B_source_indices": b_indices,
    "crossfade": False, "forced_endpoint_pixels": False,
})
print("Persisted native proof before interpolation:", DRIVE_OUTPUT / NATIVE_PROOF.name)
display(Video(str(NATIVE_PROOF), embed=True, width=960))
'''


RIFE_CONFIG = r'''
RIFE_REPO_URL = "https://github.com/hzwer/Practical-RIFE.git"
RIFE_REPO_COMMIT = "17d8c7a1005b37f4c97bfee04e316aaec7fdc536"
RIFE_MODELS = {
    "rife426": {
        "gdrive_id": "1gViYvvQrtETBgU1w8axZSsr7YUuw31uy",
        "bytes": 22_867_954,
        "sha256": "c2452dd2b244947d4be580156bbead60d6b72af5736860f7d6b3f99648c9c4cc",
    },
}
'''


RIFE_SETUP = rife_base.RIFE_SETUP.replace(
    "print(\"Practical-RIFE commit and both official model archives verified\")",
    "print(\"Practical-RIFE commit and RIFE 4.26 archive verified\")",
)


POSTPROCESS = r'''
if not RUN_RIFE_POSTPROCESS:
    print("RUN_RIFE_POSTPROCESS=False: native proof is already persisted; stopping before RIFE.")
else:
    positions = np.asarray([
        pair + fraction
        for pair in range(len(assembled_native_frames) - 1)
        for fraction in (0.25, 0.75)
    ], dtype=np.float64)
    if np.any(np.isclose(positions, np.round(positions))):
        raise RuntimeError("Uniform-synthetic stream contains a native motion position")

    model_426 = load_rife(MODEL_DIRS["rife426"])
    uniform_core = []
    for index, position in enumerate(positions):
        uniform_core.append(rife_frame_at_position(model_426, assembled_native_frames, position, cache=None))
        if index == 0 or (index + 1) % 40 == 0 or index + 1 == len(positions):
            print(f"Uniform-synthetic RIFE: {index + 1}/{len(positions)}")
    model_426 = dispose_rife(model_426)

    uniform_frames = [uniform_core[0].copy(), *uniform_core, uniform_core[-1].copy()]
    expected_output_frames = 2 * len(assembled_native_frames)
    if len(uniform_frames) != expected_output_frames:
        raise RuntimeError("Uniform-synthetic output count is wrong")

    def mild_luma_unsharp(frame):
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        y = ycrcb[:, :, 0].astype(np.float32)
        blurred = cv2.GaussianBlur(y, (0, 0), sigmaX=SHARPEN_SIGMA, sigmaY=SHARPEN_SIGMA)
        ycrcb[:, :, 0] = np.clip(y + SHARPEN_AMOUNT * (y - blurred), 0, 255).astype(np.uint8)
        return cv2.cvtColor(ycrcb, cv2.COLOR_YCrCb2BGR)

    sharpened_frames = [mild_luma_unsharp(frame) for frame in uniform_frames]
    FINAL_MASTER = RUNTIME_OUTPUT / "02_uniform_synthetic_master_720p32.mp4"
    FINAL_SCROLL = RUNTIME_OUTPUT / "03_uniform_synthetic_scroll_gop4_720p32.mp4"
    encode_bgr(sharpened_frames, OUTPUT_FPS, FINAL_MASTER, crf=11, gop=32)
    encode_bgr(sharpened_frames, OUTPUT_FPS, FINAL_SCROLL, crf=15, gop=4)

    # Contact sheet plus consecutive frames around all three joins.
    final_rgb = [cv2.cvtColor(frame, cv2.COLOR_BGR2RGB) for frame in sharpened_frames]
    CONTACT_SHEET = RUNTIME_OUTPUT / "bridge_timeline_contact_sheet.jpg"
    make_contact_sheet(final_rgb, CONTACT_SHEET, "HK → sky → Stanford → approved arcade | final 32 fps proof")

    seam_rows = []
    for name, native_index in SEAMS_NATIVE.items():
        center = 2 * native_index
        indices = list(range(max(0, center - 4), min(len(sharpened_frames), center + 5)))
        while len(indices) < 9:
            indices.append(indices[-1])
        tiles = []
        for index in indices[:9]:
            tile = cv2.resize(sharpened_frames[index], (240, 135), interpolation=cv2.INTER_AREA)
            cv2.rectangle(tile, (0, 0), (240, 25), (12, 12, 12), -1)
            cv2.putText(tile, f"{name} f{index}", (6, 17), cv2.FONT_HERSHEY_SIMPLEX, .42, (255,255,255), 1, cv2.LINE_AA)
            tiles.append(tile)
        seam_rows.append(np.hstack(tiles))
    SEAM_SHEET = RUNTIME_OUTPUT / "bridge_seam_cadence_sheet.jpg"
    cv2.imwrite(str(SEAM_SHEET), np.vstack(seam_rows), [cv2.IMWRITE_JPEG_QUALITY, 95])

    def adjacent_mae(frames, boundary):
        left = frames[max(0, boundary - 1)].astype(np.float32)
        right = frames[min(len(frames) - 1, boundary)].astype(np.float32)
        return float(np.abs(right - left).mean())

    metrics = {
        "native_seam_adjacent_mae": {name: adjacent_mae(assembled_native_frames, index) for name, index in SEAMS_NATIVE.items()},
        "final_seam_adjacent_mae": {name: adjacent_mae(sharpened_frames, 2 * index) for name, index in SEAMS_NATIVE.items()},
        "native_frames": len(assembled_native_frames),
        "output_frames": len(sharpened_frames),
        "duration_seconds": len(sharpened_frames) / OUTPUT_FPS,
        "uniform_synthetic_positions": [0.25, 0.75],
        "native_motion_frames_discarded": True,
        "forced_endpoint_pixels": False,
        "automatic_aesthetic_approval": False,
    }
    METRICS_PATH = RUNTIME_OUTPUT / "bridge_metrics.json"
    METRICS_PATH.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    final_probe = probe_video(FINAL_MASTER)
    scroll_probe = probe_video(FINAL_SCROLL)
    expected_contract = (WIDTH, HEIGHT, OUTPUT_FPS, expected_output_frames)
    for label, result in (("master", final_probe), ("scroll", scroll_probe)):
        actual = (result["width"], result["height"], round(result["fps"]), result["frames"])
        if actual != expected_contract:
            raise RuntimeError(f"{label} contract failed: {result}")
    if maximum_keyframe_gap(FINAL_SCROLL) > 4:
        raise RuntimeError("Scroll encode exceeds GOP-4")
    if abs(final_probe["duration"] - native_probe["duration"]) > 1e-6:
        raise RuntimeError("Interpolation changed the assembled duration")

    artifacts = {}
    deliverables = (FINAL_MASTER, FINAL_SCROLL, CONTACT_SHEET, SEAM_SHEET, METRICS_PATH)
    for path in deliverables:
        digest = atomic_publish(path, DRIVE_OUTPUT / path.name)
        artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}

    manifest = {
        "status": "complete_visual_review_required",
        "experiment_id": EXPERIMENT_ID, "config_fingerprint": CONFIG_FINGERPRINT,
        "sources": source_records, "segments": {
            name: json.loads((segment_dir(name) / "manifest.json").read_text())
            for name in ("A_hk_to_sky", "B_sky_to_stanford")
        },
        "native_proof": {"path": str(DRIVE_OUTPUT / NATIVE_PROOF.name), "probe": native_probe},
        "postprocess": {
            "rife_repo": RIFE_REPO_URL, "rife_commit": RIFE_REPO_COMMIT,
            "model_cache_persisted": False, "method": "uniform synthetic 25%/75% plus mild luma sharpening",
            "master_probe": final_probe, "scroll_probe": scroll_probe,
        },
        "metrics": metrics, "artifacts": artifacts,
        "typography_baked_into_video": False,
        "completed_at_unix": time.time(),
    }
    MANIFEST = RUNTIME_OUTPUT / "bridge_manifest.json"
    MANIFEST.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_digest = atomic_publish(MANIFEST, DRIVE_OUTPUT / MANIFEST.name)

    BUNDLE = RUNTIME_OUTPUT / f"{EXPERIMENT_ID}_review_bundle.zip"
    with zipfile.ZipFile(BUNDLE, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in (FINAL_SCROLL, CONTACT_SHEET, SEAM_SHEET, METRICS_PATH, MANIFEST):
            archive.write(path, arcname=path.name)
    with zipfile.ZipFile(BUNDLE) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("Review bundle integrity failed")
    bundle_digest = atomic_publish(BUNDLE, DRIVE_OUTPUT / BUNDLE.name)

    SUCCESS = DRIVE_OUTPUT / "success.json"
    atomic_write_json(SUCCESS, {
        "status": "complete_visual_review_required",
        "native_proof": str(DRIVE_OUTPUT / NATIVE_PROOF.name),
        "master": str(DRIVE_OUTPUT / FINAL_MASTER.name),
        "scroll_encode": str(DRIVE_OUTPUT / FINAL_SCROLL.name),
        "contact_sheet": str(DRIVE_OUTPUT / CONTACT_SHEET.name),
        "bundle": {"path": str(DRIVE_OUTPUT / BUNDLE.name), "sha256": bundle_digest},
        "manifest_sha256": manifest_digest, "models_persisted": False,
        "next_gate": "Eric reviews the crane-up, cloud continuity, crest-and-dive, and Stanford landing",
    })
    for path in (DRIVE_OUTPUT / FINAL_MASTER.name, DRIVE_OUTPUT / FINAL_SCROLL.name, DRIVE_OUTPUT / BUNDLE.name, SUCCESS):
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Final persistence check failed: {path}")

    display(IPImage(filename=str(CONTACT_SHEET)))
    display(IPImage(filename=str(SEAM_SHEET)))
    display(Video(str(FINAL_SCROLL), embed=True, width=960))
    print("COMPLETE:", DRIVE_OUTPUT)
    print("Native proof:", DRIVE_OUTPUT / NATIVE_PROOF.name)
    print("Scroll encode:", DRIVE_OUTPUT / FINAL_SCROLL.name)
    print("Review bundle:", DRIVE_OUTPUT / BUNDLE.name)

if AUTO_DISCONNECT_ON_SUCCESS:
    disconnect_runtime("Hong Kong-to-Stanford bridge proof completed and persisted")
else:
    _shutdown_started.set()
'''


def code(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(source.strip() + "\n")


def build_notebook() -> nbformat.NotebookNode:
    notebook = nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell(TITLE.strip() + "\n"),
        code(SETTINGS), code(SETUP), code(PREFLIGHT_AND_INSTALL), code(UTILITIES),
        code(SOURCES), code(CONFIG), code(GENERATE), code(ASSEMBLE),
        code(RIFE_CONFIG), code(RIFE_SETUP), code(POSTPROCESS),
    ])
    notebook.metadata = {
        "colab": {"name": OUTPUT.name, "gpuType": "A100", "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.x"},
        "accelerator": "GPU",
    }
    return notebook


def audit(notebook: nbformat.NotebookNode) -> None:
    nbformat.validate(notebook)
    joined = "\n".join(cell.source for cell in notebook.cells)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=f"hk-stanford-bridge-cell-{index}")
            if cell.outputs or cell.execution_count is not None:
                raise AssertionError(f"Notebook output leaked into cell {index}")

    required = (
        MODEL_ID, MODEL_REVISION, DIFFUSERS_COMMIT,
        "S1_tower_flight/candidates/42211/clip.mp4",
        "A_hk_to_sky", "B_sky_to_stanford", "a_natural_last",
        "last_image=last_reference", "城市必须真实地从画面下边缘完全离开",
        "校园之后才从下边缘进入", "无人机，四旋翼",
        '"forced_endpoint_pixels": False', '"crossfade": False',
        "uniform_core", "fraction in (0.25, 0.75)",
        "03_uniform_synthetic_scroll_gop4_720p32.mp4",
        "PERSIST_MODEL_CACHE_TO_DRIVE = False",
        "AUTO_DISCONNECT_ON_ERROR = True", "colab_runtime.unassign()",
    )
    for marker in required:
        if marker not in joined:
            raise AssertionError(f"Missing marker: {marker}")

    forbidden = (
        "crossfade=d", "xfade=", "OPENAI_API_KEY", "PERSIST_MODEL_CACHE_TO_DRIVE = True",
        "frames[0] =", "frames[-1] =", "raw_frames[0] =", "raw_frames[-1] =",
    )
    for marker in forbidden:
        if marker in joined:
            raise AssertionError(f"Forbidden marker: {marker}")
    for pattern in (r"sk-[A-Za-z0-9_-]{20,}", r"hf_[A-Za-z0-9]{20,}", r"AIza[A-Za-z0-9_-]{20,}"):
        if re.search(pattern, joined):
            raise AssertionError("Credential found in notebook")
    if len(json.dumps(notebook)) > 230_000:
        raise AssertionError("Notebook is large enough to risk Colab editor instability")


def synthetic_smoke_test() -> None:
    """Exercise the native/final frame contracts, GOP-4 encode, and ZIP."""
    import numpy as np

    native_count = round(1.5 * 16) + 2 * 41 + 81
    native = []
    for index in range(native_count):
        frame = np.zeros((72, 128, 3), np.uint8)
        frame[:, :, 0] = (index * 3) % 256
        frame[:, :, 1] = np.arange(128, dtype=np.uint8)[None, :]
        native.append(frame)
    final = [frame for frame in native for _ in range(2)]

    def encode(path: Path, frames: list[np.ndarray], fps: int, gop: int) -> None:
        command = [
            "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-s", "128x72", "-r", str(fps), "-i", "-", "-an", "-c:v", "libx264",
            "-crf", "28", "-g", str(gop), "-keyint_min", str(gop),
            "-sc_threshold", "0", "-bf", "0", "-pix_fmt", "yuv420p", str(path),
        ]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        for frame in frames:
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise AssertionError("Synthetic encode failed")

    with tempfile.TemporaryDirectory(prefix="hk-stanford-bridge-smoke-") as directory:
        root = Path(directory)
        native_path = root / "native.mp4"
        final_path = root / "final.mp4"
        encode(native_path, native, 16, 16)
        encode(final_path, final, 32, 4)

        def probe(path: Path) -> tuple[int, float]:
            payload = json.loads(subprocess.run([
                "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                "-show_entries", "stream=nb_read_frames,avg_frame_rate", "-of", "json", str(path),
            ], check=True, capture_output=True, text=True).stdout)["streams"][0]
            numerator, denominator = map(int, payload["avg_frame_rate"].split("/"))
            return int(payload["nb_read_frames"]), numerator / denominator

        if probe(native_path) != (native_count, 16.0):
            raise AssertionError("Synthetic native contract failed")
        if probe(final_path) != (2 * native_count, 32.0):
            raise AssertionError("Synthetic final contract failed")

        flags = json.loads(subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "frame=key_frame", "-of", "json", str(final_path),
        ], check=True, capture_output=True, text=True).stdout)["frames"]
        keys = [index for index, frame in enumerate(flags) if int(frame["key_frame"])]
        gaps = [b - a for a, b in zip(keys, keys[1:])] + [len(flags) - keys[-1]]
        if not keys or keys[0] != 0 or max(gaps) > 4:
            raise AssertionError("Synthetic GOP-4 contract failed")

        bundle = root / "review.zip"
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(final_path, final_path.name)
        with zipfile.ZipFile(bundle) as archive:
            if archive.testzip() is not None:
                raise AssertionError("Synthetic ZIP failed")


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
