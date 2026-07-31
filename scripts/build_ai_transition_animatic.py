"""Build the approved 18-second AI-transition pacing proxy.

This is deliberately a source-photo animatic, not a substitute for the final
image-to-video generations. It locks camera direction, occlusion timing, copy
holds, and forward/reverse scroll behavior before paid video generation.
"""

from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
MEDIA = ROOT / "web" / "public" / "media" / "depth"
OUTPUT = ROOT / "output" / "ai-cinematic" / "animatic-v1"
ANCHORS = OUTPUT / "anchors"

WIDTH = 960
HEIGHT = 540
FPS = 24
DURATION = 18.0
FRAME_COUNT = round(DURATION * FPS)

HK_SOURCE = MEDIA / "hong-kong.webp"
SKY_SOURCE = MEDIA / "shared-sky.webp"
CHURCH_SOURCE = ROOT / "output" / "imagegen" / "memorial-church-base.png"
ARCADE_SOURCE = MEDIA / "stanford-arcade.webp"

VIDEO_PATH = OUTPUT / "intro-ai-transition-animatic-v1.mp4"
BIDIRECTIONAL_PATH = OUTPUT / "intro-ai-transition-bidirectional-v1.mp4"
CONTACT_SHEET_PATH = OUTPUT / "anchor-contact-sheet-v1.jpg"
MANIFEST_PATH = OUTPUT / "animatic-manifest-v1.json"

NEW_YORK = Path("/System/Library/Fonts/NewYork.ttf")
HELVETICA = Path("/System/Library/Fonts/Helvetica.ttc")


def clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return min(maximum, max(minimum, value))


def smooth(value: float) -> float:
    value = clamp(value)
    return value * value * (3.0 - 2.0 * value)


def remap(value: float, start: float, end: float) -> float:
    if end == start:
        return 1.0
    return clamp((value - start) / (end - start))


def ease(value: float, start: float, end: float) -> float:
    return smooth(remap(value, start, end))


