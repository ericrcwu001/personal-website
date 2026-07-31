#!/usr/bin/env python3
"""Build the proof-first HunyuanVideo 1.5 portfolio intro Colab notebook."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import re
from pathlib import Path

import nbformat

import build_skyreels_v2_colab as assets


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "hunyuanvideo15_portfolio_intro_colab.ipynb"

DIFFUSERS_COMMIT = "87beae7771f8827c335d960db7abea2967efa848"
PROOF_REPO = "hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-480p_i2v_step_distilled"
PROOF_REVISION = "854c04a4c8a53d990b418c7478f0802c0fc8c726"
PRODUCTION_REPO = "hunyuanvideo-community/HunyuanVideo-1.5-Diffusers-720p_i2v"
PRODUCTION_REVISION = "dcf088ef4e420dd54bc25930ee810bb6613dfcb5"


def build_anchors() -> dict[str, dict[str, str | int]]:
    records = {
        "hk_braemar_wide": (
            assets.fit(ROOT / "output/ai-cinematic/sora-production/anchors/hk-braemar-1280x720.webp"),
            "Local Braemar Hill late-golden-hour wide anchor.",
        ),
        "stanford_memorial_church": (
            assets.fit(ROOT / "output/imagegen/memorial-church-base.png", centering=(0.52, 0.52)),
            "Local AI-assisted Memorial Church anchor approved for the portfolio concept.",
        ),
        "stanford_main_quad_arcade": (
            assets.fit(ROOT / "web/public/media/stanford-arcade.webp", centering=(0.5, 0.5)),
            "Local Main Quad arcade reference.",
        ),
    }
    result = {}
    for name, (image, provenance) in records.items():
        payload = assets.webp_bytes(image, quality=94)
        result[name] = {
            "filename": f"{name}.webp",
            "mime": "image/webp",
            "width": 1280,
            "height": 720,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "provenance": provenance,
            "base64": base64.b64encode(payload).decode("ascii"),
        }
    return result


TITLE = r'''
# HunyuanVideo 1.5 — proof-first six-shot portfolio intro

This clean Colab workflow replaces the base generator with **Tencent HunyuanVideo 1.5** while preserving every prior SkyReels artifact in its original Drive namespace.

The notebook first renders the complete six-shot, 18-second route at 480p with the official 12-step distilled I2V checkpoint. It persists the structurally valid proof, shows motion/occlusion diagnostics as review warnings, and then stops for your visual decision. Production unlocks only when you paste the exact SHA-256 of that proof into the approval cell. Production is a separate native 720p/50-step regeneration: proof pixels are never upscaled or reused. Six production segments are dependency-hashed, resumable, and published to Drive before acceptance. Final delivery includes native 720p, 1080p, a GOP-6 scroll-scrub master, bidirectional proof, timeline sheet, seam diagnostics, QA report, manifest, and ZIP.

Route: **Braemar Hill → Central tower descent → tram/sky whip → Memorial Church → sandstone column → Main Quad arcade.** Memorial Church and the arcade are guaranteed by generating those reveals from their source anchors and reversing playback behind the sky/column occlusions.

## License boundary

Tencent HunyuanVideo 1.5 is licensed only for a territory excluding the EU, UK, and South Korea, and Section 5(c) restricts displaying Outputs outside that territory. This notebook is therefore marked **local evaluation only**. Do not deploy its final film to an unrestricted global website without legal review, geoblocking, or regenerating the final assets with a globally compatible model license.
'''


SETTINGS = r'''
# User controls.
PROOF_RUN_ID = "intro_480proof_v1"
PRODUCTION_RUN_ID = "intro_720production_v1"
MAX_PROOF_CANDIDATES = 1
MAX_PRODUCTION_CANDIDATES = 2
PERSIST_MODEL_CACHE_TO_DRIVE = False
LOCAL_EVALUATION_ONLY = True

FPS = 24
PROOF_STEPS = 12
PRODUCTION_STEPS = 50
PROOF_SEED_BASE = 51000

if not LOCAL_EVALUATION_ONLY:
    raise ValueError("This notebook is intentionally restricted to local evaluation pending license review")
if MAX_PROOF_CANDIDATES not in {1, 2, 3} or MAX_PRODUCTION_CANDIDATES not in {1, 2, 3}:
    raise ValueError("Candidate counts must be 1, 2, or 3")
print("Proof:", PROOF_RUN_ID, "| Production:", PRODUCTION_RUN_ID)
'''


DRIVE_SETUP = r'''
# Mount Drive and isolate every Hunyuan artifact from the existing SkyReels runs.
from google.colab import drive
from pathlib import Path
import base64, fractions, gc, hashlib, io, json, math, os, platform, shutil, subprocess, sys, time, uuid, zipfile

drive.mount("/content/drive", force_remount=False)

DRIVE_ROOT = Path("/content/drive/MyDrive/Personal_Website_HunyuanVideo15")
DRIVE_INPUTS = DRIVE_ROOT / "inputs"
DRIVE_CACHE = DRIVE_ROOT / "cache"
DRIVE_PROOF = DRIVE_ROOT / "runs" / PROOF_RUN_ID
DRIVE_PRODUCTION = DRIVE_ROOT / "runs" / PRODUCTION_RUN_ID

RUNTIME_ROOT = Path("/content/hunyuan15_runtime")
RUNTIME_INPUTS = RUNTIME_ROOT / "inputs"
RUNTIME_MODELS = RUNTIME_ROOT / "models"
RUNTIME_PROOF = RUNTIME_ROOT / "runs" / PROOF_RUN_ID
RUNTIME_PRODUCTION = RUNTIME_ROOT / "runs" / PRODUCTION_RUN_ID

for path in (DRIVE_INPUTS, DRIVE_CACHE, DRIVE_PROOF, DRIVE_PRODUCTION,
             RUNTIME_INPUTS, RUNTIME_MODELS, RUNTIME_PROOF, RUNTIME_PRODUCTION):
    path.mkdir(parents=True, exist_ok=True)

probe = DRIVE_ROOT / f".write-probe-{uuid.uuid4().hex}"
payload = f"hunyuan persistence probe {time.time_ns()}\n"
probe.write_text(payload, encoding="utf-8")
if probe.read_text(encoding="utf-8") != payload:
    raise RuntimeError("Google Drive persistence check failed")
probe.unlink()

def free_gib(path):
    return shutil.disk_usage(path).free / (1024 ** 3)

print("Hunyuan Drive root:", DRIVE_ROOT)
print("SkyReels is untouched at: /content/drive/MyDrive/Personal_Website_SkyReelsV2")
print("Local free:", round(free_gib("/content"), 1), "GiB | Drive free:", round(free_gib(DRIVE_ROOT), 1), "GiB")
'''


ANCHORS_TEMPLATE = r"""
# Restore three self-contained anchors to Drive and the local inference SSD.
from PIL import Image, ImageDraw
from IPython.display import display

EMBEDDED_ANCHORS = json.loads(r'''__ANCHORS_JSON__''')
ANCHOR_PATHS = {}
anchor_manifest = {}

for name, record in EMBEDDED_ANCHORS.items():
    raw = base64.b64decode(record["base64"])
    if hashlib.sha256(raw).hexdigest() != record["sha256"]:
        raise RuntimeError(f"Embedded anchor hash failed: {name}")
    drive_path = DRIVE_INPUTS / record["filename"]
    if not drive_path.is_file() or hashlib.sha256(drive_path.read_bytes()).hexdigest() != record["sha256"]:
        temp = drive_path.with_name(drive_path.name + f".part-{uuid.uuid4().hex}")
        temp.write_bytes(raw); os.replace(temp, drive_path)
    local_path = RUNTIME_INPUTS / record["filename"]
    shutil.copy2(drive_path, local_path)
    if hashlib.sha256(local_path.read_bytes()).hexdigest() != record["sha256"]:
        raise RuntimeError(f"Local anchor copy failed: {name}")
    ANCHOR_PATHS[name] = local_path
    anchor_manifest[name] = {key: value for key, value in record.items() if key != "base64"}

