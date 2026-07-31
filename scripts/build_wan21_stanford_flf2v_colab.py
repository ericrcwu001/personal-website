#!/usr/bin/env python3
"""Build the punchy Wan 2.1 FLF2V Stanford camera-move Colab notebook."""

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


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "wan21_stanford_whip_first_last_frame_colab.ipynb"

DIFFUSERS_COMMIT = "2919c50962c375e32b9fa40ae5fad50cd3251332"
MODEL_ID = "Wan-AI/Wan2.1-FLF2V-14B-720P-diffusers"
MODEL_REVISION = "17c30769b1e0b5dcaa1799b117bf20a9c31f59d7"


TITLE = r'''
# Stanford speed-ramped camera proof — Wan 2.1 FLF2V 14B

This notebook replaces prompt-only Hunyuan continuation with an actual **first-and-last-frame-conditioned** model. Wan receives two real Stanford photographs:

1. **Start:** Memorial Church framed through the Main Quad arcade.
2. **Finish:** a sunlit, stable view straight down the repeating sandstone arcade.

The requested path is one continuous physical move with a pronounced cinematic speed ramp: a restrained opening, an aggressive rightward track and decisive yaw through the foreground column, then a controlled deceleration into the long arcade. It is not a uniform pan. There is no crossfade, reversed second shot, hidden hard cut, or invented endpoint.

Wan 2.1 FLF2V was selected because the official model and Diffusers pipeline expose `image` plus `last_image` conditioning. The official model card recommends Chinese prompts for FLF2V, so this notebook uses a precise Chinese camera-path prompt. It generates the native supported format: **1280×720, 81 frames, 16 fps**.

Official references:

- [Wan 2.1 FLF2V model](https://huggingface.co/Wan-AI/Wan2.1-FLF2V-14B-720P-diffusers)
- [Diffusers Wan first/last-frame documentation](https://huggingface.co/docs/diffusers/api/pipelines/wan#firstlastframetovideo-generation)

The model is Apache-2.0. The two source photographs retain their Wikimedia Commons attribution requirements. This remains a visual proof until Eric approves it.
'''


SETTINGS = r'''
# User controls. Keep these unchanged for the first proof.
EXPERIMENT_ID = "stanford_wan21_flf2v_whip_720p_v2"
SEED = 95231
WIDTH, HEIGHT = 1280, 720
NUM_FRAMES = 81
FPS = 16
INFERENCE_STEPS = 50
GUIDANCE_SCALE = 5.5
PERSIST_MODEL_CACHE_TO_DRIVE = False

# Billing behavior: success disconnects immediately. Setup/generation errors stay visible.
AUTO_DISCONNECT_ON_SUCCESS = True
HARD_CUTOFF_HOURS = 4.0
FORCE_UNASSIGN_AFTER_SECONDS = 180

if (NUM_FRAMES - 1) % 4:
    raise ValueError("Wan requires NUM_FRAMES = 4n+1")
if (WIDTH, HEIGHT, NUM_FRAMES, FPS) != (1280, 720, 81, 16):
    raise ValueError("This proof is intentionally locked to Wan FLF2V's native 720p/81-frame contract")
print("Experiment:", EXPERIMENT_ID, "| seed:", SEED)
'''


