#!/usr/bin/env python3
"""Build Eric Wu's self-contained SkyReels V2 Google Colab notebook."""

from __future__ import annotations

import ast
import base64
import hashlib
import io
import json
import re
from pathlib import Path

import nbformat
from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "skyreels_v2_portfolio_intro_colab.ipynb"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def webp_bytes(image: Image.Image, *, quality: int = 92) -> bytes:
    buffer = io.BytesIO()
    image.convert("RGB").save(buffer, "WEBP", quality=quality, method=6)
    return buffer.getvalue()


def fit(path: Path, size: tuple[int, int] = (1280, 720), centering=(0.5, 0.5)) -> Image.Image:
    with Image.open(path) as source:
        return ImageOps.fit(source.convert("RGB"), size, Image.Resampling.LANCZOS, centering=centering)


def build_anchors() -> dict[str, dict[str, str | int]]:
    hk_wide = fit(ROOT / "output/ai-cinematic/sora-production/anchors/hk-braemar-1280x720.webp")

    with Image.open(ROOT / "web/public/media/depth/hong-kong.webp") as source:
        source = source.convert("RGB")
        # A 2.30x spatial push centered on Two IFC and Bank of China Tower.
        crop_width = round(source.width / 2.30)
        crop_height = round(crop_width * 9 / 16)
        left = min(source.width - crop_width, 1080)
        top = min(source.height - crop_height, 565)
        hk_close = source.crop((left, top, left + crop_width, top + crop_height)).resize(
            (1280, 720), Image.Resampling.LANCZOS
        )

    church = fit(ROOT / "output/imagegen/memorial-church-base.png", centering=(0.52, 0.52))
    arcade = fit(ROOT / "web/public/media/stanford-arcade.webp", centering=(0.5, 0.5))

    records = {
        "hk_braemar_wide": (
            hk_wide,
            "Local portfolio anchor: Braemar Hill late-golden-hour Hong Kong wide.",
        ),
        "hk_central_close": (
            hk_close,
            "Deterministic 2.30x crop from the local Hong Kong source, centered on Two IFC and Bank of China Tower.",
        ),
        "stanford_memorial_church": (
            church,
            "Local AI-assisted Memorial Church anchor approved for the portfolio concept.",
        ),
        "stanford_main_quad_arcade": (
            arcade,
            "Local Main Quad arcade reference; no page text is burned into the image.",
        ),
    }

    result: dict[str, dict[str, str | int]] = {}
    for name, (image, provenance) in records.items():
        payload = webp_bytes(image)
        result[name] = {
            "filename": f"{name}.webp",
            "mime": "image/webp",
            "width": 1280,
            "height": 720,
            "sha256": sha256_bytes(payload),
            "provenance": provenance,
            "base64": base64.b64encode(payload).decode("ascii"),
        }
    return result


def md(source: str):
    return nbformat.v4.new_markdown_cell(source.strip() + "\n")


def code(source: str):
    return nbformat.v4.new_code_cell(source.strip() + "\n", execution_count=None, outputs=[])


