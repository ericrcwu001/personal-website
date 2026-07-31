"""Prepare camera-projection textures from the approved source plates.

The web experience mounts these textures on surfaces inside a unified 3D scene.
No source file is modified. Alpha masks are intentionally conservative and
camera-specific.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "prototype" / "intro-animatic" / "assets"
OUTPUT = ROOT / "web" / "public" / "media"
OUTPUT.mkdir(parents=True, exist_ok=True)


def cover_crop(image: Image.Image, size: tuple[int, int], focal=(0.5, 0.5)) -> Image.Image:
    target_w, target_h = size
    source_w, source_h = image.size
    scale = max(target_w / source_w, target_h / source_h)
    resized = image.resize(
        (round(source_w * scale), round(source_h * scale)),
        Image.Resampling.LANCZOS,
    )
    left = round((resized.width - target_w) * focal[0])
    top = round((resized.height - target_h) * focal[1])
    left = max(0, min(left, resized.width - target_w))
    top = max(0, min(top, resized.height - target_h))
    return resized.crop((left, top, left + target_w, top + target_h))


hong_kong = Image.open(SOURCE / "hong-kong-wide.png").convert("RGB")
hk_width, hk_height = hong_kong.size

# A clean persistent sky crop. The geometry layers move independently over it.
sky_crop = hong_kong.crop((0, 0, round(hk_width * 0.78), round(hk_height * 0.61)))
sky = cover_crop(sky_crop, (1920, 1080), focal=(0.46, 0.42))
sky = ImageEnhance.Color(sky).enhance(0.86)
sky = ImageEnhance.Contrast(sky).enhance(0.94)
sky.save(OUTPUT / "shared-golden-sky.jpg", quality=92, optimize=True)

# City and mountains share a feathered horizon so they can physically leave the
# viewport without carrying a rectangular sky plate with them.
city = hong_kong.convert("RGBA")
city_mask = Image.new("L", hong_kong.size, 0)
mask_array = np.zeros((hk_height, hk_width), dtype=np.float32)
start = int(hk_height * 0.49)
end = int(hk_height * 0.60)
for row in range(start, end):
    amount = (row - start) / max(1, end - start)
    mask_array[row, :] = 255 * amount * amount * (3 - 2 * amount)
mask_array[end:, :] = 255
city_mask = Image.fromarray(mask_array.astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(2.2))
city.putalpha(city_mask)
city.save(OUTPUT / "hong-kong-city.webp", "WEBP", quality=91, method=6)

# The Braemar branch becomes a close parallax layer.
pixels = np.asarray(hong_kong, dtype=np.int16)
brightness = pixels.sum(axis=2)
saturation = pixels.max(axis=2) - pixels.min(axis=2)
branch_region = np.zeros((hk_height, hk_width), dtype=bool)
branch_region[: int(hk_height * 0.63), int(hk_width * 0.66) :] = True
branch_strength = np.clip((475 - brightness) * 2.0 + saturation * 0.8, 0, 255)
branch_alpha = np.where(branch_region, branch_strength, 0).astype(np.uint8)
branch_alpha = np.asarray(
    Image.fromarray(branch_alpha, "L").filter(ImageFilter.GaussianBlur(0.9))
)
branch = hong_kong.convert("RGBA")
branch.putalpha(Image.fromarray(branch_alpha, "L"))
branch.save(OUTPUT / "hong-kong-foreground.webp", "WEBP", quality=90, method=6)

church_source = Image.open(SOURCE / "stanford-church.jpg").convert("RGB")
church_mask = Image.new("L", church_source.size, 0)
draw = ImageDraw.Draw(church_mask)
w, h = church_source.size
church_base = int(h * 0.84)

# Camera-specific silhouette for the facade, wings, and cross. The points sit
# just inside the real roof edge so the layer never carries a blue-sky halo
# into the shared atmosphere.
draw.polygon(
    [
        (int(w * 0.26), int(h * 0.49)),
        (int(w * 0.498), int(h * 0.148)),
        (int(w * 0.507), int(h * 0.148)),
        (int(w * 0.745), int(h * 0.49)),
        (int(w * 0.745), church_base),
        (int(w * 0.26), church_base),
    ],
    fill=255,
)
draw.polygon(
    [
        (0, int(h * 0.66)),
        (int(w * 0.26), int(h * 0.59)),
        (int(w * 0.745), int(h * 0.59)),
        (w, int(h * 0.66)),
        (w, church_base),
        (0, church_base),
    ],
    fill=255,
)
cross_x = int(w * 0.505)
draw.rounded_rectangle(
    (cross_x - 10, int(h * 0.055), cross_x + 10, int(h * 0.19)),
    radius=5,
    fill=255,
)
draw.rounded_rectangle(
    (cross_x - 39, int(h * 0.085), cross_x + 39, int(h * 0.115)),
    radius=6,
    fill=255,
)
church_mask = church_mask.filter(ImageFilter.GaussianBlur(0.8))
church = church_source.convert("RGBA")
church.putalpha(church_mask)
church.save(OUTPUT / "stanford-church-cutout.webp", "WEBP", quality=91, method=6)

arcade_source = Image.open(SOURCE / "stanford-arcade-long.jpg").convert("RGB")
aw, ah = arcade_source.size
arcade_source = arcade_source.crop((int(aw * 0.035), int(ah * 0.075), int(aw * 0.965), int(ah * 0.98)))
arcade = cover_crop(arcade_source, (1920, 1080), focal=(0.52, 0.47))
arcade_gray = ImageOps.autocontrast(arcade.convert("L"), cutoff=1)
arcade = ImageOps.colorize(arcade_gray, black="#171719", mid="#74685d", white="#dfc9a4")
arcade = ImageEnhance.Contrast(arcade).enhance(1.08)
arcade = ImageEnhance.Brightness(arcade).enhance(0.78)
arcade.save(OUTPUT / "stanford-arcade.webp", "WEBP", quality=91, method=6)

column_source = Image.open(SOURCE / "stanford-column-close.jpg").convert("RGB")
column = cover_crop(column_source, (900, 1600), focal=(0.48, 0.5)).convert("RGBA")
column_mask = Image.new("L", column.size, 0)
ImageDraw.Draw(column_mask).polygon(
    [(80, 0), (900, 0), (900, 1600), (0, 1600), (150, 1080)],
    fill=255,
)
column_mask = column_mask.filter(ImageFilter.GaussianBlur(1.0))
column.putalpha(column_mask)
column.save(OUTPUT / "stanford-column.webp", "WEBP", quality=90, method=6)

# A motivated foreground wipe for the church-to-arcade camera move. Unlike the
# old alpha polygon, this keeps the photographed arch and column intact. It is
# mounted at the same world-space joint as the arcade so all three Stanford
# layers move as one set.
threshold_source = column_source.crop((0, 0, column_source.width - 30, column_source.height))
threshold = cover_crop(threshold_source, (480, 1800), focal=(0.5, 0.28))
threshold_gray = ImageOps.autocontrast(threshold.convert("L"), cutoff=1)
threshold = ImageOps.colorize(threshold_gray, black="#171719", mid="#74685d", white="#dfc9a4")
threshold = ImageEnhance.Contrast(threshold).enhance(1.06)
threshold = ImageEnhance.Brightness(threshold).enhance(0.78)
threshold = threshold.convert("RGBA")
threshold_mask = Image.new("L", threshold.size, 0)
ImageDraw.Draw(threshold_mask).polygon(
    [
        (0, 0),
        (480, 0),
        (480, 1800),
        (150, 1800),
        (180, 1500),
        (205, 900),
        (142, 700),
        (0, 350),
    ],
    fill=255,
)
threshold.putalpha(threshold_mask.filter(ImageFilter.GaussianBlur(1.0)))
threshold.save(OUTPUT / "stanford-threshold.webp", "WEBP", quality=91, method=6)

shutil.copy2(SOURCE / "Eric_Wu_CV.pdf", ROOT / "web" / "public" / "Eric_Wu_CV.pdf")

for path in sorted(OUTPUT.iterdir()):
    with Image.open(path) as image:
        print(path.relative_to(ROOT), image.size, image.mode)