SETUP = r'''
# Mount Drive. Generated media persists; the ~84 GiB model snapshot remains temporary.
from google.colab import drive
from google.colab import drive as colab_drive, runtime as colab_runtime
from pathlib import Path
from PIL import Image, ImageDraw, ImageOps
from IPython.display import Video, display
import fractions, gc, hashlib, io, json, math, os, platform, shutil, subprocess, sys, threading, time, urllib.request, uuid, zipfile

drive.mount("/content/drive", force_remount=False)

DRIVE_ROOT = Path("/content/drive/MyDrive/Personal_Website_Wan21_FLF2V")
DRIVE_INPUTS = DRIVE_ROOT / "inputs"
DRIVE_EXPERIMENT = DRIVE_ROOT / "experiments" / EXPERIMENT_ID
DRIVE_CANDIDATE = DRIVE_EXPERIMENT / "candidate" / str(SEED)

RUNTIME_ROOT = Path("/content/wan21_flf2v_runtime")
RUNTIME_INPUTS = RUNTIME_ROOT / "inputs"
RUNTIME_MODEL = RUNTIME_ROOT / "model"
RUNTIME_EXPERIMENT = RUNTIME_ROOT / "experiments" / EXPERIMENT_ID
RUNTIME_CANDIDATE = RUNTIME_EXPERIMENT / "candidate" / str(SEED)

for path in (DRIVE_INPUTS, DRIVE_EXPERIMENT, DRIVE_CANDIDATE, RUNTIME_INPUTS, RUNTIME_MODEL, RUNTIME_CANDIDATE):
    path.mkdir(parents=True, exist_ok=True)

probe = DRIVE_EXPERIMENT / f".write-probe-{uuid.uuid4().hex}"
payload = f"wan flf2v persistence probe {time.time_ns()}\n"
probe.write_text(payload, encoding="utf-8")
if probe.read_text(encoding="utf-8") != payload:
    raise RuntimeError("Google Drive persistence check failed")
probe.unlink()

def free_gib(path):
    return shutil.disk_usage(path).free / (1024 ** 3)

print("Drive output:", DRIVE_EXPERIMENT)
print("Model cache: temporary local SSD only")
print("Local free:", round(free_gib("/content"), 1), "GiB | Drive free:", round(free_gib(DRIVE_ROOT), 1), "GiB")

# A global cutoff is armed before preflight. Errors remain visible, but billing cannot run indefinitely.
_shutdown_started = threading.Event()
def _global_hard_cutoff():
    if _shutdown_started.wait(HARD_CUTOFF_HOURS * 3600):
        return
    try:
        marker = DRIVE_EXPERIMENT / "hard_cutoff.json"
        marker.write_text(json.dumps({
            "reason": f"hard cutoff after {HARD_CUTOFF_HOURS:.1f} hours",
            "time": time.time(),
        }, indent=2) + "\n", encoding="utf-8")
        colab_drive.flush_and_unmount()
    finally:
        colab_runtime.unassign()
threading.Thread(target=_global_hard_cutoff, name="wan-billing-hard-cutoff", daemon=True).start()
'''


PREFLIGHT = r'''
# Fail visibly without disconnecting so Colab cannot hide the actual problem.
import torch

if not torch.cuda.is_available():
    raise RuntimeError("CUDA unavailable. Select an A100 High-RAM runtime.")
gpu = torch.cuda.get_device_properties(0)
vram_gib = gpu.total_memory / (1024 ** 3)
ram_gib = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)
if "A100" not in gpu.name or vram_gib < 75:
    raise RuntimeError(f"Need A100 80GB; found {gpu.name} with {vram_gib:.1f} GiB")
if ram_gib < 75:
    raise RuntimeError(f"Need High-RAM runtime with at least 75 GiB system RAM; found {ram_gib:.1f}")
if free_gib("/content") < 105:
    raise RuntimeError(f"Need at least 105 GiB local free for the 83.9 GiB snapshot plus outputs; found {free_gib('/content'):.1f}")
if free_gib(DRIVE_ROOT) < 5:
    raise RuntimeError(f"Need at least 5 GiB Drive free for durable media; found {free_gib(DRIVE_ROOT):.1f}")
for binary in ("ffmpeg", "ffprobe"):
    if shutil.which(binary) is None:
        raise RuntimeError(f"Missing binary: {binary}")
print("GPU:", gpu.name, f"{vram_gib:.1f} GiB | RAM: {ram_gib:.1f} GiB")
'''


INSTALL = rf'''
# Install a pinned Diffusers revision whose Wan pipeline signature includes last_image.
DIFFUSERS_COMMIT = "{DIFFUSERS_COMMIT}"
packages = [
    f"git+https://github.com/huggingface/diffusers.git@{{DIFFUSERS_COMMIT}}",
    "transformers==5.14.1", "accelerate==1.14.0", "huggingface-hub==1.24.0",
    "safetensors==0.8.0", "opencv-python-headless==4.12.0.88",
    "imageio==2.37.0", "imageio-ffmpeg==0.6.0", "ftfy==6.3.1",
]
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", *packages])

import accelerate, cv2, diffusers, huggingface_hub, numpy as np, safetensors, transformers
from diffusers import AutoencoderKLWan, WanImageToVideoPipeline
from huggingface_hub import model_info, snapshot_download
from safetensors import safe_open
from transformers import CLIPVisionModel

if not hasattr(diffusers, "WanImageToVideoPipeline"):
    raise RuntimeError("Pinned Diffusers revision lacks WanImageToVideoPipeline")
import inspect
signature = inspect.signature(WanImageToVideoPipeline.__call__)
if "last_image" not in signature.parameters:
    raise RuntimeError(f"Installed Wan pipeline lacks last_image conditioning: {{signature}}")
versions = {{
    "python": platform.python_version(), "torch": torch.__version__, "diffusers": diffusers.__version__,
    "transformers": transformers.__version__, "accelerate": accelerate.__version__,
    "huggingface_hub": huggingface_hub.__version__, "safetensors": safetensors.__version__,
    "diffusers_commit": DIFFUSERS_COMMIT,
}}
print(json.dumps(versions, indent=2))
'''


