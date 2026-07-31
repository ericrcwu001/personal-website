#!/usr/bin/env python3
"""Build the second-generation SkyReels cinematic portfolio notebook."""

from __future__ import annotations

import ast
import base64
import hashlib
import io
import json
import re
import time
import urllib.request
from pathlib import Path

import nbformat
from PIL import Image, ImageEnhance, ImageOps

import build_skyreels_v2_colab as base


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "skyreels_v2_cinematic_v2_colab.ipynb"

BOC_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/6/61/"
    "Bank_of_China._Hong_Kong._%2816198669451%29.jpg"
)
TRAM_URL = (
    "https://upload.wikimedia.org/wikipedia/commons/b/bf/"
    "Hong_Kong%2C_Part_3_-_HongKong8641.jpg"
)


def fetch_image(url: str) -> Image.Image:
    last_error = None
    for attempt in range(5):
        try:
            request = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "EricWuPortfolioReferenceBuilder/1.0",
                    "Referer": "https://commons.wikimedia.org/",
                },
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                payload = response.read()
            image = Image.open(io.BytesIO(payload)).convert("RGB")
            image.load()
            return image
        except Exception as error:  # pragma: no cover - network retry
            last_error = error
            time.sleep(2**attempt)
    raise RuntimeError(f"Could not fetch {url}: {last_error}")


