#!/usr/bin/env python3
"""Build v2 of the HK-to-Stanford bridge using a reversed Stanford exit."""

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

import build_wan21_hk_stanford_bridge_colab as v1


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "wan21_hk_to_stanford_reverse_exit_v2_colab.ipynb"
SKY_ASSET = ROOT / "web" / "public" / "media" / "depth" / "shared-sky.webp"
SKY_BYTES = SKY_ASSET.read_bytes()
SKY_SHA256 = hashlib.sha256(SKY_BYTES).hexdigest()
SKY_B64 = base64.b64encode(SKY_BYTES).decode("ascii")


TITLE = r'''
# Hong Kong → Stanford bridge v2 — matched exits, reversed Stanford arrival

Version 1 is rejected: Hong Kong was hidden by a rising fog bank, Stanford
materialized from the sky, and the handoff nearly froze. This notebook tests a
different construction while preserving all approved source footage.

Wan generates two movements in the direction it handles more reliably:

1. **Hong Kong → textured sky:** the rigid skyline must travel downward and
   leave through the lower boundary while sky enters only from above.
2. **Stanford → the same sky:** Memorial Church and the arcade must also travel
   downward and leave through the lower boundary.

The second generated shot is then reversed, producing sky → Stanford with the
campus physically entering from below. Reversal occurs only in an environment
without people or dialogue and is disclosed in the manifest. It is not a
crossfade or landmark morph.

The clean sky endpoint is embedded from the existing website asset, so there is
no manual upload or fragile reference download. Long low-motion endpoint runs
are compressed to a brief apex before the accepted uniform-synthetic RIFE 4.26
pass is applied once across the assembled timeline. Native and final outputs
persist; model caches do not. Colab disconnects on success, error, or cutoff.

Run all cells on a Colab **A100 80 GB High-RAM** runtime.
'''


SETTINGS = r'''
EXPERIMENT_ID = "hk_to_stanford_reverse_exit_wan21_v2"

WIDTH, HEIGHT = 1280, 720
WAN_FRAMES = 81
NATIVE_FPS = 16
OUTPUT_FPS = 32
INFERENCE_STEPS = 50
GUIDANCE_SCALE = 5.5

# Each 81-frame generation is retimed to about two seconds. Endpoint holds are
# compressed before retiming, rather than allowed to stall the shared apex.
RETIME_FRAMES_PER_HALF = 33
APEX_KEEP_FRAMES = 2
TRAILING_HOLD_FLOW_THRESHOLD = 0.10
HK_CONTEXT_SECONDS = 1.5
SEEDS = {"A_hk_to_sky": 74211, "B_stanford_to_sky": 74247}

RUN_RIFE_POSTPROCESS = True
SHARPEN_AMOUNT = 0.14
SHARPEN_SIGMA = 0.85
PERSIST_MODEL_CACHE_TO_DRIVE = False

# Motion diagnostics are advisory: visual review remains the acceptance gate.
# This avoids wasting another run because a generic optical-flow threshold was
# mistaken for aesthetic judgment.
AUTO_REJECT_ON_PHYSICAL_DIAGNOSTIC = False

AUTO_DISCONNECT_ON_SUCCESS = True
AUTO_DISCONNECT_ON_ERROR = True
HARD_CUTOFF_HOURS = 4.0

if (WAN_FRAMES - 1) % 4:
    raise ValueError("Wan requires 4n+1 frames")
if (WIDTH, HEIGHT, WAN_FRAMES, NATIVE_FPS) != (1280, 720, 81, 16):
    raise ValueError("This proof is locked to Wan FLF2V's native contract")
if RETIME_FRAMES_PER_HALF < 25 or RETIME_FRAMES_PER_HALF > WAN_FRAMES:
    raise ValueError("Bridge retime is outside the reviewed range")
if APEX_KEEP_FRAMES not in (1, 2, 3):
    raise ValueError("Apex hold must remain brief")
if OUTPUT_FPS != 2 * NATIVE_FPS:
    raise ValueError("Uniform-synthetic postprocess requires exact 2x output")

print("Experiment:", EXPERIMENT_ID)
print("Retimed bridge duration:", round(2 * RETIME_FRAMES_PER_HALF / NATIVE_FPS, 3), "seconds")
'''