UTILITIES = r'''
# Integrity, video, and persistence helpers.
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

def atomic_publish_file(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(source)
    temporary = destination.with_name(destination.name + f".part-{digest[:12]}-{uuid.uuid4().hex}")
    shutil.copy2(source, temporary)
    if sha256_file(temporary) != digest:
        temporary.unlink(missing_ok=True)
        raise RuntimeError("Drive copy hash failed")
    os.replace(temporary, destination)
    if sha256_file(destination) != digest:
        raise RuntimeError(f"Published Drive hash failed: {destination}")
    return digest

def probe_video(path):
    result = subprocess.run([
        "ffprobe", "-count_frames", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_read_frames,duration", "-of", "json", str(path),
    ], check=True, capture_output=True, text=True)
    stream = json.loads(result.stdout)["streams"][0]
    return {
        "width": int(stream["width"]), "height": int(stream["height"]),
        "fps": float(fractions.Fraction(stream["avg_frame_rate"])),
        "frames": int(stream["nb_read_frames"]), "duration": float(stream.get("duration") or 0),
    }

def maximum_keyframe_gap(path):
    result = subprocess.run([
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "frame=key_frame", "-of", "json", str(path),
    ], check=True, capture_output=True, text=True)
    flags = [int(frame["key_frame"]) for frame in json.loads(result.stdout)["frames"]]
    keys = [index for index, flag in enumerate(flags) if flag]
    if not keys or keys[0] != 0:
        return len(flags)
    return max([right - left for left, right in zip(keys, keys[1:])] + [len(flags) - keys[-1]])

def frame_to_uint8(frame):
    if isinstance(frame, Image.Image):
        return np.asarray(frame.convert("RGB"), dtype=np.uint8)
    array = np.asarray(frame)
    if np.issubdtype(array.dtype, np.floating) and array.max(initial=0) <= 1.01:
        array = array * 255
    return np.clip(array, 0, 255).astype(np.uint8)[:, :, :3]

def normalize_output(output):
    frames = output.frames[0]
    if isinstance(frames, np.ndarray) and frames.ndim == 4:
        frames = list(frames)
    return [frame_to_uint8(frame) for frame in frames]

def encode_video(frames, destination, crf=16, gop=None):
    first = frame_to_uint8(frames[0])
    height, width = first.shape[:2]
    command = [
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s:v", f"{width}x{height}", "-r", str(FPS), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "slow", "-crf", str(crf), "-pix_fmt", "yuv420p",
    ]
    if gop:
        command += ["-g", str(gop), "-keyint_min", str(gop), "-sc_threshold", "0", "-bf", "0", "-tune", "fastdecode"]
    command += ["-movflags", "+faststart", str(destination)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for frame in frames:
            process.stdin.write(frame_to_uint8(frame).tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0:
        raise RuntimeError("ffmpeg encoding failed")

def write_contact_sheet(frames, destination, label):
    indices = np.linspace(0, len(frames) - 1, 12, dtype=int)
    sheet = Image.new("RGB", (1280, 720), "#111111")
    draw = ImageDraw.Draw(sheet)
    for position, index in enumerate(indices):
        tile = Image.fromarray(frame_to_uint8(frames[index])).resize((320, 180), Image.Resampling.LANCZOS)
        x, y = (position % 4) * 320, (position // 4) * 240
        sheet.paste(tile, (x, y))
        draw.rectangle((x, y + 180, x + 320, y + 210), fill="#111111")
        draw.text((x + 8, y + 188), f"frame {index:03d}", fill="white")
    draw.rectangle((0, 0, 620, 30), fill="black")
    draw.text((8, 8), label, fill="white")
    sheet.save(destination, "JPEG", quality=92, optimize=True)
'''