def build_notebook() -> nbformat.NotebookNode:
    anchors = build_anchors()
    anchors_json = json.dumps(anchors, sort_keys=True, separators=(",", ":"))

    cells = [
        md(
            """
# SkyReels V2 — persistent portfolio-intro production run

This notebook generates the landscape Hong Kong → Stanford opening as one perceived impossible camera move using **SkyReels V2 locally on the Colab GPU**. It calls no paid video API.

The generation is deliberately staged for recovery and continuity:

1. Braemar Hill wide → a large physical push toward Two IFC and Bank of China Tower.
2. The same moving camera continues into complete volumetric cloud cover.
3. The actual final cloud frame reveals Stanford Memorial Church.
4. The camera continues into complete architectural darkness behind a sandstone column.
5. The actual final dark frame reveals the Main Quad arcade.

There are **no crossfades, dissolves, portals, flashes, or morph transitions** in assembly. Visible geometry is continued from the preceding 17 generated frames. The only model restarts occur from the exact generated cloud/dark boundary frames.

Run on a **Colab High-RAM A100**. The notebook inspects actual GPU VRAM: an 80 GB A100 selects 14B/720p; a 40 GB A100 selects the safer 1.3B/540p checkpoint and upscales the final film. All anchors, completed stage media, history frames, manifests, and final deliverables persist under `MyDrive/Personal_Website_SkyReelsV2`. Model-weight persistence is optional because it consumes 27–75 GiB of Drive.

SkyReels uses the Skywork license. This notebook is configured for Eric's personal portfolio production; review the model license before materially different commercial use.
"""
        ),
        code(
            """
# User controls. These defaults run the complete final-quality production.
RUN_ID = "intro_v1"
QUALITY_MODE = "final"             # "preview" or "final"
FORCE_PROFILE = None                # None, "14b_720p", or "1p3b_540p"
PERSIST_MODEL_CACHE_TO_DRIVE = False  # True costs ~75 GiB (14B) or ~27 GiB (1.3B) of Drive

# To create a different creative candidate, change RUN_ID instead of overwriting a completed run.
if QUALITY_MODE not in {"preview", "final"}:
    raise ValueError("QUALITY_MODE must be 'preview' or 'final'")
if FORCE_PROFILE not in {None, "14b_720p", "1p3b_540p"}:
    raise ValueError("Unknown FORCE_PROFILE")
if not RUN_ID or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for ch in RUN_ID):
    raise ValueError("RUN_ID may contain only letters, numbers, underscores, and hyphens")

FPS = 24
OVERLAP_HISTORY = 17
INFERENCE_STEPS = 50 if QUALITY_MODE == "final" else 30
GUIDANCE_SCALE = 5.0
ADDNOISE_CONDITION = 20
BASE_WINDOW_CANDIDATES = [49, 37, 25]  # automatic OOM recovery; all are 4n+1
print("Run:", RUN_ID, "| quality:", QUALITY_MODE)
"""
        ),
        code(
            """
# Mount Drive and prove that persistence is actually writable.
from google.colab import drive
from pathlib import Path
import json, os, shutil, subprocess, sys, time, uuid

drive.mount("/content/drive", force_remount=False)

DRIVE_ROOT = Path("/content/drive/MyDrive/Personal_Website_SkyReelsV2")
DRIVE_INPUTS = DRIVE_ROOT / "inputs"
DRIVE_CACHE = DRIVE_ROOT / "cache"
DRIVE_RUN = DRIVE_ROOT / "runs" / RUN_ID
DRIVE_STAGES = DRIVE_RUN / "stages"
DRIVE_FINAL = DRIVE_RUN / "deliverables"
DRIVE_LOGS = DRIVE_RUN / "logs"
DRIVE_PROVENANCE = DRIVE_RUN / "provenance"

RUNTIME_ROOT = Path("/content/skyreels_runtime")
RUNTIME_INPUTS = RUNTIME_ROOT / "inputs"
RUNTIME_MODELS = RUNTIME_ROOT / "models"
RUNTIME_RUN = RUNTIME_ROOT / "runs" / RUN_ID

for path in (
    DRIVE_INPUTS, DRIVE_CACHE, DRIVE_STAGES, DRIVE_FINAL, DRIVE_LOGS, DRIVE_PROVENANCE,
    RUNTIME_INPUTS, RUNTIME_MODELS, RUNTIME_RUN,
):
    path.mkdir(parents=True, exist_ok=True)

probe = DRIVE_ROOT / f".write-probe-{uuid.uuid4().hex}"
probe_payload = f"drive persistence probe {time.time_ns()}\\n"
probe.write_text(probe_payload, encoding="utf-8")
if probe.read_text(encoding="utf-8") != probe_payload:
    raise RuntimeError("Google Drive write/read verification failed")
probe.unlink()

if str(RUNTIME_ROOT).startswith("/content/drive"):
    raise RuntimeError("Inference must run on local SSD, not Drive FUSE")

def free_gib(path):
    return shutil.disk_usage(path).free / (1024 ** 3)

print("Persistence root:", DRIVE_ROOT)
print("Local free:", round(free_gib("/content"), 1), "GiB")
print("Drive free:", round(free_gib(DRIVE_ROOT), 1), "GiB")
"""
        ),
        code(
            f"""
# Restore the four bundled visual anchors to both Drive and the local inference SSD.
import base64, hashlib, io
from PIL import Image

EMBEDDED_ANCHORS = json.loads(r'''{anchors_json}''')
ANCHOR_LOCAL_PATHS = {{}}
anchor_manifest = {{}}

for name, record in EMBEDDED_ANCHORS.items():
    payload = base64.b64decode(record["base64"])
    digest = hashlib.sha256(payload).hexdigest()
    if digest != record["sha256"]:
        raise RuntimeError(f"Embedded anchor hash mismatch: {{name}}")
    with Image.open(io.BytesIO(payload)) as image:
        image.load()
        if image.size != (record["width"], record["height"]):
            raise RuntimeError(f"Embedded anchor dimensions changed: {{name}}")

    drive_path = DRIVE_INPUTS / record["filename"]
    if not drive_path.exists() or hashlib.sha256(drive_path.read_bytes()).hexdigest() != digest:
        temp = drive_path.with_name(drive_path.name + f".part-{{uuid.uuid4().hex}}")
        temp.write_bytes(payload)
        os.replace(temp, drive_path)

    local_path = RUNTIME_INPUTS / record["filename"]
    local_path.write_bytes(payload)
    ANCHOR_LOCAL_PATHS[name] = local_path
    anchor_manifest[name] = {{key: value for key, value in record.items() if key != "base64"}}

manifest_path = DRIVE_PROVENANCE / "anchor_manifest.json"
manifest_path.write_text(json.dumps(anchor_manifest, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
print("Verified and persisted", len(ANCHOR_LOCAL_PATHS), "anchors")
"""
        ),
        code(
            """
# Visual anchor check. Text remains semantic HTML later; no identity copy is burned into the film.
from IPython.display import display
from PIL import ImageDraw

thumbs = []
for name, path in ANCHOR_LOCAL_PATHS.items():
    image = Image.open(path).convert("RGB").resize((480, 270), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (480, 302), "#151515")
    canvas.paste(image, (0, 0))
    ImageDraw.Draw(canvas).text((12, 279), name.replace("_", " "), fill="white")
    thumbs.append(canvas)

sheet = Image.new("RGB", (960, 604), "#151515")
for index, thumb in enumerate(thumbs):
    sheet.paste(thumb, ((index % 2) * 480, (index // 2) * 302))
display(sheet)
"""
        ),
        code(
            """
# Hardware and storage preflight. High system RAM and GPU VRAM are separate checks.
import platform
import torch

if not torch.cuda.is_available():
    raise RuntimeError("CUDA GPU not available. In Colab choose Runtime > Change runtime type > A100 GPU.")

gpu = torch.cuda.get_device_properties(0)
gpu_name = gpu.name
vram_gib = gpu.total_memory / (1024 ** 3)
ram_gib = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)

PROFILES = {
    "14b_720p": {
        "repo_id": "Skywork/SkyReels-V2-DF-14B-720P-Diffusers",
        "revision": "3d2ebd783060183743ef1d0ff884049aca4fe4f0",
        "width": 1280, "height": 720, "model_gib": 74.89, "minimum_vram_gib": 70,
        "hk_frames": 121, "reveal_frames": 97,
    },
    "1p3b_540p": {
        "repo_id": "Skywork/SkyReels-V2-DF-1.3B-540P-Diffusers",
        "revision": "958acd63685c7e632e4b194549f2a703e34bd98b",
        "width": 960, "height": 544, "model_gib": 27.01, "minimum_vram_gib": 35,
        "hk_frames": 97, "reveal_frames": 97,
    },
}

if FORCE_PROFILE is not None:
    PROFILE_NAME = FORCE_PROFILE
elif vram_gib >= PROFILES["14b_720p"]["minimum_vram_gib"]:
    PROFILE_NAME = "14b_720p"
elif vram_gib >= PROFILES["1p3b_540p"]["minimum_vram_gib"]:
    PROFILE_NAME = "1p3b_540p"
else:
    raise RuntimeError(f"Only {vram_gib:.1f} GiB GPU VRAM found; an A100 40GB or better is required.")

MODEL = PROFILES[PROFILE_NAME]
if vram_gib + 0.5 < MODEL["minimum_vram_gib"]:
    raise RuntimeError(f"Forced profile {PROFILE_NAME} is unsafe on {vram_gib:.1f} GiB VRAM")

minimum_local = MODEL["model_gib"] + 15
if free_gib("/content") < minimum_local:
    raise RuntimeError(
        f"Need at least {minimum_local:.0f} GiB free under /content; only {free_gib('/content'):.1f} GiB is free."
    )

minimum_ram = 83 if PROFILE_NAME == "14b_720p" else 35
if ram_gib < minimum_ram:
    raise RuntimeError(
        f"Need High-RAM Colab for CPU offload ({minimum_ram} GiB recommended); only {ram_gib:.1f} GiB found."
    )

if PERSIST_MODEL_CACHE_TO_DRIVE:
    cache_manifest = (
        DRIVE_CACHE / "hf-snapshots" / MODEL["repo_id"].replace("/", "--") /
        MODEL["revision"] / "model-manifest.json"
    )
    needed_drive = 12 if cache_manifest.exists() else MODEL["model_gib"] + 12
else:
    needed_drive = 12
if free_gib(DRIVE_ROOT) < needed_drive:
    raise RuntimeError(f"Need {needed_drive:.0f} GiB free on Drive; only {free_gib(DRIVE_ROOT):.1f} GiB is free.")

for binary in ("ffmpeg", "ffprobe", "rsync"):
    if shutil.which(binary) is None:
        raise RuntimeError(f"Required binary missing: {binary}")

print("GPU:", gpu_name, f"({vram_gib:.1f} GiB VRAM)")
print("System RAM:", f"{ram_gib:.1f} GiB")
print("Selected profile:", PROFILE_NAME)
print("Checkpoint:", MODEL["repo_id"], "@", MODEL["revision"])
print("Native generation:", f"{MODEL['width']}x{MODEL['height']} @ {FPS} fps")
"""
        ),
        code(
            """
# Install the pinned, FlashAttention-free Diffusers runtime.
from packaging.version import Version

if Version(torch.__version__.split("+")[0]) < Version("2.6.0"):
    raise RuntimeError(
        f"Colab supplied torch {torch.__version__}; this notebook expects torch >=2.6 with a CUDA-matched build. "
        "Start a fresh current Colab GPU runtime rather than replacing torch manually."
    )

packages = [
    "diffusers==0.39.0",
    "transformers==5.14.1",
    "accelerate==1.14.0",
    "huggingface-hub==1.24.0",
    "safetensors==0.8.0",
    "ftfy==6.3.1",
    "sentencepiece==0.2.1",
    "imageio==2.37.0",
    "imageio-ffmpeg==0.6.0",
]
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", *packages])

import accelerate, diffusers, huggingface_hub, safetensors, transformers
versions = {
    "python": platform.python_version(),
    "torch": torch.__version__,
    "diffusers": diffusers.__version__,
    "transformers": transformers.__version__,
    "accelerate": accelerate.__version__,
    "huggingface_hub": huggingface_hub.__version__,
    "safetensors": safetensors.__version__,
}
expected = {
    "diffusers": "0.39.0", "transformers": "5.14.1", "accelerate": "1.14.0",
    "huggingface_hub": "1.24.0", "safetensors": "0.8.0",
}
for package, expected_version in expected.items():
    if versions[package] != expected_version:
        raise RuntimeError(f"{package} resolved to {versions[package]}, expected {expected_version}")
print(json.dumps(versions, indent=2))
"""
        ),
        code(
            """
# Download the exact checkpoint revision, validate every Hub-reported file, then infer only from local SSD.
from huggingface_hub import model_info, snapshot_download
from safetensors import safe_open

try:
    from google.colab import userdata
    HF_TOKEN = userdata.get("HF_TOKEN")
except Exception:
    HF_TOKEN = None

repo_slug = MODEL["repo_id"].replace("/", "--")
if PERSIST_MODEL_CACHE_TO_DRIVE:
    DOWNLOAD_ROOT = DRIVE_CACHE / "hf-snapshots" / repo_slug / MODEL["revision"]
else:
    DOWNLOAD_ROOT = RUNTIME_ROOT / "hf-snapshots" / repo_slug / MODEL["revision"]
DOWNLOAD_ROOT.mkdir(parents=True, exist_ok=True)

info = model_info(
    MODEL["repo_id"], revision=MODEL["revision"], files_metadata=True, token=HF_TOKEN
)
if info.sha != MODEL["revision"]:
    raise RuntimeError(f"Hub resolved {info.sha}, expected pinned revision {MODEL['revision']}")
expected_files = {item.rfilename: item.size for item in info.siblings if item.size is not None}
expected_bytes = sum(expected_files.values())
print("Pinned snapshot size:", round(expected_bytes / (1024 ** 3), 2), "GiB")

snapshot_path = Path(snapshot_download(
    repo_id=MODEL["repo_id"],
    revision=MODEL["revision"],
    local_dir=str(DOWNLOAD_ROOT),
    token=HF_TOKEN,
    force_download=False,
    max_workers=2,
))

missing = []
wrong_size = []
for relative, expected_size in expected_files.items():
    path = snapshot_path / relative
    if not path.is_file():
        missing.append(relative)
    elif path.stat().st_size != expected_size:
        wrong_size.append((relative, path.stat().st_size, expected_size))
if missing or wrong_size:
    raise RuntimeError(f"Incomplete model snapshot. Missing={missing[:5]} wrong_size={wrong_size[:5]}")

safetensor_files = sorted(snapshot_path.rglob("*.safetensors"))
if not safetensor_files:
    raise RuntimeError("No safetensors weights found")
for path in safetensor_files:
    with safe_open(path, framework="pt", device="cpu") as handle:
        if not handle.keys():
            raise RuntimeError(f"Empty safetensors header: {path}")

model_manifest = {
    "repo_id": MODEL["repo_id"], "revision": MODEL["revision"],
    "expected_bytes": expected_bytes, "file_count": len(expected_files),
    "safetensors_count": len(safetensor_files), "validated_at_unix": time.time(),
}
(snapshot_path / "model-manifest.json").write_text(
    json.dumps(model_manifest, indent=2, sort_keys=True) + "\\n", encoding="utf-8"
)

if PERSIST_MODEL_CACHE_TO_DRIVE:
    LOCAL_MODEL_DIR = RUNTIME_MODELS / repo_slug / MODEL["revision"]
    LOCAL_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    subprocess.check_call(["rsync", "-a", "--info=progress2", str(snapshot_path) + "/", str(LOCAL_MODEL_DIR) + "/"])
else:
    LOCAL_MODEL_DIR = snapshot_path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
os.environ["HF_HOME"] = str(RUNTIME_ROOT / "hf-home")
print("Validated local inference snapshot:", LOCAL_MODEL_DIR)
"""
        ),
        code(
            """
# Lock prompts, seeds, stage topology, and a configuration fingerprint in Drive.
NEGATIVE_PROMPT = (
    "crossfade, dissolve, morph, portal, flash transition, digital zoom, flat rotating photograph, "
    "rubbery architecture, melting buildings, warped columns, duplicate towers, flicker, jitter, camera cut, "
    "people, person, face, title, caption, logo, watermark, oversaturated CGI, illustration"
)

STAGES = [
    {
        "id": "00_hong_kong_push", "mode": "i2v", "start_anchor": "hk_braemar_wide",
        "end_anchor": "hk_central_close", "num_frames": MODEL["hk_frames"], "seed": 29001,
        "drop_first_in_master": False,
        "prompt": (
            "Photorealistic live-action Hong Kong at late golden hour, one uninterrupted physically plausible camera move. "
            "Begin at the Braemar Hill wide reference. The camera glides forward, descends slightly, and performs a strong "
            "spatial dolly push toward Central. Two IFC and Bank of China Tower grow roughly 2.5 to 3 times because the camera "
            "translates through space, never because a flat image scales. Foreground residential towers move faster than the "
            "harbor and distant skyline with convincing parallax. End on the supplied close skyline composition. Stable real "
            "architecture, restrained natural motion, cinematic 24 fps, late-golden-hour haze."
        ),
    },
    {
        "id": "01_cloud_occlusion", "mode": "v2v", "source_stage": "00_hong_kong_push",
        "num_frames": 61 if PROFILE_NAME == "14b_720p" else 73,
        "seed": 29002, "drop_first_in_master": False, "occlusion": "cloud",
        "prompt": (
            "Continue the exact camera velocity, direction, and physical Hong Kong space from the conditioning frames. "
            "The camera cranes upward then drives forward into a low bank of thick volumetric harbor cloud. Buildings stay "
            "solid and preserve parallax while moving cloud progressively covers them from every edge. During the final second "
            "the lens is completely inside dense luminous cloud: 100 percent of the frame is moving cloud texture with no skyline "
            "or hard geometry visible. This is physical occlusion, never a fade, dissolve, morph, portal, or white flash."
        ),
    },
    {
        "id": "02_stanford_church_reveal", "mode": "i2v", "source_stage": "01_cloud_occlusion",
        "end_anchor": "stanford_memorial_church", "num_frames": MODEL["reveal_frames"], "seed": 29003,
        "drop_first_in_master": True,
        "prompt": (
            "One continuous impossible but natural live-action camera move. Begin exactly within the supplied full-frame moving "
            "cloud. The camera keeps advancing and gently descends as cloud streams past the lens, then the cloud thins naturally "
            "to reveal Stanford Memorial Church at late golden hour. Settle into the supplied wide, slightly off-axis church view "
            "without a cut. Real sandstone, stable arches and mosaic, believable depth and parallax, no people, no morphing."
        ),
    },
    {
        "id": "03_architectural_occlusion", "mode": "v2v", "source_stage": "02_stanford_church_reveal",
        "num_frames": 61 if PROFILE_NAME == "14b_720p" else 73,
        "seed": 29004, "drop_first_in_master": False, "occlusion": "dark",
        "prompt": (
            "Continue the exact Stanford camera motion from the conditioning frames. Glide laterally and forward from Memorial "
            "Church toward the Main Quad arcade, lowering slightly. A real massive foreground sandstone arcade column approaches "
            "with strong parallax and sweeps across the lens as the camera passes inches behind it. In the final second the frame "
            "is completely occluded by dark charcoal sandstone and architectural shadow, with no church, sky, or opening visible. "
            "Physical foreground occlusion only, never a fade to black, dissolve, morph, portal, or cut."
        ),
    },
    {
        "id": "04_main_quad_arcade_reveal", "mode": "i2v", "source_stage": "03_architectural_occlusion",
        "end_anchor": "stanford_main_quad_arcade", "num_frames": MODEL["reveal_frames"], "seed": 29005,
        "drop_first_in_master": True,
        "prompt": (
            "Continue one smooth live-action camera move from the exact supplied dark sandstone occlusion. The same nearby column "
            "slides away from the lens and naturally reveals Stanford Main Quad arcade. Glide forward slightly off axis along the "
            "sandstone colonnade, with columns crossing at different speeds and deep believable architectural perspective. Arrive "
            "at the supplied wide arcade composition in late golden hour. Stable real masonry, no people, no cut, no morphing."
        ),
    },
]

CONFIG_BODY = {
    "run_id": RUN_ID, "quality_mode": QUALITY_MODE, "fps": FPS,
    "model": {**MODEL, "profile_name": PROFILE_NAME},
    "inference_steps": INFERENCE_STEPS, "guidance_scale": GUIDANCE_SCALE,
    "addnoise_condition": ADDNOISE_CONDITION, "overlap_history": OVERLAP_HISTORY,
    "base_window_candidates": BASE_WINDOW_CANDIDATES, "negative_prompt": NEGATIVE_PROMPT,
    "stages": STAGES,
    "anchor_hashes": {name: record["sha256"] for name, record in anchor_manifest.items()},
    "runtime_versions": versions,
    "pipeline": "diffusers.SkyReelsV2DiffusionForcing ImageToVideo/VideoToVideo",
    "skyreels_reference_repo_commit": "9351d13152207cc04de780e055346b08ade0b851",
    "assembly": "hard concatenation only; no crossfades or blended transitions",
}
CONFIG_FINGERPRINT = hashlib.sha256(
    json.dumps(CONFIG_BODY, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
CONFIG = {**CONFIG_BODY, "config_fingerprint": CONFIG_FINGERPRINT}

config_path = DRIVE_RUN / "config.json"
if config_path.exists():
    existing = json.loads(config_path.read_text(encoding="utf-8"))
    if existing.get("config_fingerprint") != CONFIG_FINGERPRINT:
        raise RuntimeError(
            f"Drive run {RUN_ID!r} contains a different configuration. Change RUN_ID to preserve both candidates."
        )
else:
    temp = config_path.with_name(config_path.name + f".part-{uuid.uuid4().hex}")
    temp.write_text(json.dumps(CONFIG, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    os.replace(temp, config_path)

print("Configuration fingerprint:", CONFIG_FINGERPRINT)
for stage in STAGES:
    print(stage["id"], stage["mode"], stage["num_frames"], "frames")
"""
        ),
        code(
            """
# Durable media, validation, and resume helpers.
import fractions, gc, math
import numpy as np

def sha256_file(path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()

def atomic_write_json(destination, payload):
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + f".part-{uuid.uuid4().hex}")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\\n", encoding="utf-8")
    os.replace(temp, destination)

def atomic_publish_file(source, destination):
    source, destination = Path(source), Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    expected = sha256_file(source)
    temp = destination.with_name(destination.name + f".part-{expected[:12]}-{uuid.uuid4().hex}")
    shutil.copy2(source, temp)
    if sha256_file(temp) != expected:
        temp.unlink(missing_ok=True)
        raise RuntimeError(f"Drive read-back hash mismatch: {destination}")
    os.replace(temp, destination)
    if sha256_file(destination) != expected:
        raise RuntimeError(f"Published Drive hash mismatch: {destination}")
    return expected

def probe_video(path, count_frames=True):
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height,avg_frame_rate,nb_frames,nb_read_frames,duration",
        "-of", "json",
    ]
    if count_frames:
        command.insert(1, "-count_frames")
    command.append(str(path))
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    stream = json.loads(result.stdout)["streams"][0]
    rate = float(fractions.Fraction(stream["avg_frame_rate"]))
    raw_count = stream.get("nb_read_frames") or stream.get("nb_frames")
    if raw_count in {None, "N/A"}:
        raw_count = round(float(stream["duration"]) * rate)
    return {
        "width": int(stream["width"]), "height": int(stream["height"]),
        "fps": rate, "frames": int(raw_count), "duration": float(stream.get("duration") or 0),
    }

def stage_by_id(stage_id):
    return next(stage for stage in STAGES if stage["id"] == stage_id)

def stage_fingerprint(stage):
    payload = {"config_fingerprint": CONFIG_FINGERPRINT, "stage": stage}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def stage_drive_dir(stage):
    return DRIVE_STAGES / stage["id"]

def validate_stage(stage, verbose=False):
    directory = stage_drive_dir(stage)
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        return False, "manifest missing"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("status") != "complete":
            return False, "manifest not complete"
        if manifest.get("config_fingerprint") != CONFIG_FINGERPRINT:
            return False, "configuration fingerprint changed"
        if manifest.get("stage_fingerprint") != stage_fingerprint(stage):
            return False, "stage fingerprint changed"
        for name, record in manifest["artifacts"].items():
            path = directory / name
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                return False, f"artifact invalid: {name}"
        video = probe_video(directory / "clip.mp4")
        expected = (MODEL["width"], MODEL["height"], stage["num_frames"])
        actual = (video["width"], video["height"], video["frames"])
        if actual != expected or abs(video["fps"] - FPS) > 0.01:
            return False, f"video mismatch: actual={actual} expected={expected} fps={video['fps']}"
        history = np.load(directory / "history_frames.npz", allow_pickle=False)["frames"]
        expected_history = (OVERLAP_HISTORY, MODEL["height"], MODEL["width"], 3)
        if history.shape != expected_history or history.dtype != np.uint8:
            return False, f"history mismatch: {history.shape} {history.dtype}"
        return True, "validated"
    except Exception as error:
        if verbose:
            print(stage["id"], type(error).__name__, error)
        return False, f"validation error: {error}"

def restore_stage_artifact(stage_id, filename):
    source = DRIVE_STAGES / stage_id / filename
    if not source.is_file():
        raise FileNotFoundError(source)
    destination = RUNTIME_RUN / "restored" / stage_id / filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    manifest = json.loads((DRIVE_STAGES / stage_id / "manifest.json").read_text(encoding="utf-8"))
    if sha256_file(destination) != manifest["artifacts"][filename]["sha256"]:
        raise RuntimeError(f"Restored artifact hash mismatch: {stage_id}/{filename}")
    return destination

def frame_to_uint8(frame):
    if isinstance(frame, Image.Image):
        return np.asarray(frame.convert("RGB"), dtype=np.uint8)
    array = np.asarray(frame)
    if np.issubdtype(array.dtype, np.floating):
        if array.max(initial=0) <= 1.01:
            array = array * 255.0
        array = np.clip(array, 0, 255).astype(np.uint8)
    else:
        array = np.clip(array, 0, 255).astype(np.uint8)
    if array.ndim != 3 or array.shape[2] not in (3, 4):
        raise RuntimeError(f"Unexpected frame shape: {array.shape}")
    return array[:, :, :3]

def normalize_output_frames(output):
    frames = output.frames[0]
    if isinstance(frames, np.ndarray) and frames.ndim == 4:
        frames = list(frames)
    return [frame_to_uint8(frame) for frame in frames]

def encode_video(frames, destination):
    destination = Path(destination)
    first = frame_to_uint8(frames[0])
    height, width = first.shape[:2]
    command = [
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s:v", f"{width}x{height}", "-r", str(FPS), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(destination),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for frame in frames:
            process.stdin.write(frame_to_uint8(frame).tobytes())
    finally:
        process.stdin.close()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg stage encoding failed with return code {return_code}")

def occlusion_metrics(stage, final_frame):
    gray = np.asarray(Image.fromarray(final_frame).convert("L"), dtype=np.float32)
    gx = np.abs(np.diff(gray, axis=1)).mean()
    gy = np.abs(np.diff(gray, axis=0)).mean()
    return {
        "mean_luma": float(gray.mean()), "luma_std": float(gray.std()),
        "edge_energy": float((gx + gy) / 2), "kind": stage.get("occlusion"),
    }

def publish_stage(stage, frames, attempt):
    if len(frames) != stage["num_frames"]:
        raise RuntimeError(f"{stage['id']} returned {len(frames)} frames; expected {stage['num_frames']}")
    for frame in frames:
        if frame.shape != (MODEL["height"], MODEL["width"], 3):
            raise RuntimeError(f"{stage['id']} frame shape changed: {frame.shape}")

    local = RUNTIME_RUN / "stages" / stage["id"]
    if local.exists():
        shutil.rmtree(local)
    local.mkdir(parents=True)
    clip_path = local / "clip.mp4"
    history_path = local / "history_frames.npz"
    final_path = local / "final_frame.png"
    log_path = local / "generation.json"

    encode_video(frames, clip_path)
    Image.fromarray(frames[-1]).save(final_path, "PNG", optimize=True)
    np.savez_compressed(history_path, frames=np.stack(frames[-OVERLAP_HISTORY:]).astype(np.uint8))
    video = probe_video(clip_path)
    if (video["width"], video["height"], video["frames"]) != (
        MODEL["width"], MODEL["height"], stage["num_frames"]
    ):
        raise RuntimeError(f"Encoded stage failed validation: {video}")

    generation_log = {
        "stage": stage, "attempt": attempt, "video_probe": video,
        "occlusion_metrics": occlusion_metrics(stage, frames[-1]) if stage.get("occlusion") else None,
        "completed_at_unix": time.time(), "gpu": gpu_name, "vram_gib": vram_gib,
    }
    log_path.write_text(json.dumps(generation_log, indent=2, sort_keys=True) + "\\n", encoding="utf-8")

    drive_directory = stage_drive_dir(stage)
    artifacts = {}
    for path in (clip_path, history_path, final_path, log_path):
        digest = atomic_publish_file(path, drive_directory / path.name)
        artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}

    manifest = {
        "status": "complete", "stage_id": stage["id"],
        "config_fingerprint": CONFIG_FINGERPRINT, "stage_fingerprint": stage_fingerprint(stage),
        "model_id": MODEL["repo_id"], "model_revision": MODEL["revision"],
        "artifacts": artifacts, "published_at_unix": time.time(),
    }
    atomic_write_json(drive_directory / "manifest.json", manifest)  # written last: commit marker
    ok, reason = validate_stage(stage, verbose=True)
    if not ok:
        raise RuntimeError(f"Drive publication did not validate: {stage['id']}: {reason}")
    return generation_log
"""
        ),
        code(
            """
# Load/switch the official pipelines without duplicating 27–75 GiB of weights.
from diffusers import (
    AutoencoderKLWan,
    SkyReelsV2DiffusionForcingImageToVideoPipeline,
    SkyReelsV2DiffusionForcingVideoToVideoPipeline,
    UniPCMultistepScheduler,
)

torch.backends.cuda.matmul.allow_tf32 = True
CURRENT_PIPE = None
CURRENT_KIND = None

def dispose_pipeline():
    global CURRENT_PIPE, CURRENT_KIND
    if CURRENT_PIPE is not None:
        try:
            CURRENT_PIPE.remove_all_hooks()
        except Exception:
            pass
        CURRENT_PIPE = None
        CURRENT_KIND = None
    gc.collect()
    torch.cuda.empty_cache()

def get_pipeline(kind, fresh=False):
    global CURRENT_PIPE, CURRENT_KIND
    target_class = (
        SkyReelsV2DiffusionForcingImageToVideoPipeline
        if kind == "i2v" else SkyReelsV2DiffusionForcingVideoToVideoPipeline
    )
    if fresh:
        dispose_pipeline()

    if CURRENT_PIPE is None:
        vae = AutoencoderKLWan.from_pretrained(
            str(LOCAL_MODEL_DIR), subfolder="vae", torch_dtype=torch.float32, local_files_only=True
        )
        pipe = target_class.from_pretrained(
            str(LOCAL_MODEL_DIR), vae=vae, torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True, local_files_only=True,
        )
    elif CURRENT_KIND != kind:
        previous = CURRENT_PIPE
        try:
            previous.remove_all_hooks()
        except Exception:
            pass
        # Diffusers defaults from_pipe() to FP32; None preserves BF16 transformer/text + FP32 VAE.
        pipe = target_class.from_pipe(previous, torch_dtype=None)
        CURRENT_PIPE = None
        del previous
        gc.collect()
        torch.cuda.empty_cache()
    else:
        return CURRENT_PIPE

    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, flow_shift=5.0)
    # SkyReels' Wan VAE exposes memory controls on the VAE component, not the pipeline.
    pipe.vae.enable_tiling()
    pipe.enable_model_cpu_offload()
    CURRENT_PIPE, CURRENT_KIND = pipe, kind
    return pipe

def local_start_image(stage):
    if stage.get("start_anchor"):
        return Image.open(ANCHOR_LOCAL_PATHS[stage["start_anchor"]]).convert("RGB").resize(
            (MODEL["width"], MODEL["height"]), Image.Resampling.LANCZOS
        )
    source = restore_stage_artifact(stage["source_stage"], "final_frame.png")
    return Image.open(source).convert("RGB")

def local_end_image(stage):
    return Image.open(ANCHOR_LOCAL_PATHS[stage["end_anchor"]]).convert("RGB").resize(
        (MODEL["width"], MODEL["height"]), Image.Resampling.LANCZOS
    )

def local_history(stage):
    path = restore_stage_artifact(stage["source_stage"], "history_frames.npz")
    frames = np.load(path, allow_pickle=False)["frames"]
    if frames.shape != (OVERLAP_HISTORY, MODEL["height"], MODEL["width"], 3):
        raise RuntimeError(f"Conditioning history shape changed: {frames.shape}")
    return [Image.fromarray(frame) for frame in frames]

def generate_stage(stage):
    last_error = None
    # Diffusers 0.39 has a tensor-shape bug when first+last-frame I2V is split across
    # multiple base windows. Endpoint-conditioned stages must use one complete window.
    # The 1.3B model can also run each V2V bridge in one 97-frame window on A100 40GB.
    if stage["mode"] == "i2v":
        window_candidates = [stage["num_frames"]]
    elif PROFILE_NAME == "1p3b_540p":
        window_candidates = [97]
    else:
        window_candidates = BASE_WINDOW_CANDIDATES

    for attempt_index, base_window in enumerate(window_candidates, start=1):
        pipe = None
        output = None
        if stage["mode"] == "v2v":
            # V2V's generated portion repeats the 17 conditioning frames. Request enough 4n+1 frames
            # to remove that prefix and still publish the desired number of genuinely new frames.
            minimum_model_frames = stage["num_frames"] + OVERLAP_HISTORY
            model_num_frames = ((minimum_model_frames - 1 + 3) // 4) * 4 + 1
        else:
            model_num_frames = stage["num_frames"]
        attempt = {
            "attempt_index": attempt_index, "base_num_frames": base_window,
            "model_num_frames": model_num_frames, "published_num_frames": stage["num_frames"],
            "num_inference_steps": INFERENCE_STEPS, "guidance_scale": GUIDANCE_SCALE,
            "overlap_history": OVERLAP_HISTORY, "addnoise_condition": ADDNOISE_CONDITION,
        }
        try:
            print(f"Generating {stage['id']} with base window {base_window}...")
            pipe = get_pipeline(stage["mode"], fresh=(attempt_index > 1))
            generator = torch.Generator(device="cuda").manual_seed(stage["seed"])
            common = dict(
                prompt=stage["prompt"], negative_prompt=NEGATIVE_PROMPT,
                height=MODEL["height"], width=MODEL["width"],
                num_frames=model_num_frames, base_num_frames=base_window,
                overlap_history=OVERLAP_HISTORY,
                num_inference_steps=INFERENCE_STEPS, guidance_scale=GUIDANCE_SCALE,
                addnoise_condition=ADDNOISE_CONDITION, ar_step=0, causal_block_size=None,
                fps=FPS, generator=generator, output_type="np",
            )
            if stage["mode"] == "i2v":
                output = pipe(image=local_start_image(stage), last_image=local_end_image(stage), **common)
                frames = normalize_output_frames(output)
            else:
                history = local_history(stage)
                output = pipe(video=history, **common)
                combined = normalize_output_frames(output)
                first_new = len(history) + OVERLAP_HISTORY
                required_total = first_new + stage["num_frames"]
                if len(combined) < required_total:
                    raise RuntimeError(
                        f"V2V returned {len(combined)} total frames; expected at least "
                        f"{required_total} after removing both conditioning-frame copies"
                    )
                frames = combined[first_new:required_total]

            log = publish_stage(stage, frames, attempt)
            print("Persisted and validated:", stage["id"])
            if log.get("occlusion_metrics"):
                print("Occlusion metrics:", log["occlusion_metrics"])
            del output, frames
            gc.collect()
            torch.cuda.empty_cache()
            return
        except torch.OutOfMemoryError as error:
            last_error = error
            print(f"CUDA OOM at base window {base_window}; clearing the pipeline and retrying smaller.")
            dispose_pipeline()
            pipe = None
            output = None
            gc.collect()
            torch.cuda.empty_cache()
        except RuntimeError as error:
            if "out of memory" in str(error).lower():
                last_error = error
                print(f"OOM-like failure at base window {base_window}; retrying smaller.")
                dispose_pipeline()
                pipe = None
                output = None
                gc.collect()
                torch.cuda.empty_cache()
            else:
                raise
    raise RuntimeError(
        f"{stage['id']} exhausted automatic OOM retries. Restart with FORCE_PROFILE='1p3b_540p'. Last error: {last_error}"
    )
"""
        ),
        code(
            """
# Resume scan: only a fully validated Drive stage is reusable.
resume_state = []
for stage in STAGES:
    ok, reason = validate_stage(stage, verbose=True)
    resume_state.append((stage["id"], ok, reason))
    print(f"{stage['id']}: {'COMPLETE' if ok else 'PENDING'} — {reason}")

first_pending = next((stage_id for stage_id, ok, _ in resume_state if not ok), None)
print("First incomplete stage:", first_pending or "none")
"""
        ),
        code(
            """
# Generate every missing stage in order. Rerunning this cell skips validated work.
for stage in STAGES:
    ok, reason = validate_stage(stage)
    if ok:
        print("Skipping validated stage:", stage["id"])
        continue
    if stage.get("source_stage"):
        predecessor = stage_by_id(stage["source_stage"])
        predecessor_ok, predecessor_reason = validate_stage(predecessor)
        if not predecessor_ok:
            raise RuntimeError(
                f"Cannot generate {stage['id']} before {predecessor['id']}: {predecessor_reason}"
            )
    generate_stage(stage)

dispose_pipeline()
print("All stages are persisted and validated on Drive.")
"""
        ),
        code(
            """
# Assemble hard cuts only, crop the 540p fallback to 16:9, encode 720p/1080p masters, and publish atomically.
import io
from PIL import ImageFont

for stage in STAGES:
    ok, reason = validate_stage(stage, verbose=True)
    if not ok:
        raise RuntimeError(f"Cannot assemble; {stage['id']} is invalid: {reason}")

assembly_root = RUNTIME_RUN / "assembly"
if assembly_root.exists():
    shutil.rmtree(assembly_root)
assembly_root.mkdir(parents=True)

local_clips = []
for stage in STAGES:
    local_clips.append(restore_stage_artifact(stage["id"], "clip.mp4"))

filters = []
labels = []
for index, stage in enumerate(STAGES):
    chain = []
    if stage.get("drop_first_in_master"):
        chain.append("trim=start_frame=1")
    if MODEL["height"] == 544:
        chain.append("crop=960:540:0:2")
    chain.extend(["scale=1280:720:flags=lanczos", "setsar=1", "setpts=PTS-STARTPTS"])
    filters.append(f"[{index}:v]" + ",".join(chain) + f"[v{index}]")
    labels.append(f"[v{index}]")
filters.append(
    "".join(labels) +
    f"concat=n={len(STAGES)}:v=1:a=0,trim=end_frame=432,setpts=PTS-STARTPTS,format=yuv420p[vout]"
)
filter_complex = ";".join(filters)

master_720 = assembly_root / "intro_720p24.mp4"
command = ["ffmpeg", "-y", "-v", "error"]
for clip in local_clips:
    command.extend(["-i", str(clip)])
command.extend([
    "-filter_complex", filter_complex, "-map", "[vout]", "-an", "-r", str(FPS),
    "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", str(master_720),
])
subprocess.run(command, check=True)

raw_expected_frames = sum(
    stage["num_frames"] - int(stage.get("drop_first_in_master", False)) for stage in STAGES
)
if raw_expected_frames != 435:
    raise RuntimeError(f"Stage timing changed: expected 435 pre-trim frames, found {raw_expected_frames}")
expected_frames = 432  # exactly 18.000 seconds at 24 fps
probe_720 = probe_video(master_720)
if (probe_720["width"], probe_720["height"], probe_720["frames"]) != (1280, 720, expected_frames):
    raise RuntimeError(f"720p master validation failed: {probe_720}, expected {expected_frames} frames")

master_1080 = assembly_root / "intro_1080p24.mp4"
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(master_720), "-vf", "scale=1920:1080:flags=lanczos",
    "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", str(master_1080),
], check=True)
probe_1080 = probe_video(master_1080)
if (probe_1080["width"], probe_1080["height"], probe_1080["frames"]) != (1920, 1080, expected_frames):
    raise RuntimeError(f"1080p master validation failed: {probe_1080}")

# A reverse proof verifies that the same prerendered master can be scrubbed bidirectionally on the website.
reverse_proof = assembly_root / "intro_reverse_720p24.mp4"
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(master_720), "-vf", "reverse,setpts=PTS-STARTPTS",
    "-an", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p",
    "-movflags", "+faststart", str(reverse_proof),
], check=True)

def video_frame(path, index):
    result = subprocess.run([
        "ffmpeg", "-v", "error", "-i", str(path),
        "-vf", f"select=eq(n\\,{index})", "-frames:v", "1",
        "-f", "image2pipe", "-vcodec", "png", "-",
    ], check=True, capture_output=True)
    if not result.stdout:
        raise RuntimeError(f"Could not decode frame {index} from {path}")
    return np.asarray(Image.open(io.BytesIO(result.stdout)).convert("RGB"), dtype=np.uint8)

# Pixel-pair diagnostic uses the exact two frames adjacent in the assembled master.
seam_pairs = []
for previous_id, next_id in [
    ("01_cloud_occlusion", "02_stanford_church_reveal"),
    ("03_architectural_occlusion", "04_main_quad_arcade_reveal"),
]:
    previous_stage = stage_by_id(previous_id)
    previous_final = video_frame(
        restore_stage_artifact(previous_id, "clip.mp4"), previous_stage["num_frames"] - 1
    )
    # The endpoint-conditioned segment's first frame duplicates its supplied start; assembly drops it.
    next_first = video_frame(restore_stage_artifact(next_id, "clip.mp4"), 1)
    mae = float(np.abs(previous_final.astype(np.int16) - next_first.astype(np.int16)).mean())
    seam_pairs.append((previous_id, next_id, previous_final, next_first, mae))

diagnostic = Image.new("RGB", (1280, 760), "#151515")
draw = ImageDraw.Draw(diagnostic)
for row, (previous_id, next_id, previous_frame, next_frame, mae) in enumerate(seam_pairs):
    y = row * 380
    left = Image.fromarray(previous_frame).resize((640, 360), Image.Resampling.LANCZOS)
    right = Image.fromarray(next_frame).resize((640, 360), Image.Resampling.LANCZOS)
    diagnostic.paste(left, (0, y))
    diagnostic.paste(right, (640, y))
    draw.rectangle((0, y + 330, 1280, y + 360), fill="#151515")
    draw.text((12, y + 338), f"{previous_id} final", fill="white")
    draw.text((652, y + 338), f"{next_id} first | mean pixel delta {mae:.2f}", fill="white")
seam_path = assembly_root / "seam_diagnostic.png"
diagnostic.save(seam_path, "PNG", optimize=True)

deliverable_paths = [master_720, master_1080, reverse_proof, seam_path]
deliverable_records = {}
for path in deliverable_paths:
    digest = atomic_publish_file(path, DRIVE_FINAL / path.name)
    deliverable_records[path.name] = {"bytes": path.stat().st_size, "sha256": digest}

production_manifest = {
    "status": "complete", "run_id": RUN_ID, "config_fingerprint": CONFIG_FINGERPRINT,
    "model_id": MODEL["repo_id"], "model_revision": MODEL["revision"],
    "profile": PROFILE_NAME, "fps": FPS, "pretrim_frames": raw_expected_frames,
    "expected_frames": expected_frames,
    "duration_seconds": expected_frames / FPS,
    "assembly": "hard concatenation; no crossfade/dissolve/morph/portal/flash",
    "seams": [{"previous": a, "next": b, "mean_pixel_delta": mae} for a, b, _, _, mae in seam_pairs],
    "deliverables": deliverable_records, "stage_manifests": [str(stage_drive_dir(s) / "manifest.json") for s in STAGES],
    "hardware": {"gpu": gpu_name, "vram_gib": vram_gib, "system_ram_gib": ram_gib},
    "versions": versions, "completed_at_unix": time.time(),
}
atomic_write_json(DRIVE_FINAL / "production_manifest.json", production_manifest)

print("Published final deliverables to:", DRIVE_FINAL)
print("Duration:", round(expected_frames / FPS, 3), "seconds")
print(json.dumps({name: record["sha256"] for name, record in deliverable_records.items()}, indent=2))
display(diagnostic)
"""
        ),
        code(
            """
# Playback from the persisted Drive copies.
from IPython.display import Video, display

display(Video(str(DRIVE_FINAL / "intro_720p24.mp4"), embed=True, width=960))
print("1080p master:", DRIVE_FINAL / "intro_1080p24.mp4")
print("Production manifest:", DRIVE_FINAL / "production_manifest.json")
"""
        ),
        code(
            """
# Optional browser download. The Drive copies already persist even if this download is interrupted.
from google.colab import files
files.download(str(DRIVE_FINAL / "intro_1080p24.mp4"))
"""
        ),
    ]

    notebook = nbformat.v4.new_notebook(
        cells=cells,
        metadata={
            "accelerator": "GPU",
            "colab": {"gpuType": "A100", "provenance": []},
            "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
            "language_info": {"name": "python", "version": "3.x"},
        },
    )
    return notebook