SOURCES = rf'''
# Resolve approved source clips from Drive; decode the clean sky from the
# notebook itself. No manual upload and no network reference request.
import base64, io

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
        "Could not find persisted SkyReels S1 seed 42211 under "
        "/content/drive/MyDrive/Personal_Website_SkyReelsV2/runs/*/stages/"
        "S1_tower_flight/candidates/42211/clip.mp4"
    )
HK_SOURCE_VIDEO = hk_matches[0]

STANFORD_SOURCE_VIDEO = (
    WAN_ROOT / "experiments" / "stanford_wan21_flf2v_whip_720p_v2" /
    "postprocess" / "stabilized_film32_whip_v3" / "02_post_stabilization_720p16.mp4"
)
if not STANFORD_SOURCE_VIDEO.is_file():
    raise RuntimeError(f"Missing approved original Stanford source: {{STANFORD_SOURCE_VIDEO}}")

hk_probe = probe_video(HK_SOURCE_VIDEO)
stanford_probe = probe_video(STANFORD_SOURCE_VIDEO)
if (hk_probe["width"], hk_probe["height"], round(hk_probe["fps"]), hk_probe["frames"]) != (1280, 720, 24, 48):
    raise RuntimeError(f"Unexpected Hong Kong source contract: {{hk_probe}}")
if (stanford_probe["width"], stanford_probe["height"], round(stanford_probe["fps"]), stanford_probe["frames"]) != (1280, 720, 16, 81):
    raise RuntimeError(f"Unexpected Stanford source contract: {{stanford_probe}}")

hk_frames_bgr = decode_bgr(HK_SOURCE_VIDEO)
stanford_frames_bgr = decode_bgr(STANFORD_SOURCE_VIDEO)
hk_endpoint_rgb = cv2.cvtColor(hk_frames_bgr[-1], cv2.COLOR_BGR2RGB)
stanford_endpoint_rgb = cv2.cvtColor(stanford_frames_bgr[0], cv2.COLOR_BGR2RGB)

SKY_WEBP_SHA256 = "{SKY_SHA256}"
sky_payload = base64.b64decode("{SKY_B64}")
if hashlib.sha256(sky_payload).hexdigest() != SKY_WEBP_SHA256:
    raise RuntimeError("Embedded shared-sky asset failed its hash check")
sky_image = Image.open(io.BytesIO(sky_payload)).convert("RGB")
sky_endpoint = ImageOps.fit(
    sky_image, (WIDTH, HEIGHT), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5)
)

ENDPOINTS = {{
    "hk": Image.fromarray(hk_endpoint_rgb),
    "sky": sky_endpoint,
    "stanford": Image.fromarray(stanford_endpoint_rgb),
}}

source_records = {{}}
for role, image in ENDPOINTS.items():
    local = RUNTIME_INPUTS / f"{{role}}_endpoint_1280x720.png"
    image.save(local, "PNG", optimize=True)
    digest = atomic_publish(local, DRIVE_INPUTS / local.name)
    source_records[role] = {{"path": str(DRIVE_INPUTS / local.name), "sha256": digest}}

source_records["embedded_sky_source"] = {{
    "original_workspace_path": "web/public/media/depth/shared-sky.webp",
    "embedded_webp_sha256": SKY_WEBP_SHA256,
    "derivation": "architecture-free crop of the existing Hong Kong wide source",
}}
source_records["hk_source_video"] = {{
    "path": str(HK_SOURCE_VIDEO), "sha256": sha256_file(HK_SOURCE_VIDEO), "probe": hk_probe,
}}
source_records["stanford_source_video"] = {{
    "path": str(STANFORD_SOURCE_VIDEO), "sha256": sha256_file(STANFORD_SOURCE_VIDEO), "probe": stanford_probe,
}}
atomic_write_json(DRIVE_INPUTS / "source_provenance.json", source_records)

endpoint_sheet = Image.new("RGB", (1280, 480), "#111111")
for column, role in enumerate(("hk", "sky", "stanford")):
    panel = ENDPOINTS[role].resize((426, 240), Image.Resampling.LANCZOS)
    endpoint_sheet.paste(panel, (column * 426, 0))
draw = ImageDraw.Draw(endpoint_sheet)
draw.text((12, 258), "Both locations generate forward toward the same clean sky.", fill="white")
draw.text((12, 292), "The Stanford exit is reversed only after generation to create a physical arrival.", fill="white")
endpoint_sheet_path = RUNTIME_INPUTS / "v2_matched_exit_endpoint_sheet.jpg"
endpoint_sheet.save(endpoint_sheet_path, "JPEG", quality=94, optimize=True)
atomic_publish(endpoint_sheet_path, DRIVE_INPUTS / endpoint_sheet_path.name)

print("Hong Kong:", HK_SOURCE_VIDEO)
print("Stanford:", STANFORD_SOURCE_VIDEO)
print("Embedded clean sky sha256:", SKY_WEBP_SHA256)
display(endpoint_sheet)
'''


