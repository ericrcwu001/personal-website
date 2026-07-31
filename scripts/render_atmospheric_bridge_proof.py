#!/usr/bin/env python3
"""Render a neutral atmospheric-bridge motion proof.

This deliberately tests continuity, not final architecture or materials. The
geometry is source-shaped proxy massing for Hong Kong and Stanford; landmark
surface work remains governed by the reconstruction source audit.
"""

from __future__ import annotations

import csv
import math
import subprocess
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output" / "proofs" / "atmospheric-bridge"
OUT.mkdir(parents=True, exist_ok=True)

WIDTH, HEIGHT = 1280, 720
FPS = 30
FRAME_COUNT = 210
DURATION = FRAME_COUNT / FPS

VIDEO_PATH = OUT / "atmospheric_bridge_proxy_proof.mp4"
CONTACT_PATH = OUT / "atmospheric_bridge_keyframes.jpg"
CSV_PATH = OUT / "atmospheric_bridge_diagnostics.csv"
REPORT_PATH = OUT / "report.md"

FONT = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    x = clamp((value - edge0) / (edge1 - edge0))
    return x * x * (3.0 - 2.0 * x)


def smootherstep(edge0: float, edge1: float, value: float) -> float:
    x = clamp((value - edge0) / (edge1 - edge0))
    return x * x * x * (x * (x * 6.0 - 15.0) + 10.0)


def mix(a: float, b: float, amount: float) -> float:
    return a + (b - a) * amount


def mix_color(a, b, amount: float):
    return tuple(int(round(mix(a[i], b[i], amount))) for i in range(3))


@dataclass
class Mesh:
    vertices: np.ndarray
    faces: list[tuple[int, ...]]
    color: tuple[int, int, int]
    name: str = "mesh"


def box(cx, y0, cz, width, height, depth, color, name="box") -> Mesh:
    x0, x1 = cx - width / 2, cx + width / 2
    y1 = y0 + height
    z0, z1 = cz - depth / 2, cz + depth / 2
    vertices = np.array(
        [
            [x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0],
            [x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1],
        ],
        dtype=np.float32,
    )
    faces = [
        (0, 1, 2, 3), (1, 5, 6, 2), (5, 4, 7, 6),
        (4, 0, 3, 7), (3, 2, 6, 7),
    ]
    return Mesh(vertices, faces, color, name)


def triangular_prism(cx, y0, cz, width, height, depth, color, name="pediment") -> Mesh:
    x0, x1 = cx - width / 2, cx + width / 2
    z0, z1 = cz - depth / 2, cz + depth / 2
    vertices = np.array(
        [
            [x0, y0, z0], [x1, y0, z0], [cx, y0 + height, z0],
            [x0, y0, z1], [x1, y0, z1], [cx, y0 + height, z1],
        ],
        dtype=np.float32,
    )
    faces = [(0, 1, 2), (1, 4, 5, 2), (4, 3, 5), (3, 0, 2, 5)]
    return Mesh(vertices, faces, color, name)


def cylinder(cx, y0, cz, radius, height, color, sides=10, name="column") -> Mesh:
    vertices = []
    for y in (y0, y0 + height):
        for i in range(sides):
            angle = 2 * math.pi * i / sides
            vertices.append([cx + radius * math.cos(angle), y, cz + radius * math.sin(angle)])
    faces = []
    for i in range(sides):
        j = (i + 1) % sides
        faces.append((i, j, sides + j, sides + i))
    faces.append(tuple(range(sides, sides * 2)))
    return Mesh(np.asarray(vertices, dtype=np.float32), faces, color, name)