def audit(notebook: nbformat.NotebookNode) -> None:
    nbformat.validate(notebook)
    code_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    for index, cell in enumerate(code_cells):
        ast.parse(cell.source, filename=f"notebook-cell-{index}")
        if cell.outputs or cell.execution_count is not None:
            raise AssertionError(f"Notebook cell {index} contains execution state")

    joined = "\n".join(cell.source for cell in code_cells)
    required = [
        "3d2ebd783060183743ef1d0ff884049aca4fe4f0",
        "958acd63685c7e632e4b194549f2a703e34bd98b",
        "PERSIST_MODEL_CACHE_TO_DRIVE = False",
        "SkyReelsV2DiffusionForcingImageToVideoPipeline",
        "SkyReelsV2DiffusionForcingVideoToVideoPipeline",
        "atomic_publish_file",
        "history_frames.npz",
        "intro_1080p24.mp4",
        "hard concatenation",
    ]
    for marker in required:
        if marker not in joined:
            raise AssertionError(f"Required notebook marker missing: {marker}")

    secret_patterns = [
        r"sk-[A-Za-z0-9_-]{20,}",
        r"hf_[A-Za-z0-9]{20,}",
        r"AIza[A-Za-z0-9_-]{20,}",
    ]
    for pattern in secret_patterns:
        if re.search(pattern, joined):
            raise AssertionError(f"Possible embedded credential: {pattern}")

    # Decode and independently verify every embedded asset in the final notebook source.
    anchor_cell = next(cell.source for cell in code_cells if "EMBEDDED_ANCHORS = json.loads" in cell.source)
    match = re.search(r"EMBEDDED_ANCHORS = json.loads\(r'''(.+?)'''\)", anchor_cell, re.DOTALL)
    if not match:
        raise AssertionError("Could not locate embedded anchor bundle")
    decoded = json.loads(match.group(1))
    if set(decoded) != {
        "hk_braemar_wide", "hk_central_close", "stanford_memorial_church", "stanford_main_quad_arcade"
    }:
        raise AssertionError("Embedded anchor set changed")
    for name, record in decoded.items():
        payload = base64.b64decode(record["base64"])
        if sha256_bytes(payload) != record["sha256"]:
            raise AssertionError(f"Embedded anchor audit failed: {name}")
        with Image.open(io.BytesIO(payload)) as image:
            if image.size != (1280, 720):
                raise AssertionError(f"Embedded anchor dimensions failed: {name}")


def main() -> None:
    notebook = build_notebook()
    audit(notebook)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT)
    print(f"cells={len(notebook.cells)} bytes={OUTPUT.stat().st_size}")


if __name__ == "__main__":
    main()