CONFIG = rf'''
MODEL = {{
    "repo_id": "{v1.MODEL_ID}", "revision": "{v1.MODEL_REVISION}",
    "expected_snapshot_gib": 83.93, "license": "Apache-2.0",
}}

PROMPTS = {{
    "A_hk_to_sky": (
        "照片级写实香港航拍，严格延续给定香港终止画面，同一个连续镜头。固定24毫米电影镜头，真实三维摄影机运动。"
        "摄影机立即沿现有方向快速向前，同时强烈但平滑地抬头约九十度并垂直爬升。必须遵守明确几何规则：海港地平线、山脉、"
        "所有摩天楼和前景楼顶始终作为刚性物体连续向画面下方移动，最后从下边缘完全离开；新的蓝金色天空只能从画面上边缘进入。"
        "绝对不能有云、雾、烟或白色遮挡物从下方升起并盖住城市。建筑必须保持清晰可见，直到它们真正穿过下边缘。"
        "中段是快速有冲击力的无人机式抬头爬升，具有强烈向下视差和自然方向性运动模糊，但画面中不能出现无人机。"
        "终点是给定的有纹理蓝金色薄云天空；摄影机到达终点仍有轻微向前运动，不要长时间静止。"
    ),
    "B_stanford_to_sky": (
        "照片级写实斯坦福校园，严格从给定纪念教堂和主方院拱廊画面开始，同一个连续镜头。固定24毫米电影镜头。"
        "先短暂保持教堂清晰，然后摄影机沿真实弧形轨迹快速向后上方爬升并强烈向上俯仰。必须遵守明确几何规则：砂岩拱门、柱子、"
        "教堂、树冠和地面始终作为刚性物体连续向画面下方移动，并从下边缘完全离开；同一个有纹理蓝金色天空只能从上边缘进入。"
        "绝对不能让云、雾、烟或亮色遮挡物从下方升起盖住校园，也不能让建筑溶解或变成天空。近柱、教堂、树冠具有不同的真实视差。"
        "中段快速有冲击力，路径稳定，有自然方向性运动模糊。终点精确落在给定的共享天空，仍有轻微向上运动，不要长时间静止。"
    ),
}}

NEGATIVE_PROMPT = (
    "交叉淡化，溶解，透明建筑，建筑变形，云朵变成建筑，建筑变成云，传送门，白色闪光，隐藏剪辑，跳切，"
    "从画面下方升起的云，从下方升起的雾，前景雾墙，烟雾遮挡，云层遮住城市，云层遮住教堂，照片平移，照片旋转，"
    "数码变焦，静止天空，长时间停顿，匀速移动，手持抖动，逐帧闪烁，弯曲柱子，重复拱门，"
    "无人机，四旋翼，螺旋桨，摄影设备，人物特写，卡通，插画，文字，字幕，标志，水印"
)

STABLE_CONFIG = {{
    "experiment_id": EXPERIMENT_ID, "model": MODEL, "seeds": SEEDS,
    "width": WIDTH, "height": HEIGHT, "wan_frames": WAN_FRAMES,
    "native_fps": NATIVE_FPS, "steps": INFERENCE_STEPS,
    "guidance_scale": GUIDANCE_SCALE, "prompts": PROMPTS,
    "negative_prompt": NEGATIVE_PROMPT,
    "bridge": "HK exits downward -> shared sky apex <- Stanford exits downward; reverse Stanford exit",
    "shared_sky_sha256": "{SKY_SHA256}",
    "stanford_exit_reversed_for_arrival": True,
    "crossfade": False, "forced_endpoint_pixels": False,
    "typography_baked_into_video": False,
}}
CONFIG_FINGERPRINT = hashlib.sha256(
    json.dumps(STABLE_CONFIG, sort_keys=True, separators=(",", ":")).encode()
).hexdigest()
atomic_write_json(DRIVE_EXPERIMENT / "generation_config.json", STABLE_CONFIG)
print("Configuration:", CONFIG_FINGERPRINT)
'''