def build_anchors_v2() -> dict[str, dict[str, str | int]]:
    wide = base.fit(
        ROOT / "output/ai-cinematic/sora-production/anchors/hk-braemar-1280x720.webp"
    )

    with Image.open(ROOT / "web/public/media/depth/hong-kong.webp") as source:
        source = source.convert("RGB")
        # A real 3.0x crop around Two IFC and Bank of China Tower.
        crop_width = round(source.width / 3.0)
        crop_height = round(crop_width * 9 / 16)
        left = min(source.width - crop_width, 1215)
        top = min(source.height - crop_height, 590)
        central_close = source.crop(
            (left, top, left + crop_width, top + crop_height)
        ).resize((1280, 720), Image.Resampling.LANCZOS)

    boc = ImageOps.fit(
        fetch_image(BOC_URL),
        (1280, 720),
        Image.Resampling.LANCZOS,
        centering=(0.5, 0.30),
    )
    tram = ImageOps.fit(
        fetch_image(TRAM_URL),
        (1280, 720),
        Image.Resampling.LANCZOS,
        centering=(0.5, 0.85),
    )

    def warm_grade(image: Image.Image) -> Image.Image:
        red, green, blue = image.convert("RGB").split()
        red = red.point(lambda value: min(255, round(value * 1.09)))
        green = green.point(lambda value: min(255, round(value * 1.02)))
        blue = blue.point(lambda value: min(255, round(value * 0.84)))
        graded = Image.merge("RGB", (red, green, blue))
        graded = Image.blend(graded, Image.new("RGB", graded.size, (226, 157, 82)), 0.08)
        return ImageEnhance.Contrast(graded).enhance(1.04)

    boc = warm_grade(boc)
    tram = warm_grade(tram)
    church = base.fit(
        ROOT / "output/imagegen/memorial-church-base.png", centering=(0.52, 0.52)
    )
    arcade = base.fit(
        ROOT / "web/public/media/stanford-arcade.webp", centering=(0.5, 0.5)
    )

    records = {
        "hk_braemar_wide": (
            wide,
            "Local Braemar Hill late-golden-hour wide anchor.",
        ),
        "hk_central_3x": (
            central_close,
            "Deterministic 3.0x crop of the local Braemar source around Two IFC and Bank of China Tower.",
        ),
        "hk_boc_facade": (
            boc,
            "Bank of China Tower low-angle exterior; CC0 by Bernard Spragg, Wikimedia Commons: "
            "https://commons.wikimedia.org/wiki/File:Bank_of_China._Hong_Kong._(16198669451).jpg",
        ),
        "hk_des_voeux_trams": (
            tram,
            "Trams 102 and 173 on Des Voeux Road Central with Two IFC; CC0 by lumoplank, Wikimedia Commons: "
            "https://commons.wikimedia.org/wiki/File:Hong_Kong,_Part_3_-_HongKong8641.jpg",
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
        payload = base.webp_bytes(image, quality=93)
        result[name] = {
            "filename": f"{name}.webp",
            "mime": "image/webp",
            "width": 1280,
            "height": 720,
            "sha256": base.sha256_bytes(payload),
            "provenance": provenance,
            "base64": base64.b64encode(payload).decode("ascii"),
        }
    return result


def replace_cell(notebook, prefix: str, source: str) -> None:
    for cell in notebook.cells:
        if cell.cell_type == "code" and cell.source.startswith(prefix):
            cell.source = source.strip() + "\n"
            cell.outputs = []
            cell.execution_count = None
            return
    raise KeyError(prefix)


TITLE = """
# SkyReels V2 — cinematic route v2 with automatic candidate rejection

This notebook replaces the rejected slow-drift render with a deliberately aggressive 18-second impossible-camera route:

**Braemar Hill → 3× Central skyline → Bank of China facade → Des Voeux Road trams → vertical sky whip → Memorial Church → sandstone column → Main Quad arcade.**

The three location-critical reveals are generated backward and reversed in playback. That makes the exact tram, Memorial Church and arcade anchors unavoidable rather than soft future suggestions. The notebook renders reproducible candidates stage-by-stage, rejects weak motion/freezes/endpoint jumps, persists every candidate to Drive, accepts the first hard-pass candidate by default, and invalidates only downstream work if a parent changes.

Run on a **Colab High-RAM A100 80 GB**. It uses the 14B/720p checkpoint and no paid video API. The route remains an editorial hidden-seam illusion rather than a survey-accurate 3D flight, but the visual actions and landmarks are explicitly constrained and audited.

The clean film contains no burned-in typography. On the website, map the four overlays by scroll progress: **Eric Wu** over the skyline push; the two-line **Interested in: AI Engineering & Research / Math, CS, Public Policy** overlay over the tower-to-tram flight; **Stanford Class of 2029** over Memorial Church; and the five social icons over the arcade glide. Equal scroll distance does not require equal film time.
"""


SETTINGS = r'''
# Production controls for the cinematic v2 route.
RUN_ID = "intro_cinematic_v2_1"
QUALITY_MODE = "final"
FORCE_PROFILE = "14b_720p"
PERSIST_MODEL_CACHE_TO_DRIVE = False
NOTEBOOK_LOGIC_VERSION = "cinematic-v2.1.1"

# All generated candidates and final media always persist to Drive. Set this True only if Drive has
# about 90 GiB free and you also want the 75 GiB model checkpoint to survive runtime disconnects.

# The loop renders the next seed only when the current candidate fails hard gates.
MAX_CANDIDATES_PER_STAGE = 3
AUTO_ACCEPT_PASSING_CANDIDATE = True

if QUALITY_MODE not in {"preview", "final"}:
    raise ValueError("QUALITY_MODE must be 'preview' or 'final'")
if FORCE_PROFILE != "14b_720p":
    raise ValueError("Cinematic v2 requires the 14B/720p profile")

FPS = 24
OVERLAP_HISTORY = 17
INFERENCE_STEPS = 50 if QUALITY_MODE == "final" else 30
GUIDANCE_SCALE = 5.0
ADDNOISE_CONDITION = 20
V2V_BASE_WINDOW = 49

print("Run:", RUN_ID, "|", QUALITY_MODE, "| candidates/stage:", MAX_CANDIDATES_PER_STAGE)
'''


ANCHOR_DISPLAY = r'''
# Display every embedded anchor before expensive generation.
from IPython.display import display
from PIL import ImageDraw
import math

thumbs = []
for name, path in ANCHOR_LOCAL_PATHS.items():
    image = Image.open(path).convert("RGB").resize((480, 270), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (480, 304), "#151515")
    canvas.paste(image, (0, 0))
    ImageDraw.Draw(canvas).text((12, 280), name.replace("_", " "), fill="white")
    thumbs.append(canvas)

rows = math.ceil(len(thumbs) / 2)
sheet = Image.new("RGB", (960, rows * 304), "#151515")
for index, thumb in enumerate(thumbs):
    sheet.paste(thumb, ((index % 2) * 480, (index // 2) * 304))
anchor_sheet_path = DRIVE_PROVENANCE / "anchor_contact_sheet.jpg"
anchor_sheet_temp = anchor_sheet_path.with_name(anchor_sheet_path.name + f".part-{uuid.uuid4().hex}")
sheet.save(anchor_sheet_temp, "JPEG", quality=92, optimize=True)
os.replace(anchor_sheet_temp, anchor_sheet_path)
display(sheet)
'''


INSTALL = r'''
# Install the pinned Diffusers runtime and motion-analysis dependency.
from packaging.version import Version

if Version(torch.__version__.split("+")[0]) < Version("2.6.0"):
    raise RuntimeError(
        f"Colab supplied torch {torch.__version__}; start a fresh current Colab GPU runtime."
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
    "opencv-python-headless==4.12.0.88",
]
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", *packages])

import accelerate, cv2, diffusers, huggingface_hub, safetensors, transformers
versions = {
    "python": platform.python_version(), "torch": torch.__version__,
    "diffusers": diffusers.__version__, "transformers": transformers.__version__,
    "accelerate": accelerate.__version__, "huggingface_hub": huggingface_hub.__version__,
    "safetensors": safetensors.__version__, "opencv": cv2.__version__,
}
expected = {
    "diffusers": "0.39.0", "transformers": "5.14.1", "accelerate": "1.14.0",
    "huggingface_hub": "1.24.0", "safetensors": "0.8.0", "opencv": "4.12.0",
}
for package, expected_version in expected.items():
    if versions[package] != expected_version:
        raise RuntimeError(f"{package} resolved to {versions[package]}, expected {expected_version}")
print(json.dumps(versions, indent=2))
'''


CONFIG = r'''
# Lock the nine-stage camera route and candidate seeds.
NEGATIVE_PROMPT = (
    "slow drift, gentle camera, static shot, flat rotating photograph, digital zoom, crossfade, dissolve, "
    "morph, portal, melting architecture, duplicated tower, bent tram, warped rails, unreadable facade, "
    "flicker, jitter, camera cut, people close-up, title, caption, logo, watermark, illustration"
)

STAGES = [
    {
        "id": "S0_skyline_push", "mode": "i2v", "display_frames": 49,
        "start_anchor": "hk_braemar_wide", "end_anchor": "hk_central_3x",
        "seeds": [41003, 41047, 41113], "motion_min": 0.45, "endpoint_mae_max": 55.0,
        "prompt": (
            "Photorealistic late-golden-hour Hong Kong. Immediate 24mm physical dolly acceleration from Braemar Hill, "
            "not a lens zoom. Hillside trees and foreground apartments explode outward with strong differential parallax. "
            "Bank of China Tower and Two IFC grow three times in screen height within two seconds. Fixed focal length, "
            "hard forward plunge, stable real buildings, no easing and no static opening hold."
        ),
    },
    {
        "id": "S1_tower_flight", "parent": "S0_skyline_push", "mode": "i2v_drop_first",
        "display_frames": 48, "end_anchor": "hk_boc_facade", "boundary_mae_max": 45.0,
        "seeds": [42011, 42061, 42119], "motion_min": 0.70, "endpoint_mae_max": 58.0,
        "prompt": (
            "Continue at maximum speed through a dense Central tower canyon. The camera banks hard while glass towers "
            "sweep in opposite directions across the frame. Fly inches past the diagonal Bank of China facade until its "
            "triangular steel geometry fills the frame. Aggressive cinematic lens, strong near-field parallax, no pause."
        ),
    },
    {
        "id": "S2_street_arrival", "parent": "S1_tower_flight", "mode": "reverse_i2v",
        "display_frames": 48, "start_anchor": "hk_des_voeux_trams", "boundary_mae_max": 45.0,
        "seeds": [43003, 43037, 43103], "motion_min": 0.48, "endpoint_mae_max": 60.0,
        "prompt": (
            "Begin exactly at tram-wire height on Des Voeux Road with trams 102 and 173. The camera rockets backward "
            "and upward through the street canyon toward the supplied Bank of China facade, with rails, footbridge and "
            "buildings showing strong perspective. Fast coherent retreat, stable trams, no morphing."
        ),
    },
    {
        "id": "S3_tram_attack", "parent": "S2_street_arrival", "mode": "v2v",
        "display_frames": 72, "seeds": [44017, 44059, 44101], "motion_min": 0.72,
        "boundary_mae_max": 45.0,
        "prompt": (
            "Continue the exact street-level velocity along Des Voeux Road. Surge between tram wires toward the red "
            "double-decker tram 173; its front destination board grows to dominate the center of frame. The camera barely "
            "clears the tram roof at speed. Rails and shopfronts streak backward with real parallax, no easing."
        ),
    },
    {
        "id": "S4_sky_whip", "parent": "S3_tram_attack", "mode": "v2v",
        "display_frames": 24, "seeds": [45007, 45043, 45109], "motion_min": 0.90,
        "boundary_mae_max": 45.0,
        "min_sky_run": 4, "max_sky_run": 8,
        "prompt": (
            "Without slowing after clearing the tram roof, whip-pitch the camera upward by eighty degrees in one second. "
            "Tram wires and skyscraper edges streak violently downward with cinematic motion blur. Only the final four to "
            "six frames contain clean blue-gold sky; no lingering cloud, no fade, no white flash."
        ),
    },
    {
        "id": "S5_church_arrival", "parent": "S4_sky_whip", "mode": "reverse_i2v",
        "display_frames": 48, "start_anchor": "stanford_memorial_church",
        "seeds": [46021, 46063, 46103], "motion_min": 0.50, "endpoint_mae_max": 58.0,
        "boundary_mae_max": 45.0, "min_start_sky_run": 4, "max_start_sky_run": 8,
        "prompt": (
            "Begin exactly on the complete Stanford Memorial Church mosaic facade at late golden hour. Immediately rocket "
            "backward while pitching sharply upward; the church drops below frame and the move ends in the supplied clean "
            "sky. Stable sandstone arches and red roof, strong physical parallax, no morphing and no pause."
        ),
    },
    {
        "id": "S6_church_to_column", "parent": "S5_church_arrival", "mode": "v2v",
        "display_frames": 60, "seeds": [47017, 47051, 47111], "motion_min": 0.52,
        "min_dark_run": 3, "max_dark_run": 8, "boundary_mae_max": 45.0,
        "prompt": (
            "Continue the descending velocity into a fast low pass across the unmistakable Memorial Church facade. Bank "
            "right toward the Main Quad arcade. A massive real sandstone column sweeps across the lens only during the final "
            "four to six frames. Preserve the church mosaic and straight arches; darkness is physical and extremely brief."
        ),
    },
    {
        "id": "S7_arcade_arrival", "parent": "S6_church_to_column", "mode": "reverse_i2v",
        "display_frames": 48, "start_anchor": "stanford_main_quad_arcade",
        "seeds": [48017, 48059, 48109], "motion_min": 0.48, "endpoint_mae_max": 60.0,
        "boundary_mae_max": 45.0, "min_start_dark_run": 3, "max_start_dark_run": 8,
        "prompt": (
            "Begin exactly inside Stanford Main Quad arcade, already gliding forward off axis. Accelerate backward into the "
            "nearest sandstone column until its dark textured surface fills the supplied ending frame. Repeating arches remain "
            "straight and stable, strong near-column parallax, no fade to black."
        ),
    },
    {
        "id": "S8_arcade_glide", "parent": "S7_arcade_arrival", "mode": "v2v",
        "display_frames": 35, "seeds": [49019, 49057, 49109], "motion_min": 0.34,
        "boundary_mae_max": 45.0,
        "prompt": (
            "Continue bursting forward through Stanford Main Quad arcade. Near columns streak laterally while distant arches "
            "remain stable. Decelerate only during the final half-second into a strong off-axis corridor composition, while "
            "retaining visible forward glide. No freeze and no geometry deformation."
        ),
    },
]

if sum(stage["display_frames"] for stage in STAGES) != 432:
    raise RuntimeError("The cinematic route must total exactly 432 frames")

# Four equal-weight scroll chapters mapped onto unequal cinematic shot durations.
# Ranges are half-open [start, end); the HK-to-Stanford sky whip intentionally carries no text.
CAPTION_TIMELINE = [
    {
        "id": "hong_kong_a", "scroll_progress": [0.0, 0.25], "chapter_video_frames": [0, 72],
        "visible_video_frames": [0, 72], "lines": ["Eric Wu"],
    },
    {
        "id": "hong_kong_b", "scroll_progress": [0.25, 0.5], "chapter_video_frames": [72, 241],
        "visible_video_frames": [72, 217],
        "lines": ["Interested in: AI Engineering & Research", "Math, CS, Public Policy"],
    },
    {
        "id": "stanford_a", "scroll_progress": [0.5, 0.75], "chapter_video_frames": [241, 349],
        "visible_video_frames": [241, 349], "lines": ["Stanford Class of 2029"],
    },
    {
        "id": "stanford_b", "scroll_progress": [0.75, 1.0], "chapter_video_frames": [349, 432],
        "visible_video_frames": [349, 432],
        "icons": ["GitHub", "LinkedIn", "X", "Instagram", "Email"],
    },
]

CONFIG_BODY = {
    "run_id": RUN_ID, "quality_mode": QUALITY_MODE, "fps": FPS,
    "notebook_logic_version": NOTEBOOK_LOGIC_VERSION,
    "model": {**MODEL, "profile_name": PROFILE_NAME},
    "inference_steps": INFERENCE_STEPS, "guidance_scale": GUIDANCE_SCALE,
    "addnoise_condition": ADDNOISE_CONDITION, "overlap_history": OVERLAP_HISTORY,
    "v2v_base_window": V2V_BASE_WINDOW, "negative_prompt": NEGATIVE_PROMPT,
    "stages": STAGES, "max_candidates_per_stage": MAX_CANDIDATES_PER_STAGE,
    "auto_accept_passing_candidate": AUTO_ACCEPT_PASSING_CANDIDATE,
    "caption_timeline": CAPTION_TIMELINE,
    "anchor_hashes": {name: record["sha256"] for name, record in anchor_manifest.items()},
    "runtime_versions": versions,
    "pipeline": "diffusers SkyReels V2 14B; reverse source-anchor landmark reveals",
    "route": "Braemar > BOC > Des Voeux trams > sky whip > Memorial Church > arcade",
}
STABLE_CONFIG_BODY = {key: value for key, value in CONFIG_BODY.items() if key != "runtime_versions"}
CONFIG_FINGERPRINT = hashlib.sha256(
    json.dumps(STABLE_CONFIG_BODY, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
CONFIG = {**CONFIG_BODY, "config_fingerprint": CONFIG_FINGERPRINT}

config_path = DRIVE_RUN / "config.json"
if config_path.exists():
    existing = json.loads(config_path.read_text(encoding="utf-8"))
    if existing.get("config_fingerprint") != CONFIG_FINGERPRINT:
        raise RuntimeError(f"Drive run {RUN_ID!r} differs. Change RUN_ID to preserve both versions.")
else:
    temp = config_path.with_name(config_path.name + f".part-{uuid.uuid4().hex}")
    temp.write_text(json.dumps(CONFIG, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, config_path)

print("Configuration:", CONFIG_FINGERPRINT)
for stage in STAGES:
    print(stage["id"], stage["mode"], stage["display_frames"], "displayed frames")
'''


UTILITIES = r'''
# Candidate persistence, validation, motion analysis, and dependency fingerprints.
import fractions, gc, math
import cv2
import numpy as np
from PIL import Image, ImageDraw

def sha256_file(path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()

def atomic_write_json(destination, payload):
    destination = Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + f".part-{uuid.uuid4().hex}")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, destination)

def atomic_publish_file(source, destination):
    source, destination = Path(source), Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    expected = sha256_file(source)
    temp = destination.with_name(destination.name + f".part-{expected[:12]}-{uuid.uuid4().hex}")
    shutil.copy2(source, temp)
    if sha256_file(temp) != expected:
        temp.unlink(missing_ok=True); raise RuntimeError(f"Drive hash mismatch: {destination}")
    os.replace(temp, destination)
    if sha256_file(destination) != expected:
        raise RuntimeError(f"Published hash mismatch: {destination}")
    return expected

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
        "ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=key_frame",
        "-of", "json", str(path),
    ], check=True, capture_output=True, text=True)
    flags = [int(frame["key_frame"]) for frame in json.loads(result.stdout)["frames"]]
    keyframes = [index for index, flag in enumerate(flags) if flag]
    if not keyframes or keyframes[0] != 0:
        return len(flags)
    return max([b - a for a, b in zip(keyframes, keyframes[1:])] + [len(flags) - keyframes[-1]])

def stage_by_id(stage_id):
    return next(stage for stage in STAGES if stage["id"] == stage_id)

def frame_to_uint8(frame):
    if isinstance(frame, Image.Image):
        return np.asarray(frame.convert("RGB"), dtype=np.uint8)
    array = np.asarray(frame)
    if np.issubdtype(array.dtype, np.floating):
        if array.max(initial=0) <= 1.01: array = array * 255.0
    array = np.clip(array, 0, 255).astype(np.uint8)
    return array[:, :, :3]

def normalize_output_frames(output):
    frames = output.frames[0]
    if isinstance(frames, np.ndarray) and frames.ndim == 4: frames = list(frames)
    return [frame_to_uint8(frame) for frame in frames]

def encode_video(frames, destination):
    first = frame_to_uint8(frames[0]); height, width = first.shape[:2]
    command = [
        "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
        "-s:v", f"{width}x{height}", "-r", str(FPS), "-i", "-", "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(destination),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    try:
        for frame in frames: process.stdin.write(frame_to_uint8(frame).tobytes())
    finally:
        process.stdin.close()
    if process.wait() != 0: raise RuntimeError("ffmpeg candidate encoding failed")

def write_contact_sheet(frames, destination, stage_id, seed):
    sample_count = min(8, len(frames))
    indices = np.linspace(0, len(frames) - 1, sample_count, dtype=int)
    tile_width, tile_height, label_height = 320, 180, 26
    columns = 4
    rows = math.ceil(sample_count / columns)
    sheet = Image.new("RGB", (columns * tile_width, rows * (tile_height + label_height)), "#111111")
    draw = ImageDraw.Draw(sheet)
    for position, frame_index in enumerate(indices):
        tile = Image.fromarray(frame_to_uint8(frames[frame_index])).resize(
            (tile_width, tile_height), Image.Resampling.LANCZOS
        )
        x = (position % columns) * tile_width
        y = (position // columns) * (tile_height + label_height)
        sheet.paste(tile, (x, y))
        draw.text((x + 8, y + tile_height + 5), f"frame {frame_index:03d}", fill="white")
    draw.rectangle((0, 0, min(390, sheet.width), 28), fill=(0, 0, 0))
    draw.text((8, 7), f"{stage_id} | seed {seed}", fill="white")
    sheet.save(destination, "JPEG", quality=90, optimize=True)

def accepted_pointer(stage_id): return DRIVE_STAGES / stage_id / "accepted.json"
def candidate_dir(stage_id, seed): return DRIVE_STAGES / stage_id / "candidates" / str(seed)

def current_parent_hash(stage):
    if not stage.get("parent"): return "ROOT"
    pointer = accepted_pointer(stage["parent"])
    if not pointer.is_file(): raise RuntimeError(f"Parent not accepted: {stage['parent']}")
    return json.loads(pointer.read_text(encoding="utf-8"))["candidate_manifest_sha256"]

def candidate_fingerprint(stage, seed, parent_hash):
    payload = {"config": CONFIG_FINGERPRINT, "stage": stage, "seed": seed, "parent": parent_hash}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def analyze_motion(frames, stage):
    small = [cv2.cvtColor(cv2.resize(frame, (320, 180)), cv2.COLOR_RGB2GRAY) for frame in frames]
    flow_values, diffs = [], []
    for previous, current in zip(small, small[1:]):
        flow = cv2.calcOpticalFlowFarneback(previous, current, None, .5, 3, 21, 3, 5, 1.2, 0)
        flow_values.append(float(np.linalg.norm(flow, axis=2).mean()))
        diffs.append(float(np.abs(current.astype(np.float32) - previous.astype(np.float32)).mean()))
    freeze_run = maximum_freeze = 0
    for value in diffs:
        freeze_run = freeze_run + 1 if value < 0.55 else 0
        maximum_freeze = max(maximum_freeze, freeze_run)
    gray = [cv2.cvtColor(frame, cv2.COLOR_RGB2GRAY) for frame in frames]
    dark_run = 0
    for image in reversed(gray):
        if float(image.mean()) < 70: dark_run += 1
        else: break
    start_dark_run = 0
    for image in gray:
        if float(image.mean()) < 70: start_dark_run += 1
        else: break
    sky_run = 0
    for image in reversed(gray):
        edge = (np.abs(np.diff(image.astype(np.float32), axis=0)).mean() + np.abs(np.diff(image.astype(np.float32), axis=1)).mean()) / 2
        if edge < 5.0 and float(image.mean()) > 90: sky_run += 1
        else: break
    start_sky_run = 0
    for image in gray:
        edge = (np.abs(np.diff(image.astype(np.float32), axis=0)).mean() + np.abs(np.diff(image.astype(np.float32), axis=1)).mean()) / 2
        if edge < 5.0 and float(image.mean()) > 90: start_sky_run += 1
        else: break
    metrics = {
        "median_flow": float(np.median(flow_values)), "mean_flow": float(np.mean(flow_values)),
        "maximum_freeze_run": int(maximum_freeze),
        "dark_start_run": int(start_dark_run), "dark_end_run": int(dark_run),
        "sky_start_run": int(start_sky_run), "sky_end_run": int(sky_run),
        "start_adjacent_mae": float(np.abs(frames[1].astype(np.float32) - frames[0].astype(np.float32)).mean()),
        "end_adjacent_mae": float(np.abs(frames[-1].astype(np.float32) - frames[-2].astype(np.float32)).mean()),
    }
    failures = []
    if metrics["median_flow"] < stage["motion_min"]: failures.append("motion_too_weak")
    if maximum_freeze > 6: failures.append("freeze_run")
    if stage.get("max_sky_run") is not None and sky_run > stage["max_sky_run"]: failures.append("sky_too_long")
    if stage.get("max_dark_run") is not None and dark_run > stage["max_dark_run"]: failures.append("dark_too_long")
    if stage.get("max_start_sky_run") is not None and start_sky_run > stage["max_start_sky_run"]: failures.append("opening_sky_too_long")
    if stage.get("max_start_dark_run") is not None and start_dark_run > stage["max_start_dark_run"]: failures.append("opening_dark_too_long")
    if stage.get("min_sky_run") is not None and sky_run < stage["min_sky_run"]: failures.append("sky_occlusion_missing")
    if stage.get("min_dark_run") is not None and dark_run < stage["min_dark_run"]: failures.append("column_occlusion_missing")
    if stage.get("min_start_sky_run") is not None and start_sky_run < stage["min_start_sky_run"]: failures.append("opening_sky_occlusion_missing")
    if stage.get("min_start_dark_run") is not None and start_dark_run < stage["min_start_dark_run"]: failures.append("opening_column_occlusion_missing")
    limit = stage.get("endpoint_mae_max")
    if limit is not None and max(metrics["start_adjacent_mae"], metrics["end_adjacent_mae"]) > limit:
        failures.append("endpoint_jump")
    metrics["failures"] = failures
    metrics["hard_pass"] = not failures
    metrics["score"] = metrics["median_flow"] - maximum_freeze * .08 - len(failures) * 2
    return metrics

def validate_candidate(stage, seed):
    directory = candidate_dir(stage["id"], seed); manifest_path = directory / "manifest.json"
    if not manifest_path.is_file(): return False, "manifest missing", None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        parent_hash = current_parent_hash(stage)
        if manifest["candidate_fingerprint"] != candidate_fingerprint(stage, seed, parent_hash):
            return False, "fingerprint changed", None
        for name, record in manifest["artifacts"].items():
            path = directory / name
            if not path.is_file() or path.stat().st_size != record["bytes"] or sha256_file(path) != record["sha256"]:
                return False, f"artifact invalid: {name}", None
        probe = probe_video(directory / "clip.mp4")
        if (probe["width"], probe["height"], probe["frames"]) != (MODEL["width"], MODEL["height"], stage["display_frames"]):
            return False, f"video mismatch: {probe}", None
        if abs(probe["fps"] - FPS) > 0.01:
            return False, f"video fps mismatch: {probe}", None
        return True, "validated", manifest
    except Exception as error:
        return False, str(error), None

def accepted_candidate(stage):
    if stage.get("parent") and accepted_candidate(stage_by_id(stage["parent"])) is None:
        return None
    pointer_path = accepted_pointer(stage["id"])
    if not pointer_path.is_file(): return None
    pointer = json.loads(pointer_path.read_text(encoding="utf-8")); seed = pointer["seed"]
    ok, _, manifest = validate_candidate(stage, seed)
    if not ok or sha256_file(candidate_dir(stage["id"], seed) / "manifest.json") != pointer["candidate_manifest_sha256"]:
        return None
    return seed, manifest

def publish_candidate(stage, seed, frames, generation):
    if len(frames) != stage["display_frames"]: raise RuntimeError(f"Frame mismatch for {stage['id']}")
    local = RUNTIME_RUN / "candidates" / stage["id"] / str(seed)
    if local.exists(): shutil.rmtree(local)
    local.mkdir(parents=True)
    clip = local / "clip.mp4"; history = local / "history_frames.npz"; final = local / "final_frame.png"
    contact_sheet = local / "contact_sheet.jpg"
    encode_video(frames, clip); np.savez_compressed(history, frames=np.stack(frames[-OVERLAP_HISTORY:]).astype(np.uint8))
    Image.fromarray(frames[-1]).save(final, "PNG", optimize=True)
    write_contact_sheet(frames, contact_sheet, stage["id"], seed)
    metrics = analyze_motion(frames, stage)
    if stage.get("parent"):
        parent_final = frame_to_uint8(Image.open(restore_accepted(stage["parent"], "final_frame.png")).convert("RGB"))
        boundary_mae = float(np.abs(parent_final.astype(np.float32) - frame_to_uint8(frames[0]).astype(np.float32)).mean())
        metrics["parent_boundary_mae"] = boundary_mae
        if boundary_mae > stage.get("boundary_mae_max", 45.0):
            metrics["failures"].append("parent_boundary_jump")
            metrics["hard_pass"] = False
            metrics["score"] -= 2
    else:
        metrics["parent_boundary_mae"] = None
    metrics_path = local / "metrics.json"; metrics_path.write_text(json.dumps(metrics, indent=2) + "\n")
    generation_path = local / "generation.json"; generation_path.write_text(json.dumps(generation, indent=2) + "\n")
    drive = candidate_dir(stage["id"], seed); artifacts = {}
    for path in (clip, history, final, contact_sheet, metrics_path, generation_path):
        digest = atomic_publish_file(path, drive / path.name); artifacts[path.name] = {"bytes": path.stat().st_size, "sha256": digest}
    parent_hash = current_parent_hash(stage)
    manifest = {
        "status": "complete", "stage_id": stage["id"], "seed": seed, "parent_hash": parent_hash,
        "candidate_fingerprint": candidate_fingerprint(stage, seed, parent_hash), "metrics": metrics,
        "artifacts": artifacts, "model_id": MODEL["repo_id"], "model_revision": MODEL["revision"],
    }
    atomic_write_json(drive / "manifest.json", manifest)
    return manifest

def accept_candidate(stage, seed, manifest):
    manifest_path = candidate_dir(stage["id"], seed) / "manifest.json"
    pointer = {
        "stage_id": stage["id"], "seed": seed, "metrics": manifest["metrics"],
        "candidate_manifest_sha256": sha256_file(manifest_path), "accepted_at_unix": time.time(),
    }
    atomic_write_json(accepted_pointer(stage["id"]), pointer)

def restore_accepted(stage_id, filename):
    stage = stage_by_id(stage_id); accepted = accepted_candidate(stage)
    if accepted is None: raise RuntimeError(f"Stage not accepted: {stage_id}")
    seed, manifest = accepted; source = candidate_dir(stage_id, seed) / filename
    destination = RUNTIME_RUN / "restored" / stage_id / filename; destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    if sha256_file(destination) != manifest["artifacts"][filename]["sha256"]: raise RuntimeError("Restore hash mismatch")
    return destination
'''


PIPELINE = r'''
# Official SkyReels pipelines plus forward/reverse candidate generation.
from diffusers import (
    AutoencoderKLWan, SkyReelsV2DiffusionForcingImageToVideoPipeline,
    SkyReelsV2DiffusionForcingVideoToVideoPipeline, UniPCMultistepScheduler,
)

torch.backends.cuda.matmul.allow_tf32 = True
CURRENT_PIPE = None; CURRENT_KIND = None

def dispose_pipeline():
    global CURRENT_PIPE, CURRENT_KIND
    if CURRENT_PIPE is not None:
        try: CURRENT_PIPE.remove_all_hooks()
        except Exception: pass
    CURRENT_PIPE = None; CURRENT_KIND = None; gc.collect(); torch.cuda.empty_cache()

def assert_pipeline_dtypes(pipe):
    if pipe.transformer.dtype != torch.bfloat16:
        raise RuntimeError(f"Transformer dtype changed to {pipe.transformer.dtype}; expected bfloat16")
    if pipe.vae.dtype != torch.float32:
        raise RuntimeError(f"VAE dtype changed to {pipe.vae.dtype}; expected float32")

def get_pipeline(kind):
    global CURRENT_PIPE, CURRENT_KIND
    target = SkyReelsV2DiffusionForcingVideoToVideoPipeline if kind == "v2v" else SkyReelsV2DiffusionForcingImageToVideoPipeline
    if CURRENT_PIPE is None:
        vae = AutoencoderKLWan.from_pretrained(str(LOCAL_MODEL_DIR), subfolder="vae", torch_dtype=torch.float32, local_files_only=True)
        pipe = target.from_pretrained(str(LOCAL_MODEL_DIR), vae=vae, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True, local_files_only=True)
    elif CURRENT_KIND != kind:
        previous = CURRENT_PIPE
        try: previous.remove_all_hooks()
        except Exception: pass
        pipe = target.from_pipe(previous, torch_dtype=None)
        CURRENT_PIPE = None; del previous; gc.collect(); torch.cuda.empty_cache()
    else:
        return CURRENT_PIPE
    assert_pipeline_dtypes(pipe)
    pipe.scheduler = UniPCMultistepScheduler.from_config(pipe.scheduler.config, flow_shift=5.0)
    pipe.vae.enable_tiling(); pipe.enable_model_cpu_offload(); CURRENT_PIPE, CURRENT_KIND = pipe, kind
    return pipe

def anchor_image(name):
    return Image.open(ANCHOR_LOCAL_PATHS[name]).convert("RGB").resize((MODEL["width"], MODEL["height"]), Image.Resampling.LANCZOS)

def restored_final(stage_id): return Image.open(restore_accepted(stage_id, "final_frame.png")).convert("RGB")

def v2v_request_frames(display_frames, overlap_history=OVERLAP_HISTORY, temporal_multiple=4):
    minimum = display_frames + overlap_history
    return ((minimum - 1 + temporal_multiple - 1) // temporal_multiple) * temporal_multiple + 1

def extract_new_v2v_frames(combined, history_length, display_frames, overlap_history=OVERLAP_HISTORY):
    first_new = history_length + overlap_history
    stop = first_new + display_frames
    if len(combined) < stop:
        raise RuntimeError(f"V2V returned {len(combined)} frames; need at least {stop}")
    return list(combined[first_new:stop]), first_new

def finalize_i2v_frames(forward, mode, first, last):
    forward = list(forward)
    forward[0] = np.asarray(first, dtype=np.uint8)
    forward[-1] = np.asarray(last, dtype=np.uint8)
    if mode == "i2v": return forward
    if mode == "i2v_drop_first": return forward[1:]
    if mode == "reverse_i2v": return list(reversed(forward))[1:]
    raise ValueError(mode)

def generate_candidate(stage, seed):
    mode = stage["mode"]; pipe_kind = "v2v" if mode == "v2v" else "i2v"; pipe = get_pipeline(pipe_kind)
    generator = torch.Generator(device="cuda").manual_seed(seed)
    common = dict(
        prompt=stage["prompt"], negative_prompt=NEGATIVE_PROMPT, height=MODEL["height"], width=MODEL["width"],
        num_inference_steps=INFERENCE_STEPS, guidance_scale=GUIDANCE_SCALE, fps=FPS,
        generator=generator, output_type="np", ar_step=0, causal_block_size=None,
    )
    generation = {"seed": seed, "stage": stage, "started_at_unix": time.time()}
    if mode == "v2v":
        history_array = np.load(restore_accepted(stage["parent"], "history_frames.npz"), allow_pickle=False)["frames"]
        history = [Image.fromarray(frame) for frame in history_array]
        desired = stage["display_frames"]
        model_frames = v2v_request_frames(desired)
        output = pipe(video=history, num_frames=model_frames, base_num_frames=V2V_BASE_WINDOW,
                      overlap_history=OVERLAP_HISTORY, addnoise_condition=ADDNOISE_CONDITION, **common)
        combined = normalize_output_frames(output)
        frames, first_new = extract_new_v2v_frames(combined, len(history), desired)
        generation.update({"model_frames": model_frames, "slice_start": first_new})
    else:
        if mode == "i2v":
            first = anchor_image(stage["start_anchor"]); last = anchor_image(stage["end_anchor"]); model_frames = stage["display_frames"]
        elif mode == "i2v_drop_first":
            first = restored_final(stage["parent"]); last = anchor_image(stage["end_anchor"]); model_frames = stage["display_frames"] + 1
        elif mode == "reverse_i2v":
            first = anchor_image(stage["start_anchor"]); last = restored_final(stage["parent"]); model_frames = stage["display_frames"] + 1
        else:
            raise ValueError(mode)
        if model_frames > 49:
            raise RuntimeError(f"Unsafe one-window I2V request: {model_frames} frames; topology must keep this at 49 or less")
        output = pipe(image=first, last_image=last, num_frames=model_frames, base_num_frames=model_frames,
                      overlap_history=None, addnoise_condition=0, **common)
        forward = normalize_output_frames(output)
        if len(forward) != model_frames: raise RuntimeError(f"I2V returned {len(forward)} frames, expected {model_frames}")
        frames = finalize_i2v_frames(forward, mode, first, last)
        generation.update({"model_frames": model_frames, "forced_exact_endpoints": True, "reversed": mode == "reverse_i2v"})
    generation["completed_at_unix"] = time.time()
    return publish_candidate(stage, seed, frames, generation)
'''


CONTRACT = r'''
# Fast synthetic contract tests: no model load and no generation.
assert [v2v_request_frames(n) for n in (72, 24, 60, 35)] == [89, 41, 77, 53]
assert all(v2v_request_frames(n) % 4 == 1 for n in (72, 24, 60, 35))

synthetic_combined = list(range(17 + 89))
synthetic_new, synthetic_start = extract_new_v2v_frames(synthetic_combined, 17, 72)
assert synthetic_start == 34 and synthetic_new == list(range(34, 106))

first = np.full((2, 2, 3), 11, dtype=np.uint8)
last = np.full((2, 2, 3), 99, dtype=np.uint8)
raw = [np.full_like(first, value) for value in range(49)]
reversed_display = finalize_i2v_frames(raw, "reverse_i2v", first, last)
assert len(reversed_display) == 48
assert np.array_equal(reversed_display[-1], first)
assert not np.array_equal(reversed_display[0], last)
forward_display = finalize_i2v_frames(raw, "i2v_drop_first", first, last)
assert len(forward_display) == 48 and np.array_equal(forward_display[-1], last)

assert sum(stage["display_frames"] for stage in STAGES) == 432
assert max(stage["display_frames"] + (1 if stage["mode"] in {"i2v_drop_first", "reverse_i2v"} else 0)
           for stage in STAGES if stage["mode"] != "v2v") <= 49
print("Synthetic frame, endpoint, and 18-second timeline contracts passed.")
'''


RESUME = r'''
# Show accepted stages and cached candidates.
for stage in STAGES:
    accepted = accepted_candidate(stage)
    candidate_states = []
    for seed in stage["seeds"][:MAX_CANDIDATES_PER_STAGE]:
        ok, reason, manifest = validate_candidate(stage, seed) if (not stage.get("parent") or accepted_candidate(stage_by_id(stage["parent"]))) else (False, "parent pending", None)
        candidate_states.append((seed, ok, reason, manifest["metrics"] if manifest else None))
    print(stage["id"], "ACCEPTED" if accepted else "PENDING", candidate_states)
'''


GENERATE = r'''
# Dependency-locked candidate loop. Each accepted stage is immediately durable on Drive.
for stage in STAGES:
    already = accepted_candidate(stage)
    if already:
        print("Skipping accepted stage:", stage["id"], "seed", already[0]); continue
    if stage.get("parent") and accepted_candidate(stage_by_id(stage["parent"])) is None:
        raise RuntimeError(f"Parent {stage['parent']} must be accepted before {stage['id']}")

    passing = []
    for seed in stage["seeds"][:MAX_CANDIDATES_PER_STAGE]:
        ok, reason, manifest = validate_candidate(stage, seed)
        if not ok:
            print("Generating", stage["id"], "candidate", seed)
            try:
                manifest = generate_candidate(stage, seed)
            except Exception:
                dispose_pipeline()
                raise
        metrics = manifest["metrics"]
        print(stage["id"], seed, metrics)
        if metrics["hard_pass"]:
            passing.append((metrics["score"], seed, manifest))
            if AUTO_ACCEPT_PASSING_CANDIDATE:
                break

    if not passing:
        for seed in stage["seeds"][:MAX_CANDIDATES_PER_STAGE]:
            sheet = candidate_dir(stage["id"], seed) / "contact_sheet.jpg"
            if sheet.is_file():
                print("Rejected candidate review:", sheet)
                display(Image.open(sheet))
        raise RuntimeError(
            f"No candidate passed automatic gates for {stage['id']}. Candidate clips and sheets are under "
            f"{DRIVE_STAGES / stage['id'] / 'candidates'}."
        )
    _, best_seed, best_manifest = max(passing, key=lambda item: item[0])
    accept_candidate(stage, best_seed, best_manifest)
    print("Accepted", stage["id"], "seed", best_seed, best_manifest["metrics"])
    display(Image.open(candidate_dir(stage["id"], best_seed) / "contact_sheet.jpg"))

dispose_pipeline()
print("All nine stages accepted and persisted.")
'''


ASSEMBLY = r'''
# Assemble the accepted 432 frames with hard cuts only and publish the QA package.
import io

for stage in STAGES:
    if accepted_candidate(stage) is None: raise RuntimeError(f"Not accepted: {stage['id']}")

assembly = RUNTIME_RUN / "assembly"
if assembly.exists(): shutil.rmtree(assembly)
assembly.mkdir(parents=True)
clips = [restore_accepted(stage["id"], "clip.mp4") for stage in STAGES]
filters, labels = [], []
for index in range(len(clips)):
    filters.append(f"[{index}:v]scale=1280:720:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[v{index}]")
    labels.append(f"[v{index}]")
filters.append("".join(labels) + f"concat=n={len(clips)}:v=1:a=0,format=yuv420p[vout]")
master720 = assembly / "intro_cinematic_v2_720p24.mp4"
command = ["ffmpeg", "-y", "-v", "error"]
for clip in clips: command += ["-i", str(clip)]
command += ["-filter_complex", ";".join(filters), "-map", "[vout]", "-an", "-r", str(FPS),
            "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(master720)]
subprocess.run(command, check=True)
probe720 = probe_video(master720)
if (probe720["width"], probe720["height"], probe720["frames"]) != (1280, 720, 432) or abs(probe720["fps"] - 24) > .01 or abs(probe720["duration"] - 18.0) > .05:
    raise RuntimeError(f"Master failed: {probe720}")

master1080 = assembly / "intro_cinematic_v2_1080p24.mp4"
subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(master720), "-vf", "scale=1920:1080:flags=lanczos",
                "-an", "-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(master1080)], check=True)
probe1080 = probe_video(master1080)
if (probe1080["width"], probe1080["height"], probe1080["frames"]) != (1920, 1080, 432) or abs(probe1080["fps"] - 24) > .01 or abs(probe1080["duration"] - 18.0) > .05:
    raise RuntimeError(f"1080p master failed: {probe1080}")

scrub1080 = assembly / "intro_cinematic_v2_scrub_1080p24.mp4"
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(master1080), "-an",
    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p",
    "-g", "6", "-keyint_min", "6", "-sc_threshold", "0", "-bf", "0", "-tune", "fastdecode",
    "-movflags", "+faststart", str(scrub1080),
], check=True)
probe_scrub1080 = probe_video(scrub1080)
scrub_keyframe_gap = maximum_keyframe_gap(scrub1080)
if (probe_scrub1080["width"], probe_scrub1080["height"], probe_scrub1080["frames"]) != (1920, 1080, 432) or abs(probe_scrub1080["fps"] - 24) > .01 or abs(probe_scrub1080["duration"] - 18.0) > .05 or scrub_keyframe_gap > 6:
    raise RuntimeError(f"Scrub master failed: {probe_scrub1080}")

bidirectional = assembly / "intro_cinematic_v2_bidirectional-proof.mp4"
subprocess.run([
    "ffmpeg", "-y", "-v", "error", "-i", str(master720), "-filter_complex",
    "[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[fwd];[r]reverse,setpts=PTS-STARTPTS[rev];"
    "[fwd][rev]concat=n=2:v=1:a=0,format=yuv420p[vout]",
    "-map", "[vout]", "-an", "-r", str(FPS), "-c:v", "libx264", "-preset", "medium", "-crf", "17",
    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(bidirectional),
], check=True)
probe_bidirectional = probe_video(bidirectional)
if (probe_bidirectional["width"], probe_bidirectional["height"], probe_bidirectional["frames"]) != (1280, 720, 864) or abs(probe_bidirectional["fps"] - 24) > .01 or abs(probe_bidirectional["duration"] - 36.0) > .05:
    raise RuntimeError(f"Bidirectional proof failed: {probe_bidirectional}")

def decode_frame(path, index):
    result = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", f"select=eq(n\\,{index})",
                             "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"],
                            check=True, capture_output=True)
    return np.asarray(Image.open(io.BytesIO(result.stdout)).convert("RGB"))

seam_rows = []
for previous, following in zip(STAGES, STAGES[1:]):
    left_path = restore_accepted(previous["id"], "clip.mp4"); right_path = restore_accepted(following["id"], "clip.mp4")
    left = decode_frame(left_path, previous["display_frames"] - 1); right = decode_frame(right_path, 0)
    seam_rows.append((previous["id"], following["id"], left, right, float(np.abs(left.astype(float)-right.astype(float)).mean())))
diagnostic = Image.new("RGB", (1280, len(seam_rows) * 210), "#111"); draw = ImageDraw.Draw(diagnostic)
for row, (a, b, left, right, mae) in enumerate(seam_rows):
    y=row*210; diagnostic.paste(Image.fromarray(left).resize((640,180)),(0,y)); diagnostic.paste(Image.fromarray(right).resize((640,180)),(640,y))
    draw.text((8,y+184),f"{a} final",fill="white"); draw.text((648,y+184),f"{b} first | MAE {mae:.2f}",fill="white")
diagnostic_path=assembly/"seam_diagnostic.png"; diagnostic.save(diagnostic_path)

timeline = Image.new("RGB", (960, 3 * 206), "#111111"); timeline_draw = ImageDraw.Draw(timeline)
for index, stage in enumerate(STAGES):
    frame = decode_frame(restore_accepted(stage["id"], "clip.mp4"), stage["display_frames"] // 2)
    x = (index % 3) * 320; y = (index // 3) * 206
    timeline.paste(Image.fromarray(frame).resize((320, 180), Image.Resampling.LANCZOS), (x, y))
    timeline_draw.text((x + 8, y + 185), stage["id"], fill="white")
timeline_path = assembly / "accepted_timeline_contact_sheet.jpg"; timeline.save(timeline_path, "JPEG", quality=91, optimize=True)

seam_report = [
    {"previous": a, "following": b, "mae": mae, "limit": stage_by_id(b).get("boundary_mae_max", 45.0)}
    for a, b, _, _, mae in seam_rows
]
seam_failures = [row for row in seam_report if row["mae"] > row["limit"]]
qa_report = {
    "status": "failed" if seam_failures else "passed",
    "master_720p": probe720, "master_1080p": probe1080,
    "scrub_master_1080p": {**probe_scrub1080, "maximum_keyframe_gap": scrub_keyframe_gap},
    "bidirectional_proof": probe_bidirectional, "seams": seam_report,
}
qa_path = assembly / "qa-report.json"; qa_path.write_text(json.dumps(qa_report, indent=2) + "\n")
if seam_failures:
    for failed_path in (diagnostic_path, timeline_path, qa_path):
        atomic_publish_file(failed_path, DRIVE_FINAL / failed_path.name)
    raise RuntimeError(f"Encoded seam gate failed: {seam_failures}. Diagnostics were saved to {DRIVE_FINAL}")

deliverables={}
for path in (master720,master1080,scrub1080,bidirectional,diagnostic_path,timeline_path,qa_path):
    digest=atomic_publish_file(path,DRIVE_FINAL/path.name);deliverables[path.name]={"bytes":path.stat().st_size,"sha256":digest}
manifest={
    "status":"complete","run_id":RUN_ID,"frames":432,"fps":24,"duration_seconds":18.0,
    "route":CONFIG_BODY["route"],"config_fingerprint":CONFIG_FINGERPRINT,"deliverables":deliverables,
    "accepted":[json.loads(accepted_pointer(s["id"]).read_text()) for s in STAGES],
    "assembly":"hard concatenation; no crossfade/dissolve/morph",
    "caption_timeline": CAPTION_TIMELINE,
    "website_recommended_video": "intro_cinematic_v2_scrub_1080p24.mp4",
}
atomic_write_json(DRIVE_FINAL/"production_manifest.json",manifest)
print("Published:",DRIVE_FINAL);display(diagnostic)
'''


PLAYBACK = r'''
# Playback the accepted persistent master.
from IPython.display import Video, display
display(Video(str(DRIVE_FINAL / "intro_cinematic_v2_720p24.mp4"), embed=True, width=960))
print("1080p:", DRIVE_FINAL / "intro_cinematic_v2_1080p24.mp4")
print("Website scrub master:", DRIVE_FINAL / "intro_cinematic_v2_scrub_1080p24.mp4")
print("Forward/reverse QA:", DRIVE_FINAL / "intro_cinematic_v2_bidirectional-proof.mp4")
print("Manifest:", DRIVE_FINAL / "production_manifest.json")
print("Reconnect-safe: run the notebook from the top; validated accepted stages will be skipped.")
if not PERSIST_MODEL_CACHE_TO_DRIVE:
    print("Generated media is persistent. Model weights are not cached to Drive, so a fresh runtime redownloads them.")
'''


DOWNLOAD = r'''
# Optional browser download of the complete QA handoff; the Drive directory is already durable.
from google.colab import files
bundle_base = Path("/content") / f"{RUN_ID}_qa_handoff"
bundle_path = Path(shutil.make_archive(str(bundle_base), "zip", root_dir=DRIVE_FINAL))
files.download(str(bundle_path))
'''


def build_notebook():
    original = base.build_anchors
    try:
        base.build_anchors = build_anchors_v2
        notebook = base.build_notebook()
    finally:
        base.build_anchors = original

    for cell in notebook.cells:
        if cell.cell_type == "code" and cell.source.startswith("# Restore the four bundled visual anchors"):
            cell.source = cell.source.replace(
                "# Restore the four bundled visual anchors",
                "# Restore the six bundled visual anchors",
                1,
            )

    notebook.cells[0].source = TITLE.strip() + "\n"
    replace_cell(notebook, "# User controls.", SETTINGS)
    replace_cell(notebook, "# Visual anchor check.", ANCHOR_DISPLAY)
    replace_cell(notebook, "# Install the pinned", INSTALL)
    replace_cell(notebook, "# Lock prompts", CONFIG)
    replace_cell(notebook, "# Durable media", UTILITIES)
    replace_cell(notebook, "# Load/switch", PIPELINE)
    pipeline_index = next(
        index for index, cell in enumerate(notebook.cells)
        if cell.cell_type == "code" and cell.source.startswith("# Official SkyReels pipelines")
    )
    notebook.cells.insert(pipeline_index + 1, nbformat.v4.new_code_cell(CONTRACT.strip() + "\n"))
    replace_cell(notebook, "# Resume scan", RESUME)
    replace_cell(notebook, "# Generate every missing", GENERATE)
    replace_cell(notebook, "# Assemble hard cuts", ASSEMBLY)
    replace_cell(notebook, "# Playback", PLAYBACK)
    replace_cell(notebook, "# Optional browser download", DOWNLOAD)
    return notebook


def audit(notebook):
    nbformat.validate(notebook)
    joined = "\n".join(cell.source for cell in notebook.cells)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=f"v2-cell-{index}")
            assert not cell.outputs and cell.execution_count is None
    required = [
        "hk_des_voeux_trams", "S3_tram_attack", "reverse_i2v", "MAX_CANDIDATES_PER_STAGE",
        "median_flow", "candidate_manifest_sha256", "contact_sheet.jpg", "intro_cinematic_v2_1080p24.mp4",
        "accepted_timeline_contact_sheet.jpg", "intro_cinematic_v2_bidirectional-proof.mp4",
        "intro_cinematic_v2_scrub_1080p24.mp4", "CAPTION_TIMELINE", "maximum_keyframe_gap",
        "sum(stage[\"display_frames\"] for stage in STAGES) != 432", "pipe.vae.enable_tiling()",
        "from_pipe(previous, torch_dtype=None)", "Unsafe one-window I2V request",
        "Synthetic frame, endpoint, and 18-second timeline contracts passed.", "assert_pipeline_dtypes",
    ]
    for marker in required:
        if marker not in joined: raise AssertionError(marker)
    for pattern in [r"sk-[A-Za-z0-9_-]{20,}", r"hf_[A-Za-z0-9]{20,}", r"AIza[A-Za-z0-9_-]{20,}"]:
        if re.search(pattern, joined): raise AssertionError("credential found")

    config_tree = ast.parse(CONFIG)
    stage_assignment = next(
        node for node in config_tree.body
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "STAGES" for target in node.targets)
    )
    stages = ast.literal_eval(stage_assignment.value)
    assert sum(stage["display_frames"] for stage in stages) == 432
    assert len(stages) == 9
    for stage in stages:
        if stage["mode"] == "i2v": model_frames = stage["display_frames"]
        elif stage["mode"] in {"i2v_drop_first", "reverse_i2v"}: model_frames = stage["display_frames"] + 1
        else: continue
        assert model_frames <= 49, (stage["id"], model_frames)

    history = 17
    for desired in (24, 35, 60, 72):
        minimum = desired + history
        model_frames = ((minimum - 1 + 3) // 4) * 4 + 1
        combined = list(range(history + model_frames))
        assert len(combined[history + history:history + history + desired]) == desired
    sentinel = list(range(49))
    assert list(reversed(sentinel))[1:] == list(range(47, -1, -1))
    assert sentinel[1:] == list(range(1, 49))


def main():
    notebook = build_notebook(); audit(notebook); OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT); print("sha256", hashlib.sha256(OUTPUT.read_bytes()).hexdigest(), "bytes", OUTPUT.stat().st_size)


if __name__ == "__main__":
    main()