def hong_kong_scene() -> list[Mesh]:
    rng = np.random.default_rng(231)
    meshes: list[Mesh] = []

    # Victoria Harbour and the dense Central/Kowloon massing.
    meshes.append(box(0, -0.7, 56, 70, 0.25, 50, (91, 116, 128), "harbour"))
    for index in range(92):
        depth = float(rng.uniform(24, 66))
        x = float(rng.uniform(-28, 28))
        width = float(rng.uniform(0.55, 1.8))
        height = float(rng.uniform(1.8, 7.4) * (1.12 - 0.004 * depth))
        base = int(rng.uniform(104, 145))
        color = (base, base + int(rng.uniform(-3, 8)), base + int(rng.uniform(3, 15)))
        meshes.append(box(x, 0, depth, width, height, width * 0.75, color, f"hk_{index}"))

    # Two IFC and Bank of China Tower remain simple identifiable massing anchors.
    meshes.append(box(3.7, 0, 34, 2.05, 16.8, 1.9, (130, 151, 157), "two_ifc"))
    meshes.append(box(8.2, 0, 38, 2.15, 13.0, 2.0, (105, 121, 132), "bank_of_china"))
    meshes.append(triangular_prism(8.2, 13.0, 38, 2.15, 1.9, 2.0, (105, 121, 132), "boc_crown"))
    return meshes


def stanford_scene() -> list[Mesh]:
    sandstone = (151, 137, 119)
    sandstone_light = (170, 153, 130)
    dark = (76, 70, 64)
    meshes: list[Mesh] = []
    meshes.append(box(0, -0.45, 42, 52, 0.35, 56, (119, 115, 104), "quad_ground"))

    # Memorial Church: nave mass, facade, and pediment.
    meshes.append(box(4.5, 0, 44, 13.2, 7.8, 4.5, sandstone, "church_facade"))
    meshes.append(triangular_prism(4.5, 7.8, 42.0, 13.2, 5.0, 1.2, sandstone_light, "church_pediment"))
    meshes.append(box(4.5, 0.1, 41.6, 3.0, 4.7, 0.4, dark, "central_arch"))
    meshes.append(box(0.0, 0.1, 41.6, 1.55, 3.2, 0.35, dark, "left_arch"))
    meshes.append(box(9.0, 0.1, 41.6, 1.55, 3.2, 0.35, dark, "right_arch"))

    # Main Quad arcade leading the camera toward Stanford B.
    for index, z in enumerate(np.linspace(16, 52, 15)):
        radius = 0.27
        meshes.append(cylinder(-10.2, 0, float(z), radius, 4.0, sandstone_light, name=f"column_l_{index}"))
        meshes.append(cylinder(-14.4, 0, float(z), radius, 4.0, sandstone, name=f"column_r_{index}"))
        meshes.append(box(-12.3, 3.8, float(z), 4.8, 0.55, 0.65, sandstone, name=f"arch_beam_{index}"))
    meshes.append(box(-12.3, 4.25, 34, 5.2, 0.7, 40, (95, 86, 77), "arcade_roof"))
    return meshes


HK_MESHES = hong_kong_scene()
STANFORD_MESHES = stanford_scene()