PHYSICAL_DIAGNOSTICS = r'''
def physical_exit_diagnostics(frames_rgb):
    small = [
        cv2.resize(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR), (320, 180), interpolation=cv2.INTER_AREA)
        for frame in frames_rgb
    ]
    tracked_dy = []
    flow_magnitudes = []
    bottom_fog_scores = []

    for left, right in zip(small, small[1:]):
        gray0 = cv2.cvtColor(left, cv2.COLOR_BGR2GRAY)
        gray1 = cv2.cvtColor(right, cv2.COLOR_BGR2GRAY)
        mask = np.zeros_like(gray0)
        mask[:153] = 255
        points = cv2.goodFeaturesToTrack(
            gray0, maxCorners=220, qualityLevel=0.01, minDistance=4, mask=mask
        )
        if points is not None:
            following, status, errors = cv2.calcOpticalFlowPyrLK(
                gray0, gray1, points, None, winSize=(15, 15), maxLevel=2
            )
            good = (status[:, 0] == 1) & (errors[:, 0] < 25)
            if int(good.sum()) > 5:
                tracked_dy.extend((following[good] - points[good])[:, 0, 1].tolist())

        dense = cv2.calcOpticalFlowFarneback(gray0, gray1, None, .5, 3, 15, 3, 5, 1.1, 0)
        flow_magnitudes.append(float(np.median(np.linalg.norm(dense, axis=2))))

    # A foreground fog wall is bright, low-saturation, and low-edge in the
    # bottom third while structured architecture remains in the middle third.
    for frame in small:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 130)
        bottom_fog = (gray[120:] > 165) & (hsv[120:, :, 1] < 55) & (edges[120:] == 0)
        middle_structure = float(np.mean(edges[60:120] > 0))
        bottom_fog_scores.append(float(np.mean(bottom_fog)) * min(1.0, middle_structure / 0.08))

    tracked = np.asarray(tracked_dy, dtype=np.float32)
    median_dy = float(np.median(tracked)) if tracked.size else 0.0
    downward_fraction = float(np.mean(tracked > 0.08)) if tracked.size else 0.0
    fog_peak = float(np.max(bottom_fog_scores)) if bottom_fog_scores else 1.0
    trailing_flow = float(np.median(flow_magnitudes[-16:]))
    diagnostic_pass = (
        tracked.size >= 500 and median_dy > 0.20 and downward_fraction > 0.55 and fog_peak < 0.42
    )
    return {
        "tracked_feature_count": int(tracked.size),
        "median_tracked_vertical_displacement": median_dy,
        "downward_track_fraction": downward_fraction,
        "foreground_fog_score_peak": fog_peak,
        "trailing_flow": trailing_flow,
        "physical_exit_diagnostic_pass": bool(diagnostic_pass),
        "diagnostic_is_aesthetic_approval": False,
    }
'''