def read_rgb(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(path)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def camera_crop(
    image: np.ndarray,
    *,
    zoom: float = 1.0,
    center_x: float = 0.5,
    center_y: float = 0.5,
) -> np.ndarray:
    source_height, source_width = image.shape[:2]
    target_aspect = WIDTH / HEIGHT
    source_aspect = source_width / source_height
    if source_aspect >= target_aspect:
        base_height = source_height
        base_width = round(base_height * target_aspect)
    else:
        base_width = source_width
        base_height = round(base_width / target_aspect)

    crop_width = max(2, round(base_width / zoom))
    crop_height = max(2, round(base_height / zoom))
    half_width = crop_width / 2
    half_height = crop_height / 2
    center_pixel_x = np.clip(center_x * source_width, half_width, source_width - half_width)
    center_pixel_y = np.clip(center_y * source_height, half_height, source_height - half_height)
    left = round(center_pixel_x - half_width)
    top = round(center_pixel_y - half_height)
    crop = image[top : top + crop_height, left : left + crop_width]
    return cv2.resize(crop, (WIDTH, HEIGHT), interpolation=cv2.INTER_LANCZOS4)


def grade(frame: np.ndarray, warmth: float = 1.0) -> np.ndarray:
    work = frame.astype(np.float32) / 255.0
    work = np.clip((work - 0.5) * 1.035 + 0.5, 0, 1)
    work[:, :, 0] *= 1.0 + 0.035 * warmth
    work[:, :, 1] *= 1.0 + 0.012 * warmth
    work[:, :, 2] *= 1.0 - 0.028 * warmth
    return np.clip(work * 255.0, 0, 255).astype(np.uint8)


def make_cloud_mask(seed: int) -> np.ndarray:
    random = np.random.default_rng(seed)
    small = random.normal(0.48, 0.2, (90, 160)).astype(np.float32)
    small = cv2.GaussianBlur(small, (0, 0), 7.5)
    mask = cv2.resize(small, (WIDTH, HEIGHT), interpolation=cv2.INTER_CUBIC)
    for _ in range(34):
        x = int(random.uniform(-100, WIDTH + 100))
        y = int(random.uniform(-40, HEIGHT + 40))
        radius_x = int(random.uniform(65, 190))
        radius_y = int(random.uniform(24, 80))
        strength = float(random.uniform(0.28, 0.85))
        cv2.ellipse(mask, (x, y), (radius_x, radius_y), 0, 0, 360, strength, -1)
    mask = cv2.GaussianBlur(mask, (0, 0), 31)
    minimum, maximum = float(mask.min()), float(mask.max())
    return np.clip((mask - minimum) / max(maximum - minimum, 1e-6), 0, 1)


def cloud_composite(frame: np.ndarray, time: float, opacity: float) -> np.ndarray:
    if opacity <= 0:
        return frame
    mask_a = np.roll(CLOUD_MASK_A, (round(time * -5), round(time * 12)), axis=(0, 1))
    mask_b = np.roll(CLOUD_MASK_B, (round(time * 8), round(time * -8)), axis=(0, 1))
    mask = np.clip(mask_a * 0.7 + mask_b * 0.55, 0, 1)
    # The atmospheric bridge must genuinely hide the location swap. Raising
    # the mask floor as coverage approaches one avoids a disguised dissolve
    # through translucent clouds while retaining texture on entry and exit.
    alpha = opacity * np.clip(mask + opacity * 1.5 - 0.45, 0, 1)
    alpha = np.clip(alpha, 0, 1)[:, :, None]
    cloud_color = np.empty_like(frame, dtype=np.float32)
    cloud_color[:, :, 0] = 235
    cloud_color[:, :, 1] = 218
    cloud_color[:, :, 2] = 203
    return np.clip(frame * (1 - alpha) + cloud_color * alpha, 0, 255).astype(np.uint8)


def feathered_slide(base: np.ndarray, plate: np.ndarray, offset_y: int) -> np.ndarray:
    output = base.copy()
    start = offset_y
    end = offset_y + HEIGHT
    visible_start = max(0, start)
    visible_end = min(HEIGHT, end)
    if visible_end <= visible_start:
        return output
    source_start = visible_start - start
    source_end = source_start + (visible_end - visible_start)
    region = plate[source_start:source_end]
    alpha = np.ones((visible_end - visible_start, 1, 1), dtype=np.float32)
    feather = min(90, visible_end - visible_start)
    if source_start == 0 and feather > 1:
        alpha[:feather, 0, 0] = np.linspace(0, 1, feather, dtype=np.float32)
    output[visible_start:visible_end] = np.clip(
        output[visible_start:visible_end] * (1 - alpha) + region * alpha,
        0,
        255,
    ).astype(np.uint8)
    return output


def arch_mask(progress: float) -> np.ndarray:
    progress = smooth(progress)
    mask = np.zeros((HEIGHT, WIDTH), dtype=np.float32)
    # Both source plates place the traversed opening toward camera-right.
    # Keeping this axis stable makes the cut feel like physical travel.
    center_x = round(WIDTH * 0.82)
    base_y = round(HEIGHT * 0.70)
    half_width = max(
        1,
        round(1 + (progress**1.15) * WIDTH * 0.84),
    )
    radius = half_width
    top_y = base_y - round(radius * 1.12)
    left = center_x - half_width
    right = center_x + half_width
    cv2.rectangle(mask, (left, top_y), (right, HEIGHT), 1.0, -1)
    cv2.ellipse(mask, (center_x, top_y), (half_width, round(radius * 0.74)), 0, 180, 360, 1.0, -1)
    sigma = 3.0 + progress * 11.0
    return cv2.GaussianBlur(mask, (0, 0), sigma)


def blend_dark(frame: np.ndarray, amount: float, shaped: bool) -> np.ndarray:
    amount = clamp(amount)
    if amount <= 0:
        return frame
    if shaped:
        alpha = arch_mask(amount)[:, :, None]
    else:
        alpha = np.full((HEIGHT, WIDTH, 1), amount, dtype=np.float32)
    dark = np.zeros_like(frame, dtype=np.float32) + np.array([8, 9, 10], dtype=np.float32)
    return np.clip(frame * (1 - alpha) + dark * alpha, 0, 255).astype(np.uint8)


def reveal_through_arch(frame: np.ndarray, progress: float) -> np.ndarray:
    """Reveal the new location through a growing architectural opening."""
    progress = clamp(progress)
    opening = np.clip(arch_mask(progress) * progress, 0, 1)[:, :, None]
    dark = np.zeros_like(frame, dtype=np.float32) + np.array([8, 9, 10], dtype=np.float32)
    return np.clip(frame * opening + dark * (1 - opening), 0, 255).astype(np.uint8)


def font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(path), size=size)