CONFIG = rf'''
# Pinned model, real endpoints, and a physically explicit Chinese FLF2V prompt.
MODEL = {{
    "repo_id": "{MODEL_ID}",
    "revision": "{MODEL_REVISION}",
    "expected_snapshot_gib": 83.93,
    "license": "Apache-2.0",
}}

REFERENCES = {{
    "first": {{
        "filename": "stanford_church_arcade_real_original.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/b/b6/Stanford_University_Arches_with_Memorial_Church_in_the_background.jpg",
        "sha256": "17601f44f530af14e7f25a1d3a8d0894e81494d98d68eec6bc5c71546dff4a51",
        "author": "Jawed Karim", "license": "CC BY-SA 4.0",
        "source_page": "https://commons.wikimedia.org/wiki/File:Stanford_University_Arches_with_Memorial_Church_in_the_background.jpg",
        "centering": [0.50, 0.50],
    }},
    "last": {{
        "filename": "stanford_arches_main_quad_real_original.jpg",
        "url": "https://upload.wikimedia.org/wikipedia/commons/0/0a/Stanford_University_Arches_of_Main_Quad.jpg",
        "sha256": "65205f306652e41c31b91d7bccb61c06f40edd574b8e007dd3f4fdcd0a49b864",
        "author": "Fred Hsu", "license": "CC BY-SA 3.0",
        "source_page": "https://commons.wikimedia.org/wiki/File:Stanford_University_Arches_of_Main_Quad.jpg",
        "centering": [0.50, 0.52],
    }},
}}

PROMPT = (
    "写实电影摄影，同一个真实地点、同一个连续镜头、绝对没有剪辑。起始画面是给定的真实斯坦福纪念教堂和主方院拱廊。"
    "固定24毫米广角电影镜头，水平视线，真实三维摄影机运动；不是照片平移，不是原地摇摄，不是镜头变焦。"
    "前百分之十五几乎静止，只做非常轻微的稳定器向右滑动，让观众清楚看到纪念教堂。"
    "随后摄影机突然但平滑地强力加速，沿弧形轨迹快速向右横移，同时果断向右旋转约七十度。"
    "这是有电影感的速度渐变和甩动式中段：最近的砂岩柱以强烈真实视差从画面右侧高速扫过中央并冲向左侧，"
    "纪念教堂迅速离开画面，地砖、近柱、远处拱门以明显不同速度移动；中段必须比开头和结尾快至少四倍。"
    "高速中段具有自然方向性运动模糊，但摄影机路径稳定，没有手持抖动，没有画面跳跃。"
    "穿过柱子后立刻开始明显而连续的减速，最后百分之二十平滑锁定到给定终止画面：正对长拱廊的稳定构图。"
    "运动节奏必须是极慢开始、爆发式快速中段、极慢结束，而不是匀速横摇。"
    "保持刚性建筑、正确拱门数量、真实砂岩纹理、暖色侧光、自然曝光和照片级真实感。"
)
NEGATIVE_PROMPT = (
    "交叉淡化，溶解，隐形剪辑，跳切，传送门，建筑变形，柱子弯曲，重复拱门，融化石材，照片平面旋转，"
    "匀速横摇，轻柔缓慢平移，普通摇摄，原地摇摄，数码变焦，光学变焦，无人机，四旋翼，摄像设备，"
    "漂浮物体，手持抖动，微小来回振动，闪烁，冻结画面，生硬停止，卡通，插画，微缩模型，文字，字幕，标志，水印"
)

STABLE_CONFIG = {{
    "experiment_id": EXPERIMENT_ID, "seed": SEED, "width": WIDTH, "height": HEIGHT,
    "num_frames": NUM_FRAMES, "fps": FPS, "steps": INFERENCE_STEPS,
    "guidance_scale": GUIDANCE_SCALE, "model": MODEL, "references": REFERENCES,
    "prompt": PROMPT, "negative_prompt": NEGATIVE_PROMPT,
    "camera_path": "restrained opening, aggressive curved rightward track plus ~70-degree yaw, controlled lock-off",
    "pixel_crossfade": False, "hidden_hard_cut": False,
}}
CONFIG_FINGERPRINT = hashlib.sha256(json.dumps(STABLE_CONFIG, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
print("Configuration:", CONFIG_FINGERPRINT)
'''