def make_generate() -> str:
    source = v1.GENERATE.replace("B_sky_to_stanford", "B_stanford_to_sky")
    source = source.replace(
        'valid_segment("B_stanford_to_sky", image_sha(a_natural_last), stanford_sha)',
        'valid_segment("B_stanford_to_sky", stanford_sha, image_sha(a_natural_last))',
    )
    source = source.replace(
        'generate_one("B_stanford_to_sky", a_natural_last, ENDPOINTS["stanford"])',
        'generate_one("B_stanford_to_sky", ENDPOINTS["stanford"], a_natural_last)',
    )
    source = source.replace(
        'print("Generating B_stanford_to_sky from A\'s natural final sky frame...")',
        'print("Generating Stanford-to-sky exit toward A\'s natural final sky frame...")',
    )
    source = source.replace(
        '        "automatic_aesthetic_rejection": False,\n    }',
        '        "automatic_aesthetic_rejection": False,\n    }\n'
        '    metrics.update(physical_exit_diagnostics(frames))\n'
        '    if AUTO_REJECT_ON_PHYSICAL_DIAGNOSTIC and not metrics["physical_exit_diagnostic_pass"]:\n'
        '        print("PHYSICAL DIAGNOSTIC WARNING:", segment_id, metrics)\n',
    )
    return source


GENERATE = make_generate()


ASSEMBLE = r'''
# Assemble forward HK exit followed by the reversed Stanford exit. No generated
# endpoint is overwritten and no opacity blend is introduced.
a_frames_bgr = decode_bgr(segment_dir("A_hk_to_sky") / "clip_720p16.mp4")
b_forward_frames_bgr = decode_bgr(segment_dir("B_stanford_to_sky") / "clip_720p16.mp4")
if len(a_frames_bgr) != WAN_FRAMES or len(b_forward_frames_bgr) != WAN_FRAMES:
    raise RuntimeError("A persisted v2 segment has the wrong frame count")

def frame_flow_magnitudes(frames):
    values = []
    for left, right in zip(frames, frames[1:]):
        a = cv2.cvtColor(cv2.resize(left, (320, 180)), cv2.COLOR_BGR2GRAY)
        b = cv2.cvtColor(cv2.resize(right, (320, 180)), cv2.COLOR_BGR2GRAY)
        flow = cv2.calcOpticalFlowFarneback(a, b, None, .5, 3, 15, 3, 5, 1.1, 0)
        values.append(float(np.median(np.linalg.norm(flow, axis=2))))
    return values

def compress_trailing_hold(frames):
    flows = frame_flow_magnitudes(frames)
    run = 0
    for value in reversed(flows):
        if value < TRAILING_HOLD_FLOW_THRESHOLD:
            run += 1
        else:
            break
    hold_start = max(1, len(frames) - run - 1)
    if run <= APEX_KEEP_FRAMES or hold_start + APEX_KEEP_FRAMES >= len(frames):
        return [frame.copy() for frame in frames], list(range(len(frames))), run

    prefix_indices = list(range(hold_start + 1))
    tail_indices = np.linspace(
        hold_start + 1, len(frames) - 1, APEX_KEEP_FRAMES
    ).round().astype(int).tolist()
    indices = prefix_indices + [index for index in tail_indices if index > prefix_indices[-1]]
    if indices[-1] != len(frames) - 1:
        indices.append(len(frames) - 1)
    compressed = [frames[index].copy() for index in indices]
    return compressed, indices, run

a_compressed, a_compressed_indices, a_hold_run = compress_trailing_hold(a_frames_bgr)
b_compressed_forward, b_compressed_indices, b_hold_run = compress_trailing_hold(b_forward_frames_bgr)
if min(len(a_compressed), len(b_compressed_forward)) < RETIME_FRAMES_PER_HALF:
    raise RuntimeError("Hold compression left too few frames for the locked retime")

a_retimed, a_retime_local_indices = exact_retime(a_compressed, RETIME_FRAMES_PER_HALF)
b_retimed_forward, b_retime_local_indices = exact_retime(b_compressed_forward, RETIME_FRAMES_PER_HALF)
b_retimed = [frame.copy() for frame in reversed(b_retimed_forward)]

hk_context_count = round(HK_CONTEXT_SECONDS * NATIVE_FPS)
hk_source_count = round(HK_CONTEXT_SECONDS * hk_probe["fps"])
hk_tail_source = hk_frames_bgr[-hk_source_count:]
hk_tail, hk_indices = exact_retime(hk_tail_source, hk_context_count)

assembled_native_frames = [*hk_tail, *a_retimed, *b_retimed, *stanford_frames_bgr]
SEAMS_NATIVE = {
    "hk_to_A": len(hk_tail),
    "A_to_reversed_B": len(hk_tail) + len(a_retimed),
    "reversed_B_to_stanford": len(hk_tail) + len(a_retimed) + len(b_retimed),
}

NATIVE_PROOF = RUNTIME_OUTPUT / "01_native_reverse_exit_assembled_720p16.mp4"
encode_bgr(assembled_native_frames, NATIVE_FPS, NATIVE_PROOF, crf=12, gop=16)
native_probe = probe_video(NATIVE_PROOF)
expected_native_frames = hk_context_count + 2 * RETIME_FRAMES_PER_HALF + 81
if (native_probe["width"], native_probe["height"], round(native_probe["fps"]), native_probe["frames"]) != (
    WIDTH, HEIGHT, NATIVE_FPS, expected_native_frames,
):
    raise RuntimeError(f"Native v2 assembly contract failed: {native_probe}")

native_digest = atomic_publish(NATIVE_PROOF, DRIVE_OUTPUT / NATIVE_PROOF.name)
atomic_write_json(DRIVE_OUTPUT / "native_assembly.json", {
    "status": "complete", "sha256": native_digest, "probe": native_probe,
    "seams_native": SEAMS_NATIVE, "hk_source_indices": hk_indices,
    "A_compressed_source_indices": a_compressed_indices,
    "B_forward_compressed_source_indices": b_compressed_indices,
    "A_trailing_low_motion_run": a_hold_run,
    "B_forward_trailing_low_motion_run": b_hold_run,
    "stanford_exit_reversed_for_arrival": True,
    "crossfade": False, "forced_endpoint_pixels": False,
})
print("A trailing low-motion run:", a_hold_run, "frames")
print("Stanford-exit trailing low-motion run:", b_hold_run, "frames")
print("Persisted native reverse-exit proof:", DRIVE_OUTPUT / NATIVE_PROOF.name)
display(Video(str(NATIVE_PROOF), embed=True, width=960))
'''