def alpha_window(time: float, enter: float, hold_start: float, hold_end: float, exit: float) -> float:
    if time < enter or time > exit:
        return 0.0
    if time < hold_start:
        return ease(time, enter, hold_start)
    if time <= hold_end:
        return 1.0
    return 1.0 - ease(time, hold_end, exit)


def draw_copy(frame: np.ndarray, time: float) -> np.ndarray:
    image = Image.fromarray(frame).convert("RGBA")
    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    off_white = (244, 241, 234, 255)
    muted = (244, 241, 234, 215)

    opening_alpha = alpha_window(time, 0.1, 0.45, 2.7, 3.45)
    if opening_alpha > 0:
        draw.text(
            (50, 185),
            "Eric Wu",
            font=font(NEW_YORK, 112),
            fill=off_white[:-1] + (round(255 * opening_alpha),),
            stroke_width=2,
            stroke_fill=(18, 21, 23, round(80 * opening_alpha)),
        )
        draw.text(
            (55, 315),
            "Stanford '29, AI Engineer & Researcher",
            font=font(HELVETICA, 21),
            fill=muted[:-1] + (round(215 * opening_alpha),),
        )

    interests_alpha = alpha_window(time, 3.5, 3.9, 5.65, 6.25)
    if interests_alpha > 0:
        x, y = 54, 150
        draw.text(
            (x, y),
            "INTERESTED IN:",
            font=font(HELVETICA, 14),
            fill=muted[:-1] + (round(190 * interests_alpha),),
        )
        for line_index, text in enumerate(
            ["AI Engineering & Research", "Math", "CS", "Public Policy"]
        ):
            line_alpha = interests_alpha * ease(time, 3.78 + line_index * 0.28, 4.08 + line_index * 0.28)
            draw.text(
                (x, y + 30 + line_index * 58),
                text,
                font=font(NEW_YORK, 50),
                fill=off_white[:-1] + (round(255 * line_alpha),),
                stroke_width=1,
                stroke_fill=(18, 21, 23, round(65 * line_alpha)),
            )

    stanford_alpha = alpha_window(time, 9.2, 9.7, 11.35, 12.15)
    if stanford_alpha > 0:
        draw.text(
            (62, 170),
            "Stanford",
            font=font(NEW_YORK, 106),
            fill=off_white[:-1] + (round(255 * stanford_alpha),),
            stroke_width=2,
            stroke_fill=(18, 21, 23, round(70 * stanford_alpha)),
        )
        draw.text(
            (67, 290),
            "Class of 2029",
            font=font(NEW_YORK, 42),
            fill=off_white[:-1] + (round(245 * stanford_alpha),),
        )

    social_alpha = alpha_window(time, 15.65, 16.0, 17.55, 17.95)
    if social_alpha > 0:
        label = "GitHub     LinkedIn     X     Instagram     Email"
        draw.text(
            (410, 420),
            label,
            font=font(HELVETICA, 19),
            fill=off_white[:-1] + (round(255 * social_alpha),),
            anchor="mm",
        )

    return np.asarray(Image.alpha_composite(image, layer).convert("RGB"))