REFERENCES_CELL = r'''
# Download only two small verified photographs, cache them on Drive, and show the exact 720p endpoints.
def download_verified(record, destination):
    destination = Path(destination)
    if destination.is_file() and sha256_file(destination) == record["sha256"]:
        return destination
    last_error = None
    for attempt in range(5):
        try:
            request = urllib.request.Request(record["url"], headers={"User-Agent": "Eric-Wu-portfolio-reference/1.0"})
            with urllib.request.urlopen(request, timeout=180) as response:
                payload = response.read()
            if hashlib.sha256(payload).hexdigest() != record["sha256"]:
                raise RuntimeError("Reference hash mismatch")
            temporary = destination.with_name(destination.name + f".part-{uuid.uuid4().hex}")
            temporary.write_bytes(payload)
            os.replace(temporary, destination)
            return destination
        except Exception as error:
            last_error = error
            if attempt < 4:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Reference download failed after retries: {last_error}")

ENDPOINTS = {}
provenance = {}
for role, record in REFERENCES.items():
    drive_original = download_verified(record, DRIVE_INPUTS / record["filename"])
    image = ImageOps.fit(
        Image.open(drive_original).convert("RGB"), (WIDTH, HEIGHT),
        method=Image.Resampling.LANCZOS, centering=tuple(record["centering"]),
    )
    local_endpoint = RUNTIME_INPUTS / f"{role}_endpoint_1280x720.png"
    drive_endpoint = DRIVE_EXPERIMENT / local_endpoint.name
    image.save(local_endpoint, "PNG", optimize=True)
    endpoint_digest = atomic_publish_file(local_endpoint, drive_endpoint)
    ENDPOINTS[role] = image
    provenance[role] = {**{key: value for key, value in record.items() if key != "centering"},
                        "endpoint_sha256": endpoint_digest, "endpoint_size": [WIDTH, HEIGHT]}

atomic_write_json(DRIVE_EXPERIMENT / "reference_provenance.json", provenance)
sheet = Image.new("RGB", (1280, 760), "#111111")
sheet.paste(ENDPOINTS["first"].resize((640, 360), Image.Resampling.LANCZOS), (0, 0))
sheet.paste(ENDPOINTS["last"].resize((640, 360), Image.Resampling.LANCZOS), (640, 0))
draw = ImageDraw.Draw(sheet)
draw.text((12, 370), "FIRST — Memorial Church framed by arcade", fill="white")
draw.text((652, 370), "LAST — exact long-arcade composition", fill="white")
draw.text((12, 420), "Path: slow hold -> aggressive right track + ~70-degree yaw -> slow corridor lock-off", fill="white")
sheet_path = RUNTIME_EXPERIMENT / "first_last_endpoint_sheet.jpg"
sheet.save(sheet_path, "JPEG", quality=93, optimize=True)
atomic_publish_file(sheet_path, DRIVE_EXPERIMENT / sheet_path.name)
display(sheet)
'''