def make_postprocess() -> str:
    source = v1.POSTPROCESS.replace("B_sky_to_stanford", "B_stanford_to_sky")
    source = source.replace(
        '"HK → sky → Stanford → approved arcade | final 32 fps proof"',
        '"HK exit → shared sky → reversed Stanford exit → approved arcade | v2 final"',
    )
    source = source.replace(
        '"next_gate": "Eric reviews the crane-up, cloud continuity, crest-and-dive, and Stanford landing",',
        '"next_gate": "Eric verifies both forward exits are physical and the reversed Stanford arrival reads naturally",',
    )
    source = source.replace(
        '"Hong Kong-to-Stanford bridge proof completed and persisted"',
        '"Reverse-exit Hong Kong-to-Stanford v2 completed and persisted"',
    )
    return source


POSTPROCESS = make_postprocess()


def code(source: str) -> nbformat.NotebookNode:
    return nbformat.v4.new_code_cell(source.strip() + "\n")


def build_notebook() -> nbformat.NotebookNode:
    notebook = nbformat.v4.new_notebook(cells=[
        nbformat.v4.new_markdown_cell(TITLE.strip() + "\n"),
        code(SETTINGS), code(v1.SETUP), code(v1.PREFLIGHT_AND_INSTALL), code(v1.UTILITIES),
        code(SOURCES), code(CONFIG), code(PHYSICAL_DIAGNOSTICS), code(GENERATE),
        code(ASSEMBLE), code(v1.RIFE_CONFIG), code(v1.RIFE_SETUP), code(POSTPROCESS),
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
            ast.parse(cell.source, filename=f"reverse-exit-v2-cell-{index}")
            if cell.outputs or cell.execution_count is not None:
                raise AssertionError(f"Notebook output leaked into cell {index}")

    required = (
        v1.MODEL_ID, v1.MODEL_REVISION, v1.DIFFUSERS_COMMIT,
        "S1_tower_flight/candidates/42211/clip.mp4",
        "B_stanford_to_sky", "b_forward_frames_bgr", "reversed(b_retimed_forward)",
        SKY_SHA256, "base64.b64decode", "shared-sky.webp",
        "新的蓝金色天空只能从画面上边缘进入",
        "同一个有纹理蓝金色天空只能从上边缘进入",
        "从下方升起的雾", "physical_exit_diagnostics",
        "foreground_fog_score_peak", "compress_trailing_hold",
        '"stanford_exit_reversed_for_arrival": True',
        '"crossfade": False', '"forced_endpoint_pixels": False',
        "fraction in (0.25, 0.75)", "03_uniform_synthetic_scroll_gop4_720p32.mp4",
        "PERSIST_MODEL_CACHE_TO_DRIVE = False", "colab_runtime.unassign()",
    )
    for marker in required:
        if marker not in joined:
            raise AssertionError(f"Missing marker: {marker}")

    forbidden = (
        "B_sky_to_stanford", "crossfade=d", "xfade=", "OPENAI_API_KEY",
        "PERSIST_MODEL_CACHE_TO_DRIVE = True", "frames[0] =", "frames[-1] =",
        "raw_frames[0] =", "raw_frames[-1] =",
    )
    for marker in forbidden:
        if marker in joined:
            raise AssertionError(f"Forbidden marker: {marker}")
    for pattern in (r"sk-[A-Za-z0-9_-]{20,}", r"hf_[A-Za-z0-9]{20,}", r"AIza[A-Za-z0-9_-]{20,}"):
        if re.search(pattern, joined):
            raise AssertionError("Credential found in notebook")
    if len(json.dumps(notebook)) > 360_000:
        raise AssertionError("Notebook is large enough to risk Colab editor instability")


def synthetic_smoke_test() -> None:
    """Verify the v2 frame/duration contract, GOP-4 stream, and bundle."""
    import numpy as np

    native_count = round(1.5 * 16) + 2 * 33 + 81
    frames = []
    for index in range(2 * native_count):
        frame = np.zeros((72, 128, 3), dtype=np.uint8)
        frame[:, :, 0] = (index * 5) % 256
        frame[:, :, 1] = np.arange(128, dtype=np.uint8)[None, :]
        frames.append(frame)

    with tempfile.TemporaryDirectory(prefix="reverse-exit-v2-smoke-") as directory:
        root = Path(directory)
        video = root / "final.mp4"
        command = [
            "ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
            "-s", "128x72", "-r", "32", "-i", "-", "-an", "-c:v", "libx264",
            "-crf", "28", "-g", "4", "-keyint_min", "4", "-sc_threshold", "0",
            "-bf", "0", "-pix_fmt", "yuv420p", str(video),
        ]
        process = subprocess.Popen(command, stdin=subprocess.PIPE)
        for frame in frames:
            process.stdin.write(frame.tobytes())
        process.stdin.close()
        if process.wait() != 0:
            raise AssertionError("Synthetic encode failed")

        payload = json.loads(subprocess.run([
            "ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
            "-show_entries", "stream=nb_read_frames,avg_frame_rate,duration", "-of", "json", str(video),
        ], check=True, capture_output=True, text=True).stdout)["streams"][0]
        if int(payload["nb_read_frames"]) != 2 * native_count or payload["avg_frame_rate"] != "32/1":
            raise AssertionError("Synthetic v2 frame contract failed")
        if abs(float(payload["duration"]) - native_count / 16) > 1e-6:
            raise AssertionError("Synthetic v2 duration changed")

        bundle = root / "review.zip"
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.write(video, video.name)
        with zipfile.ZipFile(bundle) as archive:
            if archive.testzip() is not None:
                raise AssertionError("Synthetic v2 bundle failed")


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