def make_cloud_field(width: int, height: int, seed: int = 2029) -> np.ndarray:
    rng = np.random.default_rng(seed)
    field = np.zeros((height, width), dtype=np.float32)
    for cell, weight in ((18, 0.18), (42, 0.26), (96, 0.32), (180, 0.24)):
        small_h = max(2, height // cell)
        small_w = max(2, width // cell)
        noise = rng.random((small_h, small_w), dtype=np.float32)
        layer = cv2.resize(noise, (width, height), interpolation=cv2.INTER_CUBIC)
        layer = cv2.GaussianBlur(layer, (0, 0), max(2, cell / 9))
        field += layer * weight
    field = cv2.normalize(field, None, 0.0, 1.0, cv2.NORM_MINMAX)
    return field


def make_wisp_field(width: int, height: int, seed: int = 2031) -> np.ndarray:
    rng = np.random.default_rng(seed)
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    for _ in range(34):
        x = float(rng.uniform(-120, width + 120))
        y = float(rng.uniform(height * 0.16, height * 0.70))
        rx = float(rng.uniform(90, 260))
        ry = float(rng.uniform(18, 54))
        alpha = int(rng.uniform(55, 145))
        draw.ellipse((x - rx, y - ry, x + rx, y + ry), fill=alpha)
    mask = mask.filter(ImageFilter.GaussianBlur(24))
    return np.asarray(mask, dtype=np.float32) / 255.0


CLOUD_FIELD = make_cloud_field(WIDTH + 760, HEIGHT + 220)
CLOUD_FIELD_NEAR = make_cloud_field(WIDTH + 920, HEIGHT + 260, seed=2030)
WISP_FIELD = make_wisp_field(WIDTH + 1120, HEIGHT + 280)
PARTICLE_RNG = np.random.default_rng(29)
PARTICLES = np.column_stack(
    (
        PARTICLE_RNG.uniform(0, WIDTH + 220, 180),
        PARTICLE_RNG.uniform(100, HEIGHT * 0.78, 180),
        PARTICLE_RNG.uniform(0.7, 2.8, 180),
        PARTICLE_RNG.uniform(0.25, 0.82, 180),
    )
)


def sky_frame(t: float, pitch_deg: float, bridge_density: float) -> np.ndarray:
    top = np.array([93, 132, 159], dtype=np.float32)
    mid = np.array([176, 184, 178], dtype=np.float32)
    bottom = np.array([226, 183, 132], dtype=np.float32)
    y = np.linspace(0, 1, HEIGHT, dtype=np.float32)[:, None]
    upper = top[None, :] * (1 - np.clip(y * 2, 0, 1)) + mid[None, :] * np.clip(y * 2, 0, 1)
    lower_amount = np.clip((y - 0.5) * 2, 0, 1)
    gradient = upper * (1 - lower_amount) + bottom[None, :] * lower_amount
    image = np.repeat(gradient[:, None, :], WIDTH, axis=1)

    shift_x = int(round(420 * t))
    shift_y = int(round(38 + pitch_deg * 2.8))
    cloud = CLOUD_FIELD[shift_y : shift_y + HEIGHT, shift_x : shift_x + WIDTH]
    vertical = np.exp(-((np.arange(HEIGHT)[:, None] - HEIGHT * 0.37) / (HEIGHT * 0.24)) ** 2)
    cloud_alpha = np.clip((cloud - 0.47) * 2.3, 0, 0.72) * vertical
    cloud_alpha *= 0.52 + 0.38 * bridge_density
    cloud_color = np.array([238, 224, 203], dtype=np.float32)
    image = image * (1 - cloud_alpha[..., None]) + cloud_color * cloud_alpha[..., None]

    # A faster, softer cloud layer creates visible depth during the zero-landmark
    # center instead of allowing the geometry change to read as a crossfade.
    near_shift_x = int(round(650 * t))
    near_shift_y = int(round(58 + pitch_deg * 3.2))
    near_cloud = CLOUD_FIELD_NEAR[
        near_shift_y : near_shift_y + HEIGHT,
        near_shift_x : near_shift_x + WIDTH,
    ]
    near_vertical = np.exp(-((np.arange(HEIGHT)[:, None] - HEIGHT * 0.48) / (HEIGHT * 0.31)) ** 2)
    near_alpha = np.clip((near_cloud - 0.50) * 1.9, 0, 0.42) * near_vertical * bridge_density
    near_color = np.array([230, 209, 183], dtype=np.float32)
    image = image * (1 - near_alpha[..., None]) + near_color * near_alpha[..., None]

    # Long, soft cloud wisps are the strongest persistent motion cue. Their
    # several-pixel-per-frame travel makes the bridge read as camera movement.
    wisp_shift_x = int(round(760 * t))
    wisp_shift_y = int(round(42 + pitch_deg * 2.1))
    wisps = WISP_FIELD[
        wisp_shift_y : wisp_shift_y + HEIGHT,
        wisp_shift_x : wisp_shift_x + WIDTH,
    ]
    wisp_vertical = np.exp(-((np.arange(HEIGHT)[:, None] - HEIGHT * 0.43) / (HEIGHT * 0.30)) ** 2)
    wisp_alpha = wisps * wisp_vertical * (0.12 + 0.52 * bridge_density)
    wisp_color = np.array([241, 222, 194], dtype=np.float32)
    image = image * (1 - wisp_alpha[..., None]) + wisp_color * wisp_alpha[..., None]

    # The sun moves only as a consequence of the continuous pitch curve.
    sun_x = int(WIDTH * 0.78 - 120 * t)
    sun_y = int(HEIGHT * 0.27 + pitch_deg * 3.1)
    yy, xx = np.ogrid[:HEIGHT, :WIDTH]
    distance = np.sqrt((xx - sun_x) ** 2 + (yy - sun_y) ** 2)
    bloom = np.clip(1 - distance / 118, 0, 1) ** 2
    core = np.clip(1 - distance / 28, 0, 1) ** 1.4
    image = image * (1 - bloom[..., None] * 0.18) + np.array([250, 218, 169]) * bloom[..., None] * 0.18
    image = image * (1 - core[..., None] * 0.30) + np.array([255, 235, 193]) * core[..., None] * 0.30
    return np.clip(image, 0, 255).astype(np.uint8)


def transform_vertices(vertices: np.ndarray, camera, yaw: float, pitch: float):
    relative = vertices - np.asarray(camera, dtype=np.float32)
    cy, sy = math.cos(yaw), math.sin(yaw)
    x1 = cy * relative[:, 0] - sy * relative[:, 2]
    z1 = sy * relative[:, 0] + cy * relative[:, 2]
    cp, sp = math.cos(pitch), math.sin(pitch)
    y2 = cp * relative[:, 1] - sp * z1
    z2 = sp * relative[:, 1] + cp * z1
    return np.column_stack((x1, y2, z2))


def render_meshes(image: np.ndarray, meshes: list[Mesh], camera, yaw, pitch, focal, visibility, bridge_density):
    if visibility <= 0.0001:
        return image
    draw_items = []
    light = np.array([-0.45, 0.72, -0.52], dtype=np.float32)
    light /= np.linalg.norm(light)
    haze_color = np.array([205, 190, 169], dtype=np.float32)

    for mesh in meshes:
        view = transform_vertices(mesh.vertices, camera, yaw, pitch)
        for face in mesh.faces:
            points = view[list(face)]
            if np.any(points[:, 2] <= 0.2):
                continue
            screen = np.column_stack(
                (
                    WIDTH / 2 + focal * points[:, 0] / points[:, 2],
                    HEIGHT / 2 - focal * points[:, 1] / points[:, 2],
                )
            )
            if screen[:, 0].max() < -40 or screen[:, 0].min() > WIDTH + 40:
                continue
            if screen[:, 1].max() < -40 or screen[:, 1].min() > HEIGHT + 40:
                continue
            normal = np.cross(points[1] - points[0], points[2] - points[0])
            norm = np.linalg.norm(normal)
            shade = 0.78
            if norm > 1e-6:
                normal /= norm
                shade = 0.68 + 0.32 * abs(float(np.dot(normal, light)))
            depth = float(points[:, 2].mean())
            distance_fog = 1.0 - math.exp(-depth * (0.006 + bridge_density * 0.045))
            transmittance = visibility * (1.0 - distance_fog)
            if transmittance < 0.006:
                continue
            base = np.asarray(mesh.color, dtype=np.float32) * shade
            color = np.clip(base * (1 - distance_fog) + haze_color * distance_fog, 0, 255)
            alpha = int(255 * clamp(transmittance))
            draw_items.append((depth, screen.astype(np.int32), tuple(int(v) for v in color), alpha))

    overlay = np.zeros((HEIGHT, WIDTH, 4), dtype=np.uint8)
    for _, polygon, color, alpha in sorted(draw_items, key=lambda item: item[0], reverse=True):
        cv2.fillPoly(overlay, [polygon], (*color, alpha), lineType=cv2.LINE_AA)

    alpha = overlay[..., 3:4].astype(np.float32) / 255.0
    return np.clip(image.astype(np.float32) * (1 - alpha) + overlay[..., :3].astype(np.float32) * alpha, 0, 255).astype(np.uint8)


def draw_foliage(
    image: np.ndarray,
    t: float,
    hk_visibility: float,
    stanford_visibility: float,
    vertical_frame_offset_px: float,
):
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    rng = np.random.default_rng(771)
    hk_alpha = int(190 * hk_visibility)
    if hk_alpha > 2:
        for _ in range(46):
            x = WIDTH * 0.90 + rng.normal(0, 118) - t * 320
            y = HEIGHT * 0.14 + rng.normal(0, 92) + vertical_frame_offset_px
            radius = rng.uniform(12, 38)
            color = (29, 43, 34, hk_alpha)
            draw.ellipse((x - radius, y - radius * 0.62, x + radius, y + radius * 0.62), fill=color)

    stan_alpha = int(205 * stanford_visibility)
    if stan_alpha > 2:
        for side in (-1, 1):
            for _ in range(38):
                anchor = WIDTH * (0.18 if side < 0 else 0.88)
                x = anchor + rng.normal(0, 115) - (t - 0.55) * 350
                y = HEIGHT * 0.10 + rng.normal(0, 82) + vertical_frame_offset_px
                radius = rng.uniform(14, 42)
                color = (35, 47, 33, stan_alpha)
                draw.ellipse((x - radius, y - radius * 0.60, x + radius, y + radius * 0.60), fill=color)

    result = Image.alpha_composite(Image.fromarray(image).convert("RGBA"), overlay)
    return np.asarray(result.convert("RGB"))


def draw_particles(image: np.ndarray, t: float, bridge_density: float, pitch_deg: float):
    if bridge_density < 0.05:
        return image
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    for x0, y0, radius, strength in PARTICLES:
        x = (x0 - 420 * t) % (WIDTH + 220) - 110
        y = y0 + pitch_deg * 1.7
        alpha = int(145 * strength * bridge_density)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=(242, 223, 196, alpha))
    result = Image.alpha_composite(Image.fromarray(image).convert("RGBA"), overlay)
    return np.asarray(result.convert("RGB"))


def add_atmospheric_depth(image: np.ndarray, bridge_density: float):
    if bridge_density <= 0:
        return image
    haze = np.full_like(image, (218, 198, 171))
    alpha = 0.08 + bridge_density * 0.24
    return cv2.addWeighted(image, 1 - alpha, haze, alpha, 0)


def frame_parameters(t: float):
    # The environment swap is hidden at the sky-filled apex. Neither scene
    # dissolves: each remains fully opaque until camera motion has carried it
    # outside the frame, and the incoming scene begins fully opaque below it.
    hk_visibility = 1.0 if t < 0.46 else 0.0
    stanford_visibility = 1.0 if t >= 0.56 else 0.0
    fog_in = smootherstep(0.16, 0.46, t)
    fog_out = 1.0 - smootherstep(0.56, 0.86, t)
    bridge_density = min(fog_in, fog_out)

    # A single crane-and-tilt arc carries Hong Kong below the frame, holds a
    # short sky-only apex, then reverses so Stanford rises naturally from below.
    # The local scene origin changes only while the infinite sky is the sole view.
    vertical_arc = (
        smootherstep(0.02, 0.46, t)
        - smootherstep(0.54, 0.98, t)
    )
    camera_pan = mix(-4.0, 7.5, t)
    camera_forward = mix(-3.0, 3.0, t)
    camera_lift = 11.0 * vertical_arc
    pitch_deg = 26.0 * vertical_arc
    # Foreground canopy has stronger parallax than distant architecture. This
    # guarantees that it crosses the lower frame edge before the hidden swap,
    # rather than popping off at the scene boundary.
    vertical_frame_offset_px = 930.0 * vertical_arc
    lens_px = 930.0
    sun_x = WIDTH * 0.78 - 120 * t
    sun_y = HEIGHT * 0.27 + pitch_deg * 3.1
    return {
        "hk_visibility": hk_visibility,
        "stanford_visibility": stanford_visibility,
        "bridge_density": bridge_density,
        "camera_pan": camera_pan,
        "camera_forward": camera_forward,
        "camera_lift": camera_lift,
        "vertical_frame_offset_px": vertical_frame_offset_px,
        "pitch_deg": pitch_deg,
        "lens_px": lens_px,
        "sun_x": sun_x,
        "sun_y": sun_y,
    }


def render_frame(t: float) -> tuple[np.ndarray, dict]:
    params = frame_parameters(t)
    pitch = math.radians(params["pitch_deg"])
    yaw = math.radians(-1.8 + 3.6 * t)
    image = sky_frame(t, params["pitch_deg"], params["bridge_density"])

    if params["hk_visibility"] > 0.0001:
        hk_camera = (
            params["camera_pan"],
            7.1 + params["camera_lift"],
            params["camera_forward"],
        )
        image = render_meshes(
            image, HK_MESHES, hk_camera, yaw, pitch, params["lens_px"],
            params["hk_visibility"], params["bridge_density"],
        )

    if params["stanford_visibility"] > 0.0001:
        stanford_camera = (
            params["camera_pan"] - 4.0,
            2.35 + params["camera_lift"],
            params["camera_forward"],
        )
        image = render_meshes(
            image, STANFORD_MESHES, stanford_camera, yaw, pitch,
            params["lens_px"], params["stanford_visibility"], params["bridge_density"],
        )

    image = draw_foliage(
        image,
        t,
        params["hk_visibility"],
        params["stanford_visibility"],
        params["vertical_frame_offset_px"],
    )
    image = add_atmospheric_depth(image, params["bridge_density"])
    image = draw_particles(image, t, params["bridge_density"], params["pitch_deg"])

    # Subtle filmic contrast without an exposure flash.
    pil = Image.fromarray(image)
    pil = ImageEnhance.Contrast(pil).enhance(1.035)
    pil = ImageEnhance.Color(pil).enhance(0.84)
    return np.asarray(pil), params


def make_contact_sheet(frames: list[tuple[float, Image.Image]], output: Path):
    thumb_w, thumb_h = 512, 288
    margin, gap, label_h = 42, 24, 44
    cols = 2
    rows = math.ceil(len(frames) / cols)
    canvas_w = margin * 2 + cols * thumb_w + (cols - 1) * gap
    canvas_h = 132 + rows * (thumb_h + label_h + gap) + margin
    canvas = Image.new("RGB", (canvas_w, canvas_h), (15, 15, 14))
    draw = ImageDraw.Draw(canvas)
    title_font = ImageFont.truetype(FONT_BOLD, 30)
    label_font = ImageFont.truetype(FONT, 17)
    draw.text((margin, 34), "Atmospheric bridge proxy proof", font=title_font, fill=(238, 232, 222))
    draw.text((margin, 78), "Neutral proxy geometry. Camera and atmosphere only.", font=label_font, fill=(161, 155, 145))
    labels = [
        "Hong Kong geometry visible",
        "Crane rise carries Hong Kong downward",
        "Hong Kong has physically exited below frame",
        "Sky-filled apex hides the location change",
        "Stanford rises naturally from below",
        "Memorial Church landing composition",
    ]
    for index, (t, frame) in enumerate(frames):
        row, col = divmod(index, cols)
        x = margin + col * (thumb_w + gap)
        y = 132 + row * (thumb_h + label_h + gap)
        thumb = frame.resize((thumb_w, thumb_h), Image.Resampling.LANCZOS)
        canvas.paste(thumb, (x, y))
        draw.text((x, y + thumb_h + 10), f"{labels[index]}   t={t:.2f}", font=label_font, fill=(238, 232, 222))
    canvas.save(output, quality=94)


def main():
    ffmpeg = [
        "/opt/homebrew/bin/ffmpeg", "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}",
        "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264",
        "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(VIDEO_PATH),
    ]
    process = subprocess.Popen(ffmpeg, stdin=subprocess.PIPE)
    rows = []
    key_times = [0.06, 0.30, 0.47, 0.52, 0.72, 0.94]
    key_frames: dict[float, Image.Image] = {}

    for frame_index in range(FRAME_COUNT):
        t = frame_index / (FRAME_COUNT - 1)
        frame, params = render_frame(t)
        if process.stdin is None:
            raise RuntimeError("ffmpeg stdin is unavailable")
        process.stdin.write(frame.tobytes())
        rows.append({"frame": frame_index, "time_seconds": frame_index / FPS, "t": t, **params})
        for key_t in key_times:
            if key_t not in key_frames and t >= key_t:
                key_frames[key_t] = Image.fromarray(frame.copy())
        if frame_index % 30 == 0:
            print(f"Rendered {frame_index + 1}/{FRAME_COUNT}")

    process.stdin.close()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with {return_code}")

    with CSV_PATH.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    make_contact_sheet([(t, key_frames[t]) for t in key_times], CONTACT_PATH)

    hk = np.array([row["hk_visibility"] for row in rows])
    stanford = np.array([row["stanford_visibility"] for row in rows])
    pan = np.array([row["camera_pan"] for row in rows])
    lift = np.array([row["camera_lift"] for row in rows])
    pitch = np.array([row["pitch_deg"] for row in rows])
    lens = np.array([row["lens_px"] for row in rows])
    sun_x = np.array([row["sun_x"] for row in rows])
    sun_y = np.array([row["sun_y"] for row in rows])
    overlap = np.minimum(hk, stanford)
    zero_gap = np.where((hk < 1e-4) & (stanford < 1e-4))[0]
    pan_delta = np.diff(pan)

    checks = {
        "maximum_landmark_visibility_overlap": float(overlap.max()),
        "zero_landmark_gap_frames": int(len(zero_gap)),
        "camera_pan_delta_std": float(pan_delta.std()),
        "maximum_camera_lift": float(lift.max()),
        "maximum_lift_frame_jump": float(np.max(np.abs(np.diff(lift)))),
        "maximum_pitch_frame_jump_degrees": float(np.max(np.abs(np.diff(pitch)))),
        "maximum_lens_frame_jump_pixels": float(np.max(np.abs(np.diff(lens)))),
        "maximum_sun_frame_jump_pixels": float(np.max(np.hypot(np.diff(sun_x), np.diff(sun_y)))),
    }
    assert checks["maximum_landmark_visibility_overlap"] < 1e-6
    assert checks["zero_landmark_gap_frames"] >= 12
    assert checks["camera_pan_delta_std"] < 1e-8
    assert checks["maximum_lift_frame_jump"] < 0.24
    assert checks["maximum_pitch_frame_jump_degrees"] < 0.56
    assert checks["maximum_lens_frame_jump_pixels"] < 2.5
    assert checks["maximum_sun_frame_jump_pixels"] < 2.1

    capture = cv2.VideoCapture(str(VIDEO_PATH))
    decoded = []
    while True:
        ok, encoded_frame = capture.read()
        if not ok:
            break
        decoded.append(cv2.cvtColor(encoded_frame, cv2.COLOR_BGR2GRAY))
    capture.release()
    frame_differences = np.array(
        [np.mean(cv2.absdiff(decoded[index], decoded[index - 1])) for index in range(1, len(decoded))]
    )
    center_differences = frame_differences[int(0.40 * len(decoded)) : int(0.62 * len(decoded))]
    flow_x = []
    for index in range(int(0.40 * len(decoded)), int(0.62 * len(decoded)) - 1, 3):
        flow = cv2.calcOpticalFlowFarneback(
            decoded[index][:320], decoded[index + 1][:320], None,
            0.5, 3, 21, 3, 5, 1.2, 0,
        )
        magnitude = np.linalg.norm(flow, axis=2)
        moving = magnitude > 0.02
        flow_x.append(float(np.median(flow[..., 0][moving])) if np.any(moving) else 0.0)
    encoded_checks = {
        "decoded_frames": len(decoded),
        "center_difference_max": float(center_differences.max()),
        "center_to_global_p95": float(center_differences.max() / np.percentile(frame_differences, 95)),
        "median_center_sky_flow_x": float(np.median(flow_x)),
        "flow_direction_consistent": all(value <= 0 for value in flow_x) or all(value >= 0 for value in flow_x),
    }
    assert encoded_checks["decoded_frames"] == FRAME_COUNT
    assert encoded_checks["center_to_global_p95"] < 0.5
    assert encoded_checks["flow_direction_consistent"]

    report = f"""# Atmospheric bridge proxy proof report

Generated from neutral source-shaped proxy massing. This proof evaluates motion
and atmospheric continuity only; it is not an architectural or photorealism
approval.

## Outputs

- `atmospheric_bridge_proxy_proof.mp4`: {WIDTH}x{HEIGHT}, {FPS} fps, {DURATION:.1f} seconds
- `atmospheric_bridge_keyframes.jpg`: six diagnostic moments
- `atmospheric_bridge_diagnostics.csv`: per-frame continuity parameters

## Automated continuity checks

- Maximum Hong Kong/Stanford landmark visibility overlap: {checks['maximum_landmark_visibility_overlap']:.6f}
- Zero-landmark atmospheric center: {checks['zero_landmark_gap_frames']} frames
- Camera pan delta standard deviation: {checks['camera_pan_delta_std']:.10f}
- Total rightward camera travel: {pan[-1] - pan[0]:.4f} proxy world units
- Maximum vertical camera lift: {checks['maximum_camera_lift']:.4f} proxy world units
- Maximum vertical lift change per frame: {checks['maximum_lift_frame_jump']:.4f} proxy world units
- Maximum pitch change per frame: {checks['maximum_pitch_frame_jump_degrees']:.4f} degrees
- Maximum lens change per frame: {checks['maximum_lens_frame_jump_pixels']:.4f} pixels
- Maximum sun displacement per frame: {checks['maximum_sun_frame_jump_pixels']:.4f} pixels

Encoded-video validation:

- Decoded frame count: {encoded_checks['decoded_frames']}
- Maximum mean frame difference inside the atmospheric center: {encoded_checks['center_difference_max']:.4f}
- Atmospheric-center difference relative to the video's global 95th percentile: {encoded_checks['center_to_global_p95']:.4f}
- Median horizontal sky flow through the atmospheric center: {encoded_checks['median_center_sky_flow_x']:.4f} pixels/frame
- Median sky optical-flow direction remained consistent throughout the center: {encoded_checks['flow_direction_consistent']}

All automated continuity assertions passed. Creative approval still depends on
watching the video at normal speed, scrubbing through the atmospheric center,
and judging whether the transition feels continuous rather than effect-driven.

## Known limitation

The complete official reconstruction caches are not present on this Mac and
Blender is not installed. Hong Kong and Stanford are therefore neutral proxy
massing in this proof. The approved camera and atmosphere curves must next be
transferred to the authoritative Hong Kong geometry and Stanford reconstruction.
"""
    REPORT_PATH.write_text(report)
    print(VIDEO_PATH)
    print(CONTACT_PATH)
    print(REPORT_PATH)


if __name__ == "__main__":
    main()