GENERATE = r'''
# Download temporarily, generate one 720p FLF2V proof, persist it, and retain failures for debugging.

def disconnect_runtime_safely(reason):
    if not AUTO_DISCONNECT_ON_SUCCESS or _shutdown_started.is_set():
        return
    _shutdown_started.set()
    print("AUTO-DISCONNECT:", reason)
    fallback = threading.Timer(FORCE_UNASSIGN_AFTER_SECONDS, colab_runtime.unassign)
    fallback.daemon = True
    fallback.start()
    try:
        atomic_write_json(DRIVE_EXPERIMENT / "runtime_shutdown.json", {
            "reason": reason, "requested_at_unix": time.time(), "outputs_persisted": "see success.json",
        })
        colab_drive.flush_and_unmount()
    except Exception as error:
        print("Drive flush/unmount warning:", repr(error))
    try:
        colab_runtime.unassign()
    except Exception as error:
        print("Runtime deletion warning; fallback remains armed:", repr(error))

def candidate_valid():
    manifest_path = DRIVE_CANDIDATE / "manifest.json"
    if not manifest_path.is_file():
        return False
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete" or manifest.get("config_fingerprint") != CONFIG_FINGERPRINT:
            return False
        for name, record in manifest["artifacts"].items():
            path = DRIVE_CANDIDATE / name
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                return False
        probe = probe_video(DRIVE_CANDIDATE / "stanford_wan21_flf2v_720p16.mp4")
        return (probe["width"], probe["height"], probe["fps"], probe["frames"]) == (WIDTH, HEIGHT, float(FPS), NUM_FRAMES)
    except Exception:
        return False

model_directory = None
pipe = None
generation_succeeded = False
if candidate_valid():
    print("Validated existing candidate; skipping model download and generation.")
else:
    started = time.time()
    try:
        info = model_info(MODEL["repo_id"], revision=MODEL["revision"], files_metadata=True)
        if info.sha != MODEL["revision"]:
            raise RuntimeError("Pinned Wan model revision changed")
        expected = {item.rfilename: item.size for item in info.siblings if item.size is not None}
        expected_bytes = sum(expected.values())
        if not 82 * 1024 ** 3 < expected_bytes < 86 * 1024 ** 3:
            raise RuntimeError(f"Unexpected Wan snapshot size: {expected_bytes / 1024 ** 3:.2f} GiB")
        if free_gib("/content") < expected_bytes / 1024 ** 3 + 15:
            raise RuntimeError("Insufficient local SSD for the pinned Wan snapshot plus 15 GiB reserve")

        model_directory = Path(snapshot_download(
            repo_id=MODEL["repo_id"], revision=MODEL["revision"],
            local_dir=str(RUNTIME_MODEL), max_workers=4,
        ))
        invalid = [name for name, size in expected.items()
                   if not (model_directory / name).is_file() or (model_directory / name).stat().st_size != size]
        if invalid:
            raise RuntimeError(f"Incomplete model snapshot: {invalid[:5]}")
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

        output = pipe(
            image=ENDPOINTS["first"], last_image=ENDPOINTS["last"],
            prompt=PROMPT, negative_prompt=NEGATIVE_PROMPT,
            height=HEIGHT, width=WIDTH, num_frames=NUM_FRAMES,
            num_inference_steps=INFERENCE_STEPS, guidance_scale=GUIDANCE_SCALE,
            generator=torch.Generator(device="cuda").manual_seed(SEED), output_type="np",
        )
        raw_frames = normalize_output(output)
        if len(raw_frames) != NUM_FRAMES:
            raise RuntimeError(f"Wan returned {len(raw_frames)} frames instead of {NUM_FRAMES}")

        first_exact = np.asarray(ENDPOINTS["first"], dtype=np.uint8)
        last_exact = np.asarray(ENDPOINTS["last"], dtype=np.uint8)
        raw_first_mae = float(np.abs(raw_frames[0].astype(np.float32) - first_exact.astype(np.float32)).mean())
        raw_last_mae = float(np.abs(raw_frames[-1].astype(np.float32) - last_exact.astype(np.float32)).mean())

        def flow_magnitude(left, right):
            a = cv2.cvtColor(cv2.resize(left, (320, 180)), cv2.COLOR_RGB2GRAY)
            b = cv2.cvtColor(cv2.resize(right, (320, 180)), cv2.COLOR_RGB2GRAY)
            flow = cv2.calcOpticalFlowFarneback(a, b, None, .5, 3, 21, 3, 5, 1.2, 0)
            return float(np.median(np.linalg.norm(flow, axis=2)))

        flows = [flow_magnitude(a, b) for a, b in zip(raw_frames, raw_frames[1:])]
        edge_flow = float(np.median(np.asarray(flows[:16] + flows[-16:])))
        middle_flow_p75 = float(np.percentile(flows[24:56], 75))
        whip_speed_ratio = middle_flow_p75 / max(edge_flow, 0.05)
        camera_motion_gate_pass = whip_speed_ratio >= 4.0
        metrics = {
            "raw_first_endpoint_mae": raw_first_mae,
            "raw_last_endpoint_mae": raw_last_mae,
            "forced_exact_endpoint_pixels": False,
            "first_adjacent_mae": float(np.abs(raw_frames[1].astype(np.float32) - raw_frames[0].astype(np.float32)).mean()),
            "last_adjacent_mae": float(np.abs(raw_frames[-1].astype(np.float32) - raw_frames[-2].astype(np.float32)).mean()),
            "median_flow": float(np.median(flows)), "mean_flow": float(np.mean(flows)),
            "first_third_flow": float(np.median(flows[:27])),
            "middle_third_flow": float(np.median(flows[27:54])),
            "last_third_flow": float(np.median(flows[54:])),
            "edge_flow": edge_flow,
            "middle_flow_p75": middle_flow_p75,
            "whip_speed_ratio": whip_speed_ratio,
            "camera_motion_gate_pass": camera_motion_gate_pass,
            "camera_motion_gate": "middle 75th-percentile flow must be at least 4x combined opening/closing median flow",
            "automatic_rejection_enabled": False,
            "reason": "human review still decides whether the physical path, speed ramp, and architecture look cinematic",
        }

        clip = RUNTIME_CANDIDATE / "stanford_wan21_flf2v_720p16.mp4"
        contact = RUNTIME_CANDIDATE / "timeline_contact_sheet.jpg"
        final_frame = RUNTIME_CANDIDATE / "final_frame.png"
        metrics_path = RUNTIME_CANDIDATE / "motion_metrics.json"
        encode_video(raw_frames, clip, crf=16)
        write_contact_sheet(raw_frames, contact, f"Wan 2.1 FLF2V whip proof | seed {SEED} | native model endpoints")
        Image.fromarray(raw_frames[-1]).save(final_frame, "PNG", optimize=True)
        metrics_path.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")

        artifacts = {}
        for path in (clip, contact, final_frame, metrics_path):
            digest = atomic_publish_file(path, DRIVE_CANDIDATE / path.name)
            artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}
        atomic_write_json(DRIVE_CANDIDATE / "manifest.json", {
            "status": "complete", "visual_status": "manual_review_required",
            "config_fingerprint": CONFIG_FINGERPRINT, "config": STABLE_CONFIG,
            "versions": versions, "metrics": metrics, "artifacts": artifacts,
            "started_at_unix": started, "completed_at_unix": time.time(),
            "caption_windows": [
                {"id": "stanford_a", "seconds": [0.0, 2.5], "lines": ["Stanford Class of 2029"]},
                {"id": "stanford_b", "seconds": [2.5, NUM_FRAMES / FPS],
                 "icons": ["GitHub", "LinkedIn", "X", "Instagram", "Email"]},
            ],
            "pixel_crossfade": False, "hidden_hard_cut": False, "first_last_conditioning": True,
        })
        generation_succeeded = True
    except Exception as error:
        atomic_write_json(DRIVE_EXPERIMENT / "runtime_error.json", {
            "error_type": type(error).__name__, "error": str(error), "recorded_at_unix": time.time(),
            "note": "Runtime intentionally remains connected for debugging; success is the only immediate disconnect.",
        })
        raise
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
        if generation_succeeded and model_directory is not None and not PERSIST_MODEL_CACHE_TO_DRIVE:
            shutil.rmtree(model_directory)
            print("Released temporary 83.9 GiB Wan snapshot")

display(Image.open(DRIVE_CANDIDATE / "timeline_contact_sheet.jpg"))
display(Video(str(DRIVE_CANDIDATE / "stanford_wan21_flf2v_720p16.mp4"), embed=True, width=960))
'''