def render_background(time: float) -> np.ndarray:
    if time < 4.5:
        amount = ease(time, 0, 4.5)
        frame = camera_crop(
            HK,
            zoom=1.0 + 0.085 * amount,
            center_x=0.485 + 0.045 * amount,
            center_y=0.51,
        )
        return grade(frame, 0.9)

    if time < 7.2:
        amount = ease(time, 4.5, 7.2)
        sky = camera_crop(SKY, zoom=1.02, center_x=0.5 + amount * 0.02, center_y=0.48)
        hk_final = camera_crop(HK, zoom=1.085, center_x=0.53, center_y=0.51)
        frame = feathered_slide(sky, hk_final, round(amount * HEIGHT * 1.12))
    elif time < 14.35:
        reveal = ease(time, 7.2, 10.8)
        dolly = ease(time, 11.0, 14.35)
        frame = camera_crop(
            CHURCH,
            zoom=1.34 - reveal * 0.22 + dolly * 0.88,
            center_x=0.5,
            center_y=0.27 + reveal * 0.28 + dolly * 0.12,
        )
    else:
        emerge = ease(time, 14.35, 17.9)
        frame = camera_crop(
            ARCADE,
            zoom=1.62 - emerge * 0.54,
            center_x=0.45 + emerge * 0.06,
            center_y=0.42 + emerge * 0.1,
        )

    frame = grade(frame, 1.0)
    cloud_in = ease(time, 5.35, 6.85)
    cloud_out = 1.0 - ease(time, 8.05, 9.45)
    cloud_amount = min(cloud_in, cloud_out)
    if cloud_amount > 0:
        frame = cloud_composite(frame, time, cloud_amount * 1.17)

    if 13.15 <= time < 14.35:
        frame = blend_dark(frame, ease(time, 13.15, 14.25), shaped=True)
    elif 14.25 <= time < 14.8:
        frame = blend_dark(frame, 1.0, shaped=False)
    elif 14.8 <= time < 15.6:
        frame = reveal_through_arch(frame, remap(time, 14.8, 15.6))
    return frame


def add_grain(frame: np.ndarray, frame_index: int) -> np.ndarray:
    random = np.random.default_rng(2029 + frame_index)
    noise = random.normal(0, 1.35, frame.shape[:2] + (1,))
    return np.clip(frame.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def encode() -> dict[str, np.ndarray]:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    ANCHORS.mkdir(parents=True, exist_ok=True)
    command = [
        "ffmpeg",
        "-y",
        "-loglevel",
        "error",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{WIDTH}x{HEIGHT}",
        "-r",
        str(FPS),
        "-i",
        "-",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "18",
        "-g",
        "6",
        "-keyint_min",
        "1",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(VIDEO_PATH),
    ]
    process = subprocess.Popen(command, stdin=subprocess.PIPE)
    if process.stdin is None:
        raise RuntimeError("Could not open ffmpeg stdin")

    anchor_times = {
        "00-hong-kong-opening": 0.6,
        "01-hong-kong-crane": 5.85,
        "02-cloud-occlusion": 7.55,
        "03-memorial-church-reveal": 10.25,
        "04-dark-arch": 14.35,
        "05-main-quad-arcade": 17.2,
    }
    anchor_frames: dict[str, np.ndarray] = {}
    anchor_indices = {name: round(time * FPS) for name, time in anchor_times.items()}

    for frame_index in range(FRAME_COUNT):
        time = frame_index / FPS
        background = render_background(time)
        frame = draw_copy(background, time)
        frame = add_grain(frame, frame_index)
        for name, target_index in anchor_indices.items():
            if frame_index == target_index:
                anchor_frames[name] = frame.copy()
        process.stdin.write(frame.tobytes())

    process.stdin.close()
    return_code = process.wait()
    if return_code != 0:
        raise RuntimeError(f"ffmpeg exited with {return_code}")

    for name, frame in anchor_frames.items():
        Image.fromarray(frame).save(ANCHORS / f"{name}.png", optimize=True)
    return anchor_frames


def make_bidirectional_proof() -> None:
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(VIDEO_PATH),
            "-filter_complex",
            "[0:v]split=2[forward][reverse_source];"
            "[reverse_source]reverse[reverse];"
            "[forward][reverse]concat=n=2:v=1:a=0[out]",
            "-map",
            "[out]",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-g",
            "6",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(BIDIRECTIONAL_PATH),
        ],
        check=True,
    )