manifest_path = DRIVE_INPUTS / "anchor_manifest.json"
temp = manifest_path.with_name(manifest_path.name + f".part-{uuid.uuid4().hex}")
temp.write_text(json.dumps(anchor_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
os.replace(temp, manifest_path)

thumbs = []
for name, path in ANCHOR_PATHS.items():
    image = Image.open(path).convert("RGB").resize((480, 270), Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", (480, 302), "#111111"); canvas.paste(image, (0, 0))
    ImageDraw.Draw(canvas).text((10, 278), name.replace("_", " "), fill="white")
    thumbs.append(canvas)
sheet = Image.new("RGB", (960, math.ceil(len(thumbs) / 2) * 302), "#111111")
for index, thumb in enumerate(thumbs): sheet.paste(thumb, ((index % 2) * 480, (index // 2) * 302))
sheet_path = DRIVE_INPUTS / "anchor_contact_sheet.jpg"; sheet.save(sheet_path, "JPEG", quality=92)
display(sheet)
"""


PREFLIGHT = r'''
# A100-80, storage, and license preflight.
import torch
from packaging.version import Version

if not torch.cuda.is_available():
    raise RuntimeError("CUDA unavailable. Select an A100 GPU runtime.")
if Version(torch.__version__.split("+")[0]) < Version("2.6"):
    raise RuntimeError(f"HunyuanVideo 1.5 needs torch>=2.6; found {torch.__version__}")
gpu = torch.cuda.get_device_properties(0)
vram_gib = gpu.total_memory / (1024 ** 3)
ram_gib = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / (1024 ** 3)
if "A100" not in gpu.name or vram_gib < 75:
    raise RuntimeError(f"Need A100 80GB; found {gpu.name} with {vram_gib:.1f} GiB")
if ram_gib < 80:
    raise RuntimeError(f"Need High-RAM runtime; found {ram_gib:.1f} GiB")
if free_gib("/content") < 72:
    raise RuntimeError(f"Need at least 72 GiB local free; found {free_gib('/content'):.1f}")
if free_gib(DRIVE_ROOT) < 15:
    raise RuntimeError(f"Need at least 15 GiB Drive free for durable media; found {free_gib(DRIVE_ROOT):.1f}")
for binary in ("ffmpeg", "ffprobe", "rsync"):
    if shutil.which(binary) is None: raise RuntimeError(f"Missing binary: {binary}")

print("GPU:", gpu.name, f"{vram_gib:.1f} GiB | RAM: {ram_gib:.1f} GiB")
print("LICENSE WARNING: local evaluation only; outputs are not cleared for unrestricted global deployment.")
'''


INSTALL = rf'''
# Install the pinned HunyuanVideo 1.5 Diffusers runtime.
DIFFUSERS_COMMIT = "{DIFFUSERS_COMMIT}"
packages = [
    f"git+https://github.com/huggingface/diffusers.git@{{DIFFUSERS_COMMIT}}",
    "transformers==5.14.1", "accelerate==1.14.0", "huggingface-hub==1.24.0",
    "safetensors==0.8.0", "imageio==2.37.0", "imageio-ffmpeg==0.6.0",
    "opencv-python-headless==4.12.0.88", "kernels==0.16.0",
]
subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", *packages])

import accelerate, cv2, diffusers, huggingface_hub, numpy as np, safetensors, transformers
from huggingface_hub import model_info, snapshot_download
from safetensors import safe_open
from diffusers import HunyuanVideo15ImageToVideoPipeline

if not hasattr(diffusers, "HunyuanVideo15ImageToVideoPipeline"):
    raise RuntimeError("Pinned Diffusers commit lacks HunyuanVideo15ImageToVideoPipeline")
versions = {{
    "python": platform.python_version(), "torch": torch.__version__, "diffusers": diffusers.__version__,
    "transformers": transformers.__version__, "accelerate": accelerate.__version__,
    "huggingface_hub": huggingface_hub.__version__, "safetensors": safetensors.__version__,
}}
print(json.dumps(versions, indent=2))
'''


CONFIG = rf'''
# Lock models, six segments, captions, and reproducible fingerprints.
PROOF_MODEL = {{
    "repo_id": "{PROOF_REPO}", "revision": "{PROOF_REVISION}",
    "width": 848, "height": 480, "steps": PROOF_STEPS, "expected_gib": 32.25,
    "target_size": 640, "use_meanflow": True,
}}
PRODUCTION_MODEL = {{
    "repo_id": "{PRODUCTION_REPO}", "revision": "{PRODUCTION_REVISION}",
    "width": 1280, "height": 720, "steps": PRODUCTION_STEPS, "expected_gib": 50.51,
    "target_size": 960, "use_meanflow": False,
}}

NEGATIVE_PROMPT = (
    "static camera, hovering, digital zoom, flat rotating photograph, crossfade, dissolve, morph, portal, "
    "melting architecture, duplicated building, bent facade, warped street, unreadable geometry, flicker, "
    "jitter, camera cut, title, caption, logo, watermark, illustration"
)

SEGMENTS = [
    {{
        "id": "S0_hk_skyline_push", "display_frames": 72, "request_frames": 73,
        "mode": "forward_anchor", "anchor": "hk_braemar_wide", "motion_min": 0.35,
        "seeds": [61003, 61047],
        "prompt": "Photorealistic late-golden-hour Hong Kong. An FPV cinema dolly immediately accelerates from Braemar Hill toward Central. Foreground hillside and apartments rush outward with differential parallax while Bank of China Tower and Two IFC enlarge through real forward translation. Level 24mm lens, stable buildings, no zoom, flat-image rotation, cut, morph, or hold.",
    }},
    {{
        "id": "S1_hk_tower_descent", "parent": "S0_hk_skyline_push", "display_frames": 72,
        "request_frames": 73, "mode": "forward_parent", "motion_min": 0.48,
        "seeds": [62011, 62061],
        "prompt": "Continue the exact forward velocity through a clear gap between Central skyscrapers. Keep the horizon level while facades rise along both edges and the street grid expands centrally. Descend aggressively but smoothly toward Des Voeux Road, stable straight architecture, no orbit, roll, hovering, crossfade, or morph.",
    }},
    {{
        "id": "S2_tram_to_sky_whip", "parent": "S1_hk_tower_descent", "display_frames": 60,
        "request_frames": 61, "mode": "forward_parent", "motion_min": 0.58,
        "min_sky_end": 6, "max_sky_end": 12, "seeds": [63013, 63067],
        "prompt": "Level at tram-wire height on Des Voeux Road with a red double-decker tram ahead. Surge toward and skim above the tram roof, then crane and whip-pitch upward. Wires and towers streak through the lower frame; only the final six to ten frames are completely textured blue-gold sky. No fade, flash, cut, or lingering cloud tunnel.",
    }},
    {{
        "id": "S3_sky_to_memorial_church", "parent": "S2_tram_to_sky_whip", "display_frames": 72,
        "request_frames": 73, "mode": "reverse_anchor", "anchor": "stanford_memorial_church",
        "motion_min": 0.32, "min_sky_start": 4, "max_sky_start": 12, "seeds": [64007, 64043],
        "prompt": "Begin exactly on the complete Stanford Memorial Church mosaic facade at late golden hour. Immediately accelerate backward and crane upward; the church and sandstone quad descend naturally below frame. Finish with only eight to twelve frames of textured blue-gold sky. Stable mosaic, straight arches, no morphing, fade, or pause.",
    }},
    {{
        "id": "S4_church_to_column", "parent": "S3_sky_to_memorial_church", "display_frames": 72,
        "request_frames": 73, "mode": "forward_parent", "motion_min": 0.38,
        "min_dark_end": 4, "max_dark_end": 10, "seeds": [65017, 65059],
        "prompt": "Continue forward-right across the unmistakable Memorial Church facade and Main Quad. Enter the arcade with stable sandstone geometry. A single near sandstone column sweeps across the lens only during the final four to eight frames and fully covers the frame with dark textured masonry. No fade or black flash.",
    }},
    {{
        "id": "S5_column_to_arcade", "parent": "S4_church_to_column", "display_frames": 84,
        "request_frames": 85, "mode": "reverse_anchor", "anchor": "stanford_main_quad_arcade",
        "motion_min": 0.28, "min_dark_start": 4, "max_dark_start": 10, "seeds": [66019, 66057],
        "prompt": "Begin exactly inside Stanford Main Quad arcade, gliding forward slightly off axis. Accelerate backward until the same nearest sandstone column fills the final six to ten frames with dark textured masonry. Repeating arches remain straight and stable, strong near-column parallax, no fade to black or geometry deformation.",
    }},
]

if sum(segment["display_frames"] for segment in SEGMENTS) != 432:
    raise RuntimeError("Six production segments must total exactly 432 frames")
if any(segment["request_frames"] % 4 != 1 for segment in SEGMENTS):
    raise RuntimeError("Every Hunyuan request must be 4n+1 frames")

CAPTION_TIMELINE = [
    {{"id":"hong_kong_a","scroll_progress":[0,.25],"chapter_video_frames":[0,72],"visible_video_frames":[0,72],"lines":["Eric Wu"]}},
    {{"id":"hong_kong_b","scroll_progress":[.25,.5],"chapter_video_frames":[72,204],"visible_video_frames":[72,180],"lines":["Interested in: AI Engineering & Research","Math, CS, Public Policy"]}},
    {{"id":"stanford_a","scroll_progress":[.5,.75],"chapter_video_frames":[204,348],"visible_video_frames":[228,336],"lines":["Stanford Class of 2029"]}},
    {{"id":"stanford_b","scroll_progress":[.75,1.0],"chapter_video_frames":[348,432],"visible_video_frames":[360,432],"icons":["GitHub","LinkedIn","X","Instagram","Email"]}},
]

STABLE_CONFIG = {{
    "logic_version": "hunyuan15-six-shot-v1.1.0", "fps": FPS,
    "diffusers_commit": DIFFUSERS_COMMIT, "proof_model": PROOF_MODEL,
    "production_model": PRODUCTION_MODEL, "segments": SEGMENTS,
    "negative_prompt": NEGATIVE_PROMPT, "captions": CAPTION_TIMELINE,
    "anchors": {{name: data["sha256"] for name, data in anchor_manifest.items()}},
    "license_scope": "local evaluation only; not cleared for unrestricted global deployment",
}}
CONFIG_FINGERPRINT = hashlib.sha256(json.dumps(STABLE_CONFIG, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def write_locked_config(root, run_id, profile):
    path = root / "config.json"
    payload = {{**STABLE_CONFIG, "run_id": run_id, "profile": profile, "config_fingerprint": CONFIG_FINGERPRINT, "runtime_versions": versions}}
    if path.is_file():
        existing = json.loads(path.read_text())
        if existing.get("config_fingerprint") != CONFIG_FINGERPRINT or existing.get("profile") != profile:
            raise RuntimeError(f"Run {{run_id}} has a different configuration. Change the run ID.")
    else:
        temp = path.with_name(path.name + f".part-{{uuid.uuid4().hex}}")
        temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n"); os.replace(temp, path)

write_locked_config(DRIVE_PROOF, PROOF_RUN_ID, "480p_step_distilled")
write_locked_config(DRIVE_PRODUCTION, PRODUCTION_RUN_ID, "720p_full")
print("Configuration:", CONFIG_FINGERPRINT)
for segment in SEGMENTS: print(segment["id"], segment["display_frames"], "display frames")
'''


UTILITIES = r'''
# Hashing, model acquisition, candidate persistence, metrics, and Hunyuan frame policies.
def sha256_file(path, chunk_size=8 * 1024 * 1024):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        while chunk := handle.read(chunk_size): digest.update(chunk)
    return digest.hexdigest()

def atomic_write_json(destination, payload):
    destination = Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + f".part-{uuid.uuid4().hex}")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, destination)

def atomic_publish_file(source, destination):
    source, destination = Path(source), Path(destination); destination.parent.mkdir(parents=True, exist_ok=True)
    digest = sha256_file(source)
    temp = destination.with_name(destination.name + f".part-{digest[:12]}-{uuid.uuid4().hex}")
    shutil.copy2(source, temp)
    if sha256_file(temp) != digest: temp.unlink(missing_ok=True); raise RuntimeError("Drive copy hash failed")
    os.replace(temp, destination)
    if sha256_file(destination) != digest: raise RuntimeError(f"Published Drive hash failed: {destination}")
    return digest

def probe_video(path):
    result = subprocess.run(["ffprobe","-count_frames","-v","error","-select_streams","v:0",
        "-show_entries","stream=width,height,avg_frame_rate,nb_read_frames,duration","-of","json",str(path)],
        check=True,capture_output=True,text=True)
    stream = json.loads(result.stdout)["streams"][0]
    return {"width":int(stream["width"]),"height":int(stream["height"]),
            "fps":float(fractions.Fraction(stream["avg_frame_rate"])),
            "frames":int(stream["nb_read_frames"]),"duration":float(stream.get("duration") or 0)}

def maximum_keyframe_gap(path):
    result = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","frame=key_frame","-of","json",str(path)],
                            check=True,capture_output=True,text=True)
    flags=[int(frame["key_frame"]) for frame in json.loads(result.stdout)["frames"]]
    keys=[i for i,flag in enumerate(flags) if flag]
    if not keys or keys[0] != 0: return len(flags)
    return max([b-a for a,b in zip(keys,keys[1:])] + [len(flags)-keys[-1]])

def frame_to_uint8(frame):
    if isinstance(frame, Image.Image): return np.asarray(frame.convert("RGB"),dtype=np.uint8)
    array=np.asarray(frame)
    if np.issubdtype(array.dtype,np.floating) and array.max(initial=0) <= 1.01: array=array*255
    return np.clip(array,0,255).astype(np.uint8)[:,:,:3]

def normalize_output(output):
    frames=output.frames[0]
    if isinstance(frames,np.ndarray) and frames.ndim==4: frames=list(frames)
    return [frame_to_uint8(frame) for frame in frames]

def encode_video(frames,destination,width=None,height=None,crf=17,gop=None):
    first=frame_to_uint8(frames[0]); source_h,source_w=first.shape[:2]
    filters=[]
    if width and height: filters=["-vf",f"scale={width}:{height}:flags=lanczos"]
    command=["ffmpeg","-y","-v","error","-f","rawvideo","-pix_fmt","rgb24","-s:v",f"{source_w}x{source_h}","-r",str(FPS),"-i","-","-an",*filters,
             "-c:v","libx264","-preset","medium","-crf",str(crf),"-pix_fmt","yuv420p"]
    if gop: command += ["-g",str(gop),"-keyint_min",str(gop),"-sc_threshold","0","-bf","0","-tune","fastdecode"]
    command += ["-movflags","+faststart",str(destination)]
    process=subprocess.Popen(command,stdin=subprocess.PIPE)
    try:
        for frame in frames: process.stdin.write(frame_to_uint8(frame).tobytes())
    finally: process.stdin.close()
    if process.wait()!=0: raise RuntimeError("ffmpeg encoding failed")

def write_contact_sheet(frames,destination,label):
    indices=np.linspace(0,len(frames)-1,min(8,len(frames)),dtype=int)
    sheet=Image.new("RGB",(1280,412),"#111111"); draw=ImageDraw.Draw(sheet)
    for position,index in enumerate(indices):
        tile=Image.fromarray(frame_to_uint8(frames[index])).resize((320,180),Image.Resampling.LANCZOS)
        x=(position%4)*320; y=(position//4)*206; sheet.paste(tile,(x,y))
        draw.text((x+8,y+184),f"frame {index:03d}",fill="white")
    draw.rectangle((0,0,500,28),fill="black"); draw.text((8,7),label,fill="white")
    sheet.save(destination,"JPEG",quality=91,optimize=True)

def analyze_frames(frames,segment,parent_frame=None):
    small=[cv2.cvtColor(cv2.resize(frame,(320,180)),cv2.COLOR_RGB2GRAY) for frame in frames]
    flows,diffs=[],[]
    for previous,current in zip(small,small[1:]):
        flow=cv2.calcOpticalFlowFarneback(previous,current,None,.5,3,21,3,5,1.2,0)
        flows.append(float(np.linalg.norm(flow,axis=2).mean()))
        diffs.append(float(np.abs(current.astype(np.float32)-previous.astype(np.float32)).mean()))
    freeze=maximum_freeze=0
    for value in diffs:
        freeze=freeze+1 if value<.55 else 0; maximum_freeze=max(maximum_freeze,freeze)
    gray=[cv2.cvtColor(frame,cv2.COLOR_RGB2GRAY) for frame in frames]
    def sky(image):
        edge=(np.abs(np.diff(image.astype(np.float32),axis=0)).mean()+np.abs(np.diff(image.astype(np.float32),axis=1)).mean())/2
        return edge<5 and float(image.mean())>90
    def dark(image): return float(image.mean())<70
    def leading(predicate):
        count=0
        for image in gray:
            if predicate(image): count+=1
            else: break
        return count
    def trailing(predicate):
        count=0
        for image in reversed(gray):
            if predicate(image): count+=1
            else: break
        return count
    metrics={"median_flow":float(np.median(flows)),"mean_flow":float(np.mean(flows)),
             "maximum_freeze_run":int(maximum_freeze),"sky_start_run":leading(sky),"sky_end_run":trailing(sky),
             "dark_start_run":leading(dark),"dark_end_run":trailing(dark),
             "start_adjacent_mae":float(np.abs(frames[1].astype(np.float32)-frames[0].astype(np.float32)).mean()),
             "end_adjacent_mae":float(np.abs(frames[-1].astype(np.float32)-frames[-2].astype(np.float32)).mean()),
             "parent_boundary_mae":None if parent_frame is None else float(np.abs(parent_frame.astype(np.float32)-frames[0].astype(np.float32)).mean())}
    failures=[]; catastrophic=[]
    if metrics["median_flow"]<segment["motion_min"]: failures.append("motion_too_weak")
    if maximum_freeze>4: failures.append("freeze_run")
    if maximum_freeze>12: catastrophic.append("catastrophic_freeze_run")
    if metrics["parent_boundary_mae"] is not None and metrics["parent_boundary_mae"]>45: failures.append("parent_boundary_jump")
    if metrics["parent_boundary_mae"] is not None and metrics["parent_boundary_mae"]>60: catastrophic.append("catastrophic_parent_jump")
    for key,metric in (("min_sky_end","sky_end_run"),("min_sky_start","sky_start_run"),("min_dark_end","dark_end_run"),("min_dark_start","dark_start_run")):
        if key in segment and metrics[metric]<segment[key]: failures.append(key.replace("min_","")+"_missing")
    for key,metric in (("max_sky_end","sky_end_run"),("max_sky_start","sky_start_run"),("max_dark_end","dark_end_run"),("max_dark_start","dark_start_run")):
        if key in segment and metrics[metric]>segment[key]: failures.append(key.replace("max_","")+"_too_long")
    metrics["failures"]=failures; metrics["catastrophic_failures"]=catastrophic
    metrics["hard_pass"]=not failures and not catastrophic; metrics["usable"]=not catastrophic
    metrics["score"]=metrics["median_flow"]-2*len(failures)-.08*maximum_freeze
    return metrics

def segment_by_id(segment_id): return next(segment for segment in SEGMENTS if segment["id"]==segment_id)
def stage_root(run_root,segment_id): return run_root/"stages"/segment_id
def accepted_pointer(run_root,segment_id): return stage_root(run_root,segment_id)/"accepted.json"

def current_parent_hash(run_root,segment):
    if not segment.get("parent"): return "ROOT"
    accepted=accepted_candidate(run_root,segment_by_id(segment["parent"]))
    if accepted is None: raise RuntimeError(f"Parent not accepted: {segment['parent']}")
    return accepted[1]["manifest_file_sha256"]

def candidate_fingerprint(run_root,segment,seed,profile):
    proof_hash=None
    if profile=="production":
        approval_path=DRIVE_PROOF/"approval.json"
        if approval_path.is_file(): proof_hash=json.loads(approval_path.read_text()).get("proof_master_sha256")
    payload={"config":CONFIG_FINGERPRINT,"profile":profile,"segment":segment,"seed":seed,
             "parent":current_parent_hash(run_root,segment),"approved_proof_sha256":proof_hash}
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(",", ":")).encode()).hexdigest()

def candidate_dir(run_root,segment,seed,profile,fingerprint=None):
    fingerprint=fingerprint or candidate_fingerprint(run_root,segment,seed,profile)
    return stage_root(run_root,segment["id"])/"candidates"/fingerprint/str(seed)

def validate_candidate(run_root,segment,seed,profile,width,height):
    fingerprint=candidate_fingerprint(run_root,segment,seed,profile)
    directory=candidate_dir(run_root,segment,seed,profile,fingerprint); path=directory/"manifest.json"
    if not path.is_file(): return False,"manifest missing",None
    try:
        manifest=json.loads(path.read_text())
        if manifest["candidate_fingerprint"]!=fingerprint: return False,"fingerprint changed",None
        for name,record in manifest["artifacts"].items():
            artifact=directory/name
            if not artifact.is_file() or artifact.stat().st_size!=record["bytes"] or sha256_file(artifact)!=record["sha256"]: return False,f"artifact invalid: {name}",None
        probe=probe_video(directory/"clip.mp4")
        if (probe["width"],probe["height"],probe["frames"])!=(width,height,segment["display_frames"]): return False,f"video mismatch: {probe}",None
        manifest["manifest_file_sha256"]=sha256_file(path)
        return True,"validated",manifest
    except Exception as error: return False,str(error),None

def accepted_candidate(run_root,segment):
    if segment.get("parent") and accepted_candidate(run_root,segment_by_id(segment["parent"])) is None: return None
    pointer=accepted_pointer(run_root,segment["id"])
    if not pointer.is_file(): return None
    record=json.loads(pointer.read_text()); seed=record["seed"]
    profile=record["profile"]; model=PROOF_MODEL if profile=="proof" else PRODUCTION_MODEL
    expected_fingerprint=candidate_fingerprint(run_root,segment,seed,profile)
    if record.get("candidate_fingerprint")!=expected_fingerprint: return None
    ok,_,manifest=validate_candidate(run_root,segment,seed,profile,model["width"],model["height"])
    if not ok or manifest["manifest_file_sha256"]!=record["manifest_file_sha256"]: return None
    return seed,manifest

def accept_candidate(run_root,segment,seed,manifest,profile):
    atomic_write_json(accepted_pointer(run_root,segment["id"]),{"segment_id":segment["id"],"seed":seed,"profile":profile,
        "candidate_fingerprint":manifest["candidate_fingerprint"],"manifest_file_sha256":manifest["manifest_file_sha256"],
        "metrics":manifest["metrics"],"accepted_at_unix":time.time()})

def restore_accepted(run_root,segment_id,filename):
    segment=segment_by_id(segment_id); accepted=accepted_candidate(run_root,segment)
    if accepted is None: raise RuntimeError(f"Not accepted: {segment_id}")
    seed,manifest=accepted
    source=candidate_dir(run_root,segment,seed,manifest["profile"],manifest["candidate_fingerprint"])/filename
    destination=RUNTIME_ROOT/"restored"/run_root.name/segment_id/filename; destination.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(source,destination)
    if sha256_file(destination)!=manifest["artifacts"][filename]["sha256"]: raise RuntimeError("Restore hash mismatch")
    return destination

def publish_candidate(run_root,runtime_root,segment,seed,profile,frames,generation,parent_frame):
    if len(frames)!=segment["display_frames"]: raise RuntimeError(f"Frame mismatch for {segment['id']}")
    local=runtime_root/"candidates"/segment["id"]/str(seed)
    if local.exists(): shutil.rmtree(local)
    local.mkdir(parents=True)
    clip=local/"clip.mp4"; final=local/"final_frame.png"; sheet=local/"contact_sheet.jpg"
    encode_video(frames,clip); Image.fromarray(frames[-1]).save(final,"PNG",optimize=True)
    write_contact_sheet(frames,sheet,f"{segment['id']} | seed {seed} | {profile}")
    metrics=analyze_frames(frames,segment,parent_frame)
    metrics_path=local/"metrics.json"; metrics_path.write_text(json.dumps(metrics,indent=2)+"\n")
    generation_path=local/"generation.json"; generation_path.write_text(json.dumps(generation,indent=2)+"\n")
    fingerprint=candidate_fingerprint(run_root,segment,seed,profile)
    drive=candidate_dir(run_root,segment,seed,profile,fingerprint); artifacts={}
    for path in (clip,final,sheet,metrics_path,generation_path):
        digest=atomic_publish_file(path,drive/path.name); artifacts[path.name]={"bytes":path.stat().st_size,"sha256":digest}
    manifest={"status":"complete","segment_id":segment["id"],"seed":seed,"profile":profile,
              "parent_hash":current_parent_hash(run_root,segment),"candidate_fingerprint":fingerprint,
              "metrics":metrics,"artifacts":artifacts,"generation":generation}
    atomic_write_json(drive/"manifest.json",manifest)
    manifest["manifest_file_sha256"]=sha256_file(drive/"manifest.json")
    return manifest

def acquire_model(model,profile):
    slug=model["repo_id"].replace("/","--")
    if PERSIST_MODEL_CACHE_TO_DRIVE:
        source=DRIVE_CACHE/"hf-snapshots"/slug/model["revision"]
    else:
        source=RUNTIME_ROOT/"hf-snapshots"/slug/model["revision"]
    source.mkdir(parents=True,exist_ok=True)
    info=model_info(model["repo_id"],revision=model["revision"],files_metadata=True)
    if info.sha!=model["revision"]: raise RuntimeError("Pinned Hugging Face revision changed")
    expected={item.rfilename:item.size for item in info.siblings if item.size is not None}
    missing_bytes=sum(size for name,size in expected.items() if not (source/name).is_file() or (source/name).stat().st_size!=size)
    reserve_bytes=15*(1024**3)
    capacity_root=DRIVE_ROOT if PERSIST_MODEL_CACHE_TO_DRIVE else Path("/content")
    if shutil.disk_usage(capacity_root).free < missing_bytes+reserve_bytes:
        raise RuntimeError(
            f"Not enough free space for {profile}: need {missing_bytes/(1024**3):.1f} GiB download "
            f"plus 15 GiB reserve at {capacity_root}"
        )
    snapshot=Path(snapshot_download(repo_id=model["repo_id"],revision=model["revision"],local_dir=str(source),max_workers=2))
    invalid=[name for name,size in expected.items() if not (snapshot/name).is_file() or (snapshot/name).stat().st_size!=size]
    if invalid: raise RuntimeError(f"Incomplete {profile} snapshot: {invalid[:5]}")
    for path in snapshot.rglob("*.safetensors"):
        with safe_open(path,framework="pt",device="cpu") as handle:
            if not handle.keys(): raise RuntimeError(f"Empty safetensors file: {path}")
    if PERSIST_MODEL_CACHE_TO_DRIVE:
        total_bytes=sum(expected.values())
        if free_gib("/content") < total_bytes/(1024**3)+15:
            raise RuntimeError(f"Need {total_bytes/(1024**3)+15:.1f} GiB local free to stage the {profile} model")
        local=RUNTIME_MODELS/slug/model["revision"]; local.mkdir(parents=True,exist_ok=True)
        subprocess.run(["rsync","-a",str(snapshot)+"/",str(local)+"/"],check=True)
        for name,size in expected.items():
            if not (local/name).is_file() or (local/name).stat().st_size!=size: raise RuntimeError(f"Local model copy invalid: {name}")
        return local
    return snapshot

def load_hunyuan(model_dir,model,profile):
    pipe=HunyuanVideo15ImageToVideoPipeline.from_pretrained(str(model_dir),torch_dtype=torch.bfloat16,
                                                            local_files_only=True,low_cpu_mem_usage=True)
    if pipe.__class__.__name__!="HunyuanVideo15ImageToVideoPipeline": raise RuntimeError("Wrong pipeline class")
    config=pipe.transformer.config
    if config.task_type!="i2v" or int(config.target_size)!=model["target_size"]:
        raise RuntimeError(f"Wrong {profile} transformer contract: task={config.task_type}, target={config.target_size}")
    if bool(getattr(config,"use_meanflow",False))!=model["use_meanflow"]:
        raise RuntimeError(f"Wrong MeanFlow contract for {profile}")
    if int(pipe.vae.config.temporal_compression_ratio)!=4: raise RuntimeError("Wrong VAE temporal compression")
    if pipe.transformer.dtype!=torch.bfloat16: raise RuntimeError(f"Wrong transformer dtype: {pipe.transformer.dtype}")
    # Hunyuan uses padded text masks; the non-varlen Flash-Attention 2 backend rejects them.
    pipe.transformer.set_attention_backend("flash_varlen_hub")
    pipe.vae.enable_tiling(); pipe.enable_model_cpu_offload()
    return pipe

def dispose_pipeline(pipe):
    if pipe is not None:
        try: pipe.remove_all_hooks()
        except Exception: pass
        del pipe
    gc.collect(); torch.cuda.empty_cache()

def purge_runtime_model(model_dir):
    path=Path(model_dir).resolve()
    runtime=RUNTIME_ROOT.resolve()
    if path==runtime or runtime not in path.parents: raise RuntimeError(f"Refusing unsafe model cleanup: {path}")
    shutil.rmtree(path,ignore_errors=False)
    print("Released temporary local model snapshot:",path)

def blend_hidden_boundary(frames,parent_frame,count=8):
    frames=list(frames)
    for index in range(min(count,len(frames))):
        parent_weight=(count-index)/(count+1)
        frames[index]=np.clip(parent_frame.astype(np.float32)*parent_weight+frames[index].astype(np.float32)*(1-parent_weight),0,255).astype(np.uint8)
    return frames

def render_segment(pipe,run_root,runtime_root,segment,seed,profile):
    model=PROOF_MODEL if profile=="proof" else PRODUCTION_MODEL
    parent_frame=None
    if segment.get("parent"):
        parent_frame=np.asarray(Image.open(restore_accepted(run_root,segment["parent"],"final_frame.png")).convert("RGB"),dtype=np.uint8)
    if segment["mode"] in {"forward_anchor","reverse_anchor"}:
        input_image=Image.open(ANCHOR_PATHS[segment["anchor"]]).convert("RGB")
    else:
        input_image=Image.fromarray(parent_frame)
    input_image=input_image.resize((model["width"],model["height"]),Image.Resampling.LANCZOS)
    generator=torch.Generator(device="cuda").manual_seed(seed)
    started=time.time()
    output=pipe(image=input_image,prompt=segment["prompt"],negative_prompt=NEGATIVE_PROMPT,
                num_frames=segment["request_frames"],num_inference_steps=model["steps"],generator=generator,output_type="np")
    raw=normalize_output(output)
    if len(raw)!=segment["request_frames"]: raise RuntimeError(f"Hunyuan returned {len(raw)} frames, expected {segment['request_frames']}")
    input_exact=np.asarray(input_image.resize((raw[0].shape[1],raw[0].shape[0]),Image.Resampling.LANCZOS),dtype=np.uint8)
    raw[0]=input_exact
    if segment["mode"]=="forward_anchor": frames=raw[:segment["display_frames"]]
    elif segment["mode"]=="forward_parent": frames=raw[1:1+segment["display_frames"]]
    elif segment["mode"]=="reverse_anchor":
        frames=list(reversed(raw))[1:1+segment["display_frames"]]
        frames=blend_hidden_boundary(frames,parent_frame,8)
    else: raise ValueError(segment["mode"])
    generation={"model":model,"diffusers_commit":DIFFUSERS_COMMIT,"started_at_unix":started,
                "completed_at_unix":time.time(),"frame_policy":segment["mode"],"license":"local evaluation only"}
    return publish_candidate(run_root,runtime_root,segment,seed,profile,frames,generation,parent_frame)
'''


PROOF = r'''
# Quick full-route proof: six 480p/12-step segments, persisted before production unlock.
from IPython.display import Video, display

PROOF_GATE = DRIVE_PROOF / "proof_gate.json"

def proof_gate_record():
    if not PROOF_GATE.is_file(): return None
    try: return json.loads(PROOF_GATE.read_text())
    except Exception: return None

def proof_gate_valid():
    gate=proof_gate_record()
    if gate is None: return False
    try:
        if gate.get("config_fingerprint")!=CONFIG_FINGERPRINT or gate.get("status")!="passed": return False
        for segment in SEGMENTS:
            accepted=accepted_candidate(DRIVE_PROOF,segment)
            if accepted is None: return False
            if gate.get("accepted_manifest_hashes",{}).get(segment["id"])!=accepted[1]["manifest_file_sha256"]: return False
        master=DRIVE_PROOF/"deliverables"/"proof_480p24.mp4"
        return master.is_file() and sha256_file(master)==gate["master_sha256"]
    except Exception: return False

if proof_gate_valid():
    print("Validated existing proof; no proof model download or regeneration required.")
else:
    proof_model_dir=None; proof_pipe=None; proof_complete=False
    try:
        if not all(accepted_candidate(DRIVE_PROOF,segment) is not None for segment in SEGMENTS):
            proof_model_dir=acquire_model(PROOF_MODEL,"proof")
            proof_pipe=load_hunyuan(proof_model_dir,PROOF_MODEL,"proof")
        for index,segment in enumerate(SEGMENTS):
            existing=accepted_candidate(DRIVE_PROOF,segment)
            if existing:
                print("Proof segment restored:",segment["id"],existing[0]); continue
            seeds=[PROOF_SEED_BASE+index*101+offset for offset in (0,37,83)][:MAX_PROOF_CANDIDATES]
            passing=[]
            for seed in seeds:
                ok,reason,manifest=validate_candidate(DRIVE_PROOF,segment,seed,"proof",PROOF_MODEL["width"],PROOF_MODEL["height"])
                if not ok:
                    print("Generating proof",segment["id"],"seed",seed,"because",reason)
                    manifest=render_segment(proof_pipe,DRIVE_PROOF,RUNTIME_PROOF,segment,seed,"proof")
                print(segment["id"],seed,json.dumps(manifest["metrics"],indent=2))
                display(Image.open(candidate_dir(DRIVE_PROOF,segment,seed,"proof")/"contact_sheet.jpg"))
                if manifest["metrics"]["usable"]:
                    passing.append((manifest["metrics"]["score"],seed,manifest)); break
            if not passing:
                raise RuntimeError(f"Proof gate failed at {segment['id']}: {manifest['metrics']}")
            _,seed,manifest=max(passing,key=lambda item:item[0])
            accept_candidate(DRIVE_PROOF,segment,seed,manifest,"proof")
        proof_complete=True
    finally:
        dispose_pipeline(proof_pipe)
        proof_pipe=None
        if proof_complete and proof_model_dir is not None: purge_runtime_model(proof_model_dir)

    deliverables=DRIVE_PROOF/"deliverables"; deliverables.mkdir(parents=True,exist_ok=True)
    clips=[restore_accepted(DRIVE_PROOF,segment["id"],"clip.mp4") for segment in SEGMENTS]
    master=RUNTIME_PROOF/"proof_480p24.mp4"; master.parent.mkdir(parents=True,exist_ok=True)
    filters=[]; labels=[]
    for index in range(len(clips)):
        filters.append(f"[{index}:v]scale=848:480:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[v{index}]"); labels.append(f"[v{index}]")
    filters.append("".join(labels)+f"concat=n={len(clips)}:v=1:a=0,format=yuv420p[vout]")
    command=["ffmpeg","-y","-v","error"]
    for clip in clips: command += ["-i",str(clip)]
    command += ["-filter_complex",";".join(filters),"-map","[vout]","-an","-r",str(FPS),"-c:v","libx264","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart",str(master)]
    subprocess.run(command,check=True)
    probe=probe_video(master)
    if (probe["width"],probe["height"],probe["frames"])!=(848,480,432): raise RuntimeError(f"Proof assembly failed: {probe}")
    digest=atomic_publish_file(master,deliverables/master.name)
    accepted_hashes={segment["id"]:accepted_candidate(DRIVE_PROOF,segment)[1]["manifest_file_sha256"] for segment in SEGMENTS}
    atomic_write_json(PROOF_GATE,{"status":"passed","config_fingerprint":CONFIG_FINGERPRINT,"master_sha256":digest,
                                  "accepted_manifest_hashes":accepted_hashes,"frames":432,"fps":24,"duration_seconds":18.0,
                                  "license":"local evaluation only"})

display(Video(str(DRIVE_PROOF/"deliverables"/"proof_480p24.mp4"),embed=True,width=848))
print("Proof persisted:",DRIVE_PROOF/"deliverables"/"proof_480p24.mp4")
print("APPROVAL SHA-256:",proof_gate_record()["master_sha256"])
print("If the complete route looks right, paste that exact value into the next cell. Production never reuses proof pixels.")
'''


APPROVAL = r'''
# Human visual gate, cryptographically bound to the exact persisted proof shown above.
APPROVED_PROOF_SHA256 = ""  # @param {type:"string"}
PROOF_APPROVAL = DRIVE_PROOF / "approval.json"

def proof_approval_valid():
    if not proof_gate_valid() or not PROOF_APPROVAL.is_file(): return False
    try:
        gate=proof_gate_record(); approval=json.loads(PROOF_APPROVAL.read_text())
        return (approval.get("status")=="approved" and approval.get("config_fingerprint")==CONFIG_FINGERPRINT
                and approval.get("proof_master_sha256")==gate["master_sha256"])
    except Exception: return False

gate=proof_gate_record()
if gate is None:
    print("Run the proof cell first.")
elif APPROVED_PROOF_SHA256.strip():
    if APPROVED_PROOF_SHA256.strip()!=gate["master_sha256"]:
        raise RuntimeError("Approval hash does not match the current persisted proof")
    atomic_write_json(PROOF_APPROVAL,{"status":"approved","config_fingerprint":CONFIG_FINGERPRINT,
                                      "proof_master_sha256":gate["master_sha256"],"approved_at_unix":time.time()})
    print("Approved exact proof:",gate["master_sha256"])
else:
    print("Production locked. Review the proof and paste its APPROVAL SHA-256 above.")
'''


PRODUCTION = r'''
# Native 720p production. Runs only after the persisted proof passes and is approved.
PRODUCTION_UNLOCKED = proof_approval_valid()

if not PRODUCTION_UNLOCKED:
    print("Production remains locked. Approve the exact proof in the preceding cell, then rerun from here.")
else:
    all_complete=all(accepted_candidate(DRIVE_PRODUCTION,segment) is not None for segment in SEGMENTS)
    production_pipe=None; production_model_dir=None; production_complete=False
    if not all_complete:
        production_model_dir=acquire_model(PRODUCTION_MODEL,"production")
        production_pipe=load_hunyuan(production_model_dir,PRODUCTION_MODEL,"production")
    try:
        for segment in SEGMENTS:
            existing=accepted_candidate(DRIVE_PRODUCTION,segment)
            if existing:
                print("Production segment restored:",segment["id"],existing[0]); continue
            passing=[]
            for seed in segment["seeds"][:MAX_PRODUCTION_CANDIDATES]:
                ok,reason,manifest=validate_candidate(DRIVE_PRODUCTION,segment,seed,"production",1280,720)
                if not ok:
                    print("Generating production",segment["id"],"seed",seed)
                    manifest=render_segment(production_pipe,DRIVE_PRODUCTION,RUNTIME_PRODUCTION,segment,seed,"production")
                print(segment["id"],seed,json.dumps(manifest["metrics"],indent=2))
                if manifest["metrics"]["usable"]:
                    passing.append((manifest["metrics"]["score"],seed,manifest))
                    if manifest["metrics"]["hard_pass"]: break
            if not passing:
                for seed in segment["seeds"][:MAX_PRODUCTION_CANDIDATES]:
                    sheet=candidate_dir(DRIVE_PRODUCTION,segment,seed,"production")/"contact_sheet.jpg"
                    if sheet.is_file(): display(Image.open(sheet))
                raise RuntimeError(f"No production candidate passed for {segment['id']}")
            _,seed,manifest=max(passing,key=lambda item:item[0])
            accept_candidate(DRIVE_PRODUCTION,segment,seed,manifest,"production")
            display(Image.open(candidate_dir(DRIVE_PRODUCTION,segment,seed,"production")/"contact_sheet.jpg"))
            print("Accepted",segment["id"],seed)
        production_complete=True
    finally:
        dispose_pipeline(production_pipe)
        production_pipe=None
        if production_complete and production_model_dir is not None: purge_runtime_model(production_model_dir)
'''


ASSEMBLY = r'''
# Assemble exact 18-second evaluation masters, scrub encode, diagnostics, manifest, and QA ZIP.
if not PRODUCTION_UNLOCKED:
    print("Assembly skipped because production is locked.")
elif not all(accepted_candidate(DRIVE_PRODUCTION,segment) is not None for segment in SEGMENTS):
    print("Assembly skipped because production is incomplete.")
else:
    final_dir=DRIVE_PRODUCTION/"deliverables"; final_dir.mkdir(parents=True,exist_ok=True)
    assembly=RUNTIME_PRODUCTION/"assembly"
    if assembly.exists(): shutil.rmtree(assembly)
    assembly.mkdir(parents=True)
    clips=[restore_accepted(DRIVE_PRODUCTION,segment["id"],"clip.mp4") for segment in SEGMENTS]
    filters=[]; labels=[]
    for index in range(len(clips)):
        filters.append(f"[{index}:v]scale=1280:720:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[v{index}]"); labels.append(f"[v{index}]")
    filters.append("".join(labels)+f"concat=n={len(clips)}:v=1:a=0,format=yuv420p[vout]")
    master720=assembly/"intro_hunyuan15_eval_720p24.mp4"
    command=["ffmpeg","-y","-v","error"]
    for clip in clips: command += ["-i",str(clip)]
    command += ["-filter_complex",";".join(filters),"-map","[vout]","-an","-r",str(FPS),"-c:v","libx264","-preset","slow","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart",str(master720)]
    subprocess.run(command,check=True)
    p720=probe_video(master720)
    if (p720["width"],p720["height"],p720["frames"])!=(1280,720,432) or abs(p720["fps"]-24)>.01 or abs(p720["duration"]-18)>.05: raise RuntimeError(p720)

    master1080=assembly/"intro_hunyuan15_eval_1080p24.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(master720),"-vf","scale=1920:1080:flags=lanczos","-an","-c:v","libx264","-preset","slow","-crf","16","-pix_fmt","yuv420p","-movflags","+faststart",str(master1080)],check=True)
    p1080=probe_video(master1080)
    if ((p1080["width"],p1080["height"],p1080["frames"])!=(1920,1080,432)
            or abs(p1080["fps"]-24)>.01 or abs(p1080["duration"]-18)>.05): raise RuntimeError(p1080)

    scrub=assembly/"intro_hunyuan15_eval_scrub_1080p24.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(master1080),"-an","-c:v","libx264","-preset","slow","-crf","17","-pix_fmt","yuv420p",
                    "-g","6","-keyint_min","6","-sc_threshold","0","-bf","0","-tune","fastdecode","-movflags","+faststart",str(scrub)],check=True)
    pscrub=probe_video(scrub); keygap=maximum_keyframe_gap(scrub)
    if ((pscrub["width"],pscrub["height"],pscrub["frames"])!=(1920,1080,432)
            or abs(pscrub["fps"]-24)>.01 or abs(pscrub["duration"]-18)>.05 or keygap>6):
        raise RuntimeError({"probe":pscrub,"keyframe_gap":keygap})

    pingpong=assembly/"intro_hunyuan15_eval_bidirectional-proof.mp4"
    subprocess.run(["ffmpeg","-y","-v","error","-i",str(master720),"-filter_complex",
                    "[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[fwd];[r]reverse,setpts=PTS-STARTPTS[rev];[fwd][rev]concat=n=2:v=1:a=0,format=yuv420p[vout]",
                    "-map","[vout]","-an","-r","24","-c:v","libx264","-crf","17","-pix_fmt","yuv420p","-movflags","+faststart",str(pingpong)],check=True)
    ppingpong=probe_video(pingpong)
    if ((ppingpong["width"],ppingpong["height"],ppingpong["frames"])!=(1280,720,864)
            or abs(ppingpong["fps"]-24)>.01 or abs(ppingpong["duration"]-36)>.05): raise RuntimeError(ppingpong)

    def decode_frame(path,index):
        result=subprocess.run(["ffmpeg","-v","error","-i",str(path),"-vf",f"select=eq(n\\,{index})","-frames:v","1","-f","image2pipe","-vcodec","png","-"],check=True,capture_output=True)
        return np.asarray(Image.open(io.BytesIO(result.stdout)).convert("RGB"))

    seams=[]
    for previous,following in zip(SEGMENTS,SEGMENTS[1:]):
        left=decode_frame(restore_accepted(DRIVE_PRODUCTION,previous["id"],"clip.mp4"),previous["display_frames"]-1)
        right=decode_frame(restore_accepted(DRIVE_PRODUCTION,following["id"],"clip.mp4"),0)
        seams.append({"previous":previous["id"],"following":following["id"],"mae":float(np.abs(left.astype(float)-right.astype(float)).mean()),"left":left,"right":right})
    diagnostic=Image.new("RGB",(1280,len(seams)*210),"#111111"); draw=ImageDraw.Draw(diagnostic)
    for row,seam in enumerate(seams):
        y=row*210; diagnostic.paste(Image.fromarray(seam["left"]).resize((640,180)),(0,y)); diagnostic.paste(Image.fromarray(seam["right"]).resize((640,180)),(640,y))
        draw.text((8,y+184),seam["previous"]+" final",fill="white"); draw.text((648,y+184),seam["following"]+f" first | MAE {seam['mae']:.2f}",fill="white")
    diagnostic_path=assembly/"seam_diagnostic.png"; diagnostic.save(diagnostic_path)

    timeline=Image.new("RGB",(960,412),"#111111"); tdraw=ImageDraw.Draw(timeline)
    for index,segment in enumerate(SEGMENTS):
        frame=decode_frame(restore_accepted(DRIVE_PRODUCTION,segment["id"],"clip.mp4"),segment["display_frames"]//2)
        x=(index%3)*320; y=(index//3)*206; timeline.paste(Image.fromarray(frame).resize((320,180)),(x,y)); tdraw.text((x+8,y+184),segment["id"],fill="white")
    timeline_path=assembly/"accepted_timeline.jpg"; timeline.save(timeline_path,"JPEG",quality=91)

    seam_failures=[seam for seam in seams if seam["mae"]>45]
    qa={"status":"failed" if seam_failures else "passed","master_720p":p720,"master_1080p":p1080,
        "scrub_1080p":{**pscrub,"maximum_keyframe_gap":keygap},"bidirectional_proof":ppingpong,
        "seams":[{key:value for key,value in seam.items() if key not in {"left","right"}} for seam in seams],"license":"local evaluation only"}
    qa_path=assembly/"qa-report.json"; qa_path.write_text(json.dumps(qa,indent=2)+"\n")

    if seam_failures:
        for path in (diagnostic_path,timeline_path,qa_path): atomic_publish_file(path,final_dir/path.name)
        raise RuntimeError({"seam_threshold":45,"failed_seams":[(s["previous"],s["following"],s["mae"]) for s in seam_failures],
                            "diagnostics":str(final_dir)})

    deliverables={}
    for path in (master720,master1080,scrub,pingpong,diagnostic_path,timeline_path,qa_path):
        digest=atomic_publish_file(path,final_dir/path.name); deliverables[path.name]={"bytes":path.stat().st_size,"sha256":digest}
    manifest={"status":"complete","publication_status":"blocked_pending_license_review","run_id":PRODUCTION_RUN_ID,
              "config_fingerprint":CONFIG_FINGERPRINT,"frames":432,"fps":24,"duration_seconds":18.0,
              "model":PRODUCTION_MODEL,"approved_proof_sha256":proof_gate_record()["master_sha256"],
              "caption_timeline":CAPTION_TIMELINE,"website_recommended_video":scrub.name,
              "deliverables":deliverables,"accepted":[json.loads(accepted_pointer(DRIVE_PRODUCTION,s["id"]).read_text()) for s in SEGMENTS],
              "license_warning":"Tencent HunyuanVideo 1.5 Outputs are not cleared here for unrestricted display in the EU, UK, or South Korea."}
    manifest_path=assembly/"production_manifest.json"; manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    atomic_publish_file(manifest_path,final_dir/manifest_path.name)

    bundle=assembly/"hunyuan15_final_qa.zip"
    with zipfile.ZipFile(bundle,"w",compression=zipfile.ZIP_DEFLATED) as archive:
        for path in (*[assembly/name for name in deliverables],manifest_path): archive.write(path,arcname=path.name)
    with zipfile.ZipFile(bundle) as archive:
        if archive.testzip() is not None: raise RuntimeError("Final ZIP integrity failed")
    atomic_publish_file(bundle,final_dir/bundle.name)
    print("Published evaluation package:",final_dir)
    display(timeline); display(diagnostic)
'''


PLAYBACK = r'''
# Playback and persistent paths.
from IPython.display import Video, display
final_dir=DRIVE_PRODUCTION/"deliverables"
master=final_dir/"intro_hunyuan15_eval_720p24.mp4"
if master.is_file():
    display(Video(str(master),embed=True,width=960))
    print("QA ZIP:",final_dir/"hunyuan15_final_qa.zip")
    print("Deployment remains blocked pending Tencent license review.")
else:
    print("No final master yet. Approve the proof and complete production first.")
'''


DOWNLOAD = r'''
# Optional browser download; Drive remains the durable source of truth.
from google.colab import files
bundle=DRIVE_PRODUCTION/"deliverables"/"hunyuan15_final_qa.zip"
if bundle.is_file(): files.download(str(bundle))
else: print("QA ZIP not available yet.")
'''


def code(source: str):
    return nbformat.v4.new_code_cell(source.strip() + "\n")


def build_notebook():
    anchors_json = json.dumps(build_anchors(), separators=(",", ":"), sort_keys=True)
    anchor_cell = ANCHORS_TEMPLATE.replace("__ANCHORS_JSON__", anchors_json)
    cells = [
        nbformat.v4.new_markdown_cell(TITLE.strip() + "\n"),
        code(SETTINGS), code(DRIVE_SETUP), code(anchor_cell), code(PREFLIGHT), code(INSTALL),
        code(CONFIG), code(UTILITIES), code(PROOF), code(APPROVAL), code(PRODUCTION), code(ASSEMBLY), code(PLAYBACK), code(DOWNLOAD),
    ]
    notebook = nbformat.v4.new_notebook(cells=cells)
    notebook.metadata.update({"kernelspec":{"display_name":"Python 3","language":"python","name":"python3"},
                              "language_info":{"name":"python","version":"3.x"},
                              "colab":{"gpuType":"A100","provenance":[]}})
    return notebook


def audit(notebook):
    nbformat.validate(notebook)
    joined="\n".join(cell.source for cell in notebook.cells)
    for index,cell in enumerate(notebook.cells):
        if cell.cell_type=="code":
            ast.parse(cell.source,filename=f"hunyuan-cell-{index}")
            if cell.outputs or cell.execution_count is not None: raise AssertionError(f"Output leaked into cell {index}")
    required=(
        "HunyuanVideo15ImageToVideoPipeline", PROOF_REPO, PRODUCTION_REPO, PROOF_REVISION, PRODUCTION_REVISION,
        "sum(segment[\"display_frames\"] for segment in SEGMENTS) != 432", "APPROVED_PROOF_SHA256",
        "proof_gate_valid", "reverse_anchor", "stanford_memorial_church", "stanford_main_quad_arcade",
        "intro_hunyuan15_eval_scrub_1080p24.mp4", "hunyuan15_final_qa.zip", "blocked_pending_license_review",
        "Personal_Website_HunyuanVideo15", "Personal_Website_SkyReelsV2", "set_attention_backend(\"flash_varlen_hub\")",
    )
    for marker in required:
        if marker not in joined: raise AssertionError(marker)
    for forbidden in ("OPENAI_API_KEY","DASHSCOPE_API_KEY","intro_cinematic_14b_a10080_v1"):
        if forbidden in joined: raise AssertionError(forbidden)
    for pattern in (r"sk-[A-Za-z0-9_-]{20,}",r"hf_[A-Za-z0-9]{20,}",r"AIza[A-Za-z0-9_-]{20,}"):
        if re.search(pattern,joined): raise AssertionError("Credential found")


def synthetic_smoke_test():
    """Exercise slicing, exact assembly, scrub GOP, lineage hashing, and ZIP integrity without a model."""
    import fractions
    import subprocess
    import tempfile
    import zipfile

    import numpy as np

    display_counts = [72, 72, 60, 72, 72, 84]
    request_counts = [73, 73, 61, 73, 73, 85]
    policies = ["forward_anchor", "forward_parent", "forward_parent", "reverse_anchor", "forward_parent", "reverse_anchor"]
    sliced = []
    for display_count, request_count, policy in zip(display_counts, request_counts, policies):
        raw = list(range(request_count))
        if policy == "forward_anchor": frames = raw[:display_count]
        elif policy == "forward_parent": frames = raw[1 : 1 + display_count]
        else: frames = list(reversed(raw))[1 : 1 + display_count]
        if len(frames) != display_count: raise AssertionError((policy, len(frames), display_count))
        sliced.append(frames)
    if sum(map(len, sliced)) != 432: raise AssertionError("Synthetic route is not 432 frames")

    base = {"config": "c", "profile": "production", "segment": "S1", "seed": 1}
    first = hashlib.sha256(json.dumps({**base, "parent": "parent-a"}, sort_keys=True).encode()).hexdigest()
    second = hashlib.sha256(json.dumps({**base, "parent": "parent-b"}, sort_keys=True).encode()).hexdigest()
    if first == second: raise AssertionError("Parent lineage did not invalidate the child fingerprint")

    def probe(path):
        result = subprocess.run(
            ["ffprobe", "-count_frames", "-v", "error", "-select_streams", "v:0", "-show_entries",
             "stream=width,height,avg_frame_rate,nb_read_frames", "-of", "json", str(path)],
            check=True, capture_output=True, text=True,
        )
        stream = json.loads(result.stdout)["streams"][0]
        return int(stream["nb_read_frames"]), float(fractions.Fraction(stream["avg_frame_rate"]))

    with tempfile.TemporaryDirectory(prefix="hunyuan15-smoke-") as directory:
        root = Path(directory); clips = []
        for clip_index, frame_count in enumerate(display_counts):
            path = root / f"s{clip_index}.mp4"; clips.append(path)
            command = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s:v", "48x32",
                       "-r", "24", "-i", "-", "-an", "-c:v", "libx264", "-crf", "28", "-pix_fmt", "yuv420p", str(path)]
            process = subprocess.Popen(command, stdin=subprocess.PIPE)
            for frame_index in range(frame_count):
                frame = np.zeros((32, 48, 3), dtype=np.uint8)
                frame[:, :, 0] = (clip_index * 37 + frame_index) % 256
                frame[:, :, 1] = (frame_index * 3) % 256
                process.stdin.write(frame.tobytes())
            process.stdin.close()
            if process.wait() != 0: raise AssertionError("Synthetic segment encoding failed")

        master = root / "master.mp4"
        command = ["ffmpeg", "-y", "-v", "error"]
        for clip in clips: command += ["-i", str(clip)]
        labels = "".join(f"[{index}:v]" for index in range(len(clips)))
        command += ["-filter_complex", labels + f"concat=n={len(clips)}:v=1:a=0[v]", "-map", "[v]", "-r", "24",
                    "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(master)]
        subprocess.run(command, check=True)
        if probe(master) != (432, 24.0): raise AssertionError(("master", probe(master)))

        scrub = root / "scrub.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(master), "-an", "-c:v", "libx264", "-g", "6",
                        "-keyint_min", "6", "-sc_threshold", "0", "-bf", "0", "-pix_fmt", "yuv420p", str(scrub)], check=True)
        frames = json.loads(subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "frame=key_frame", "-of", "json", str(scrub)],
            check=True, capture_output=True, text=True,
        ).stdout)["frames"]
        keys = [index for index, frame in enumerate(frames) if int(frame["key_frame"])]
        gaps = [right - left for left, right in zip(keys, keys[1:])] + [len(frames) - keys[-1]]
        if not keys or keys[0] != 0 or max(gaps) > 6: raise AssertionError(("scrub-gop", max(gaps)))

        pingpong = root / "pingpong.mp4"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(master), "-filter_complex",
                        "[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[a];[r]reverse,setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1:a=0[v]",
                        "-map", "[v]", "-r", "24", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(pingpong)], check=True)
        if probe(pingpong) != (864, 24.0): raise AssertionError(("pingpong", probe(pingpong)))

        bundle = root / "bundle.zip"
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(master, arcname=master.name); archive.write(scrub, arcname=scrub.name)
        with zipfile.ZipFile(bundle) as archive:
            if archive.testzip() is not None: raise AssertionError("Synthetic ZIP integrity failed")


def main():
    notebook=build_notebook(); audit(notebook); synthetic_smoke_test(); OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    nbformat.write(notebook,OUTPUT)
    print("synthetic smoke test: passed")
    print(OUTPUT); print("sha256",hashlib.sha256(OUTPUT.read_bytes()).hexdigest()); print("bytes",OUTPUT.stat().st_size)


if __name__ == "__main__":
    main()