DELIVER = r'''
# Create a GOP-4 scrub master and bidirectional preview, verify Drive, bundle, then disconnect.
master = DRIVE_CANDIDATE / "stanford_wan21_flf2v_720p16.mp4"
scrub = RUNTIME_EXPERIMENT / "stanford_wan21_flf2v_scrub_gop4_720p16.mp4"
pingpong = RUNTIME_EXPERIMENT / "stanford_wan21_flf2v_bidirectional_preview.mp4"

subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(master), "-an", "-c:v", "libx264",
    "-preset", "slow", "-crf", "17", "-g", "4", "-keyint_min", "4", "-sc_threshold", "0",
    "-bf", "0", "-tune", "fastdecode", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(scrub),
], check=True)
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(master),
    "-filter_complex", "[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[a];"
                       "[r]reverse,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]",
    "-map", "[v]", "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "slow", "-crf", "17",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(pingpong),
], check=True)

if (probe_video(scrub)["frames"], maximum_keyframe_gap(scrub)) != (NUM_FRAMES, 4):
    raise RuntimeError(f"Invalid scrub master: {probe_video(scrub)}, GOP {maximum_keyframe_gap(scrub)}")
if probe_video(pingpong)["frames"] != NUM_FRAMES * 2:
    raise RuntimeError(f"Invalid bidirectional preview: {probe_video(pingpong)}")

published = {}
for path in (scrub, pingpong):
    digest = atomic_publish_file(path, DRIVE_EXPERIMENT / path.name)
    published[path.name] = {"bytes": path.stat().st_size, "sha256": digest}

review_files = [
    master, DRIVE_CANDIDATE / "timeline_contact_sheet.jpg", DRIVE_CANDIDATE / "final_frame.png",
    DRIVE_CANDIDATE / "motion_metrics.json", DRIVE_CANDIDATE / "manifest.json",
    DRIVE_EXPERIMENT / "first_endpoint_1280x720.png", DRIVE_EXPERIMENT / "last_endpoint_1280x720.png",
    DRIVE_EXPERIMENT / "first_last_endpoint_sheet.jpg", DRIVE_EXPERIMENT / "reference_provenance.json",
    DRIVE_EXPERIMENT / scrub.name, DRIVE_EXPERIMENT / pingpong.name,
]
bundle = RUNTIME_EXPERIMENT / "stanford_wan21_flf2v_review_bundle.zip"
with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
    for path in review_files:
        archive.write(path, arcname=path.name)
with zipfile.ZipFile(bundle) as archive:
    if archive.testzip() is not None:
        raise RuntimeError("Review ZIP integrity failed")
bundle_digest = atomic_publish_file(bundle, DRIVE_EXPERIMENT / bundle.name)
published[bundle.name] = {"bytes": bundle.stat().st_size, "sha256": bundle_digest}

for name, record in published.items():
    path = DRIVE_EXPERIMENT / name
    if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
        raise RuntimeError(f"Final Drive verification failed: {name}")

atomic_write_json(DRIVE_EXPERIMENT / "success.json", {
    "status": "complete_visual_review_required", "experiment_id": EXPERIMENT_ID,
    "config_fingerprint": CONFIG_FINGERPRINT, "model_cache_persisted": PERSIST_MODEL_CACHE_TO_DRIVE,
    "native_contract": {"width": WIDTH, "height": HEIGHT, "frames": NUM_FRAMES, "fps": FPS},
    "artifacts": published, "next_gate": "Eric reviews the physical camera path before website integration",
})
if json.loads((DRIVE_EXPERIMENT / "success.json").read_text())["status"] != "complete_visual_review_required":
    raise RuntimeError("Success marker did not persist")

print("PERSISTED MASTER:", master)
print("PERSISTED REVIEW BUNDLE:", DRIVE_EXPERIMENT / bundle.name)
print("The 83.9 GiB model snapshot was not copied to Drive.")
disconnect_runtime_safely("Wan first/last-frame Stanford proof completed and all outputs verified on Drive")
'''