def make_contact_sheet(anchor_frames: dict[str, np.ndarray]) -> None:
    names = list(anchor_frames)
    thumb_width, thumb_height = 480, 270
    sheet = Image.new("RGB", (thumb_width * 2, (thumb_height + 34) * 3), "#111214")
    draw = ImageDraw.Draw(sheet)
    label_font = font(HELVETICA, 16)
    for index, name in enumerate(names):
        row, column = divmod(index, 2)
        thumb = Image.fromarray(anchor_frames[name]).resize((thumb_width, thumb_height))
        x = column * thumb_width
        y = row * (thumb_height + 34)
        sheet.paste(thumb, (x, y))
        draw.text((x + 12, y + thumb_height + 8), name, font=label_font, fill="#f0ede7")
    sheet.save(CONTACT_SHEET_PATH, quality=92, optimize=True)


def write_manifest() -> None:
    manifest = {
        "status": "source-photo pacing proxy; not final AI video",
        "duration_seconds": DURATION,
        "fps": FPS,
        "resolution": [WIDTH, HEIGHT],
        "runtime_direction": "one continuous impossible camera move",
        "scroll_behavior": "bidirectional exact-time scrub",
        "occlusions": [
            {"type": "moving cloud field", "start": 5.35, "full": [6.85, 8.05], "end": 9.45},
            {"type": "dark architectural arch", "start": 13.15, "full": [14.25, 14.8], "end": 15.6},
        ],
        "identity_beats": [
            {"name": "Hong Kong A", "range": [0, 3.45], "copy": "Eric Wu"},
            {"name": "Hong Kong B", "range": [3.5, 6.25], "copy": "Interests"},
            {"name": "Atmospheric bridge", "range": [5.35, 9.45], "copy": None},
            {"name": "Stanford A", "range": [9.2, 12.15], "copy": "Stanford / Class of 2029"},
            {"name": "Architectural bridge", "range": [13.15, 15.6], "copy": None},
            {"name": "Stanford B", "range": [15.65, 17.95], "copy": "Social links"},
        ],
        "outputs": {
            "forward": str(VIDEO_PATH.relative_to(ROOT)),
            "forward_reverse": str(BIDIRECTIONAL_PATH.relative_to(ROOT)),
            "contact_sheet": str(CONTACT_SHEET_PATH.relative_to(ROOT)),
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")


HK = read_rgb(HK_SOURCE)
SKY = read_rgb(SKY_SOURCE)
CHURCH = read_rgb(CHURCH_SOURCE)
ARCADE = read_rgb(ARCADE_SOURCE)
CLOUD_MASK_A = make_cloud_mask(2029)
CLOUD_MASK_B = make_cloud_mask(8529)


def main() -> None:
    for path in [HK_SOURCE, SKY_SOURCE, CHURCH_SOURCE, ARCADE_SOURCE]:
        if not path.exists():
            raise FileNotFoundError(path)
    anchor_frames = encode()
    make_bidirectional_proof()
    make_contact_sheet(anchor_frames)
    write_manifest()
    print(VIDEO_PATH)
    print(BIDIRECTIONAL_PATH)
    print(CONTACT_SHEET_PATH)
    print(MANIFEST_PATH)


if __name__ == "__main__":
    main()
