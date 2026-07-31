"""Generate source-grounded depth maps for the real-time photo reconstructions.

The resulting grayscale images are relative inverse-depth fields: white pixels
are closer to the reference camera and black pixels are farther away. The web
renderer unprojects the corresponding photograph along the reference camera's
rays, producing real parallax without inventing building geometry.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as functional
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
from transformers import AutoImageProcessor, AutoModelForDepthEstimation


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "prototype" / "intro-animatic" / "assets"
OUTPUT = ROOT / "web" / "public" / "media" / "depth"
OUTPUT.mkdir(parents=True, exist_ok=True)

MODEL_ID = "depth-anything/Depth-Anything-V2-Small-hf"


def cover_crop(image: Image.Image, size: tuple[int, int], focal=(0.5, 0.5)) -> Image.Image:
    target_width, target_height = size
    scale = max(target_width / image.width, target_height / image.height)
    resized = image.resize(
        (round(image.width * scale), round(image.height * scale)),
        Image.Resampling.LANCZOS,
    )
    left = round((resized.width - target_width) * focal[0])
    top = round((resized.height - target_height) * focal[1])
    left = max(0, min(left, resized.width - target_width))
    top = max(0, min(top, resized.height - target_height))
    return resized.crop((left, top, left + target_width, top + target_height))


def prepare_sources() -> dict[str, Image.Image]:
    hong_kong_source = Image.open(SOURCE / "hong-kong-wide.png").convert("RGB")
    hong_kong = cover_crop(
        hong_kong_source,
        (1920, 1280),
        focal=(0.52, 0.58),
    )
    hong_kong = ImageEnhance.Color(hong_kong).enhance(0.94)

    church_photo = cover_crop(
        Image.open(SOURCE / "stanford-church.jpg").convert("RGB"),
        (1920, 1340),
        focal=(0.5, 0.53),
    )
    church_photo = ImageEnhance.Color(church_photo).enhance(0.92)

    # Build one opaque Stanford plate with enough genuine sky above the roof
    # for a physical tilt-down reveal. The architecture is composited once at
    # build time, so the browser never exposes a feathered rectangular layer.
    shared_sky_source = hong_kong_source.crop(
        (0, 0, hong_kong_source.width, round(hong_kong_source.height * 0.43))
    )
    shared_sky = cover_crop(shared_sky_source, (1920, 1080), focal=(0.55, 0.46))
    church = shared_sky.resize((3840, 3000), Image.Resampling.BICUBIC)
    church_mask = Image.new("L", church_photo.size, 0)
    draw = ImageDraw.Draw(church_mask)
    width, height = church_photo.size
    draw.polygon(
        [
            (round(width * 0.225), round(height * 0.43)),
            (round(width * 0.5), round(height * 0.025)),
            (round(width * 0.775), round(height * 0.43)),
            (round(width * 0.79), round(height * 0.78)),
            (round(width * 0.21), round(height * 0.78)),
        ],
        fill=255,
    )
    draw.rectangle(
        (0, round(height * 0.53), width, height),
        fill=255,
    )
    draw.rectangle(
        (
            round(width * 0.482),
            round(height * 0.005),
            round(width * 0.518),
            round(height * 0.14),
        ),
        fill=255,
    )
    church_pixels = np.asarray(church_photo, dtype=np.int16)
    red = church_pixels[:, :, 0]
    green = church_pixels[:, :, 1]
    blue = church_pixels[:, :, 2]
    sky_like = (
        (blue > red + 14)
        & (blue > green + 5)
        & ((red + green + blue) > 230)
    )
    mask_pixels = np.asarray(church_mask, dtype=np.uint8).copy()
    mask_pixels[sky_like] = 0
    church_mask = Image.fromarray(mask_pixels, "L")
    church_mask = church_mask.filter(ImageFilter.GaussianBlur(0.7))
    church.paste(church_photo, (960, 1260), church_mask)
    ground_extension = church_photo.crop((0, 940, width, height)).transpose(
        Image.Transpose.FLIP_TOP_BOTTOM
    )
    church.paste(ground_extension, (960, 2600))

    arcade_source = Image.open(SOURCE / "stanford-column.jpg").convert("RGB")
    arcade = cover_crop(arcade_source, (1920, 1280), focal=(0.5, 0.45))
    arcade_gray = ImageOps.autocontrast(arcade.convert("L"), cutoff=1)
    arcade = ImageOps.colorize(
        arcade_gray,
        black="#171614",
        mid="#766354",
        white="#dfc092",
    )
    arcade = ImageEnhance.Contrast(arcade).enhance(1.04)
    arcade = ImageEnhance.Brightness(arcade).enhance(0.9)

    return {
        "hong-kong": hong_kong,
        "stanford-church": church,
        "stanford-arcade": arcade,
    }


def main() -> None:
    device = torch.device("mps" if torch.backends.mps.is_available() else "cpu")
    print(f"Depth device: {device}")
    processor = AutoImageProcessor.from_pretrained(MODEL_ID, local_files_only=True)
    model = AutoModelForDepthEstimation.from_pretrained(MODEL_ID, local_files_only=True)
    model.to(device).eval()

    hong_kong_source = Image.open(SOURCE / "hong-kong-wide.png").convert("RGB")
    clean_sky_source = hong_kong_source.crop(
        (0, 0, hong_kong_source.width, round(hong_kong_source.height * 0.43))
    )
    clean_sky = cover_crop(clean_sky_source, (1920, 1080), focal=(0.55, 0.46))
    clean_sky = ImageEnhance.Color(clean_sky).enhance(0.9)
    clean_sky.save(OUTPUT / "shared-sky.webp", "WEBP", quality=94, method=6)
    print(f"Wrote {(OUTPUT / 'shared-sky.webp').relative_to(ROOT)}")

    for name, image in prepare_sources().items():
        color_path = OUTPUT / f"{name}.webp"
        depth_path = OUTPUT / f"{name}-depth.png"

        inputs = processor(images=image, return_tensors="pt")
        inputs = {key: value.to(device) for key, value in inputs.items()}
        with torch.inference_mode():
            prediction = model(**inputs).predicted_depth
        prediction = functional.interpolate(
            prediction.unsqueeze(1),
            size=(image.height, image.width),
            mode="bicubic",
            align_corners=False,
        ).squeeze()
        depth = prediction.float().cpu().numpy()
        low, high = np.percentile(depth, (1.0, 99.0))
        depth = np.clip((depth - low) / max(high - low, 1e-6), 0, 1)

        # Preserve fine architecture while reducing single-pixel depth noise.
        depth_image = Image.fromarray(np.round(depth * 255).astype(np.uint8), "L")
        depth_image = ImageOps.autocontrast(depth_image, cutoff=(0.5, 0.5))
        depth_image.save(depth_path, optimize=True)

        # Each reconstruction fills the viewport. Keeping the source opaque
        # avoids a visibly feathered rectangular plate when the camera tracks
        # laterally; scene changes happen while the camera sees only sky or a
        # close sandstone surface.
        image.save(color_path, "WEBP", quality=94, method=6)

        print(f"Wrote {color_path.relative_to(ROOT)}")
        print(f"Wrote {depth_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