def code(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(source.strip() + "\n")


def build_notebook() -> nbformat.NotebookNode:
    cells = [
        nbformat.v4.new_markdown_cell(TITLE.strip() + "\n"),
        code(SETTINGS), code(SETUP), code(PREFLIGHT), code(INSTALL), code(UTILITIES),
        code(CONFIG), code(REFERENCES_CELL), code(GENERATE), code(DELIVER),
    ]
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
            ast.parse(cell.source, filename=f"wan-flf2v-cell-{index}")
            if cell.outputs or cell.execution_count is not None:
                raise AssertionError(f"Output leaked into cell {index}")
    required = (
        MODEL_ID, MODEL_REVISION, DIFFUSERS_COMMIT, "last_image=ENDPOINTS[\"last\"]",
        "NUM_FRAMES = 81", "WIDTH, HEIGHT = 1280, 720", "GUIDANCE_SCALE = 5.5",
        "果断向右旋转约七十度", "中段必须比开头和结尾快至少四倍", "极慢开始、爆发式快速中段、极慢结束",
        '"forced_exact_endpoint_pixels": False', '"whip_speed_ratio": whip_speed_ratio',
        "PERSIST_MODEL_CACHE_TO_DRIVE = False", "expected_snapshot_gib\": 83.93",
        "AUTO_DISCONNECT_ON_SUCCESS = True", "Runtime intentionally remains connected for debugging",
        "stanford_wan21_flf2v_scrub_gop4_720p16.mp4", "first_last_conditioning\": True",
        "license\": \"Apache-2.0", "CC BY-SA 4.0", "CC BY-SA 3.0",
    )
    for marker in required:
        if marker not in joined:
            raise AssertionError(f"Missing marker: {marker}")
    for forbidden in (
        "EMBEDDED_SOURCE_CLIP_PARTS", "crossfade=d", "reverse_second_shot", "OPENAI_API_KEY",
        'raw_frames[0] = first_exact', 'raw_frames[-1] = last_exact',
    ):
        if forbidden in joined:
            raise AssertionError(f"Forbidden marker: {forbidden}")
    for pattern in (r"sk-[A-Za-z0-9_-]{20,}", r"hf_[A-Za-z0-9]{20,}", r"AIza[A-Za-z0-9_-]{20,}"):
        if re.search(pattern, joined):
            raise AssertionError("Credential found")
    if len(json.dumps(notebook)) > 180_000:
        raise AssertionError("Notebook grew large enough to risk Colab editor instability")


def synthetic_smoke_test() -> None:
    """Verify native video structure, GOP-4 scrubbing, ping-pong, and ZIP integrity."""
    import fractions

    import numpy as np

    frames = []
    for index in range(81):
        frame = np.zeros((72, 128, 3), np.uint8)
        frame[:, :, 0] = (index * 3) % 256
        frame[:, :, 1] = np.arange(128, dtype=np.uint8)[None, :]
        frames.append(frame)

    def encode(path: Path, gop: int | None = None) -> None:
        command = [
            "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
            "-s:v", "128x72", "-r", "16", "-i", "-", "-an", "-c:v", "libx264",
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
            raise AssertionError("Synthetic encode failed")

    def probe(path: Path) -> tuple[int, float]:
        output = subprocess.run([
            "ffprobe", "-count_frames", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=avg_frame_rate,nb_read_frames", "-of", "json", str(path),
        ], check=True, capture_output=True, text=True).stdout
        stream = json.loads(output)["streams"][0]
        return int(stream["nb_read_frames"]), float(fractions.Fraction(stream["avg_frame_rate"]))

    with tempfile.TemporaryDirectory(prefix="wan-flf2v-smoke-") as directory:
        root = Path(directory)
        master, scrub, pingpong = root / "master.mp4", root / "scrub.mp4", root / "pingpong.mp4"
        encode(master)
        encode(scrub, 4)
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-i", str(master),
            "-filter_complex", "[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[a];"
                               "[r]reverse,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-an", "-r", "16", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(pingpong),
        ], check=True)
        if probe(master) != (81, 16.0) or probe(scrub) != (81, 16.0) or probe(pingpong) != (162, 16.0):
            raise AssertionError("Synthetic structure failed")
        flags = json.loads(subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=key_frame",
            "-of", "json", str(scrub),
        ], check=True, capture_output=True, text=True).stdout)["frames"]
        keys = [index for index, frame in enumerate(flags) if int(frame["key_frame"])]
        gaps = [right - left for left, right in zip(keys, keys[1:])] + [len(flags) - keys[-1]]
        if not keys or keys[0] != 0 or max(gaps) > 4:
            raise AssertionError("Synthetic GOP failed")
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
