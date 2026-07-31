"""Generate Eric Wu's continuous cinematic intro with Sora video extensions.

The default invocation is deliberately non-billable. It prepares the exact
1280x720 Hong Kong reference frame and writes the production manifest. Pass
``--execute hk`` only when a direct OpenAI API key with Videos API access is
available. Later stages extend the completed source video rather than starting
independent clips, preserving camera motion across scene changes.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import requests
from PIL import Image, ImageEnhance


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "web" / "public" / "media" / "depth" / "hong-kong.webp"
OUTPUT = ROOT / "output" / "ai-cinematic" / "sora-production"
ANCHORS = OUTPUT / "anchors"
REFERENCE = ANCHORS / "hk-braemar-1280x720.webp"
MANIFEST = OUTPUT / "production-manifest.json"
STATE = OUTPUT / "generation-state.json"
CREDENTIAL_FILE = Path.home() / ".codex" / "openai-video.env"

API_BASE = "https://api.openai.com/v1"
SIZE = "1280x720"
POLL_SECONDS = 15


@dataclass(frozen=True)
class Stage:
    key: str
    seconds: int
    output_name: str
    prompt: str


STAGES = {
    "hk": Stage(
        key="hk",
        seconds=8,
        output_name="01-hong-kong-scale-change.mp4",
        prompt=(
            "One single unbroken photorealistic stabilized cinema-camera shot. "
            "Begin exactly on the supplied late-golden-hour photograph from "
            "Braemar Hill overlooking the real Hong Kong skyline. For the first "
            "three seconds, hold the broad panorama with only a slow rightward "
            "camera drift. Then accelerate decisively forward through real "
            "three-dimensional space across Victoria Harbour toward Central. "
            "This must be physical camera travel with strong evolving parallax, "
            "not a flat image zoom, rotation, warp, or Ken Burns effect. Move "
            "toward a tight skyline composition in which Two International "
            "Finance Centre and Bank of China Tower become approximately 2.5 to "
            "3 times larger in the frame while retaining their real shape, "
            "facade, proportions, and positions. Foreground foliage clears much "
            "faster than the distant buildings and the harbour visibly expands "
            "beneath the camera. After the close landmark beat, preserve the same "
            "forward velocity while the camera cranes upward and pitches toward "
            "the sky. The towers travel downward and leave frame naturally. Enter "
            "dense, warm, volumetric golden-hour cloud cover, with the final "
            "three quarters of a second completely filled by moving cloud texture. "
            "Natural motion blur and exposure adaptation, coherent lens and "
            "camera inertia. No text, no people, no invented buildings, no facade "
            "morphing, no dissolve, no portal, no cut, no flash."
        ),
    ),
    "stanford": Stage(
        key="stanford",
        seconds=8,
        output_name="02-hong-kong-through-stanford-darkness.mp4",
        prompt=(
            "Continue the exact same unbroken camera move, inheriting the source "
            "video's velocity, lens, roll, exposure, and cloud optical flow. Begin "
            "inside complete moving golden-hour cloud cover; keep the frame fully "
            "occluded long enough that no geographic transformation is visible. "
            "Then descend and pitch down as the clouds thin naturally and the real "
            "Stanford Memorial Church and Main Quad rise into view from below. The "
            "architecture is revealed by cloud motion, never morphed from it. Hold "
            "a broad, slightly off-axis late-golden-hour view of the church, then "
            "continue physically forward toward the dark central sandstone arch. "
            "Accelerate into the arch until real architectural shadow fills every "
            "pixel for the final half second. Preserve Romanesque geometry, mosaic "
            "detail, and camera inertia. No people, text, dissolve, portal, cut, "
            "white flash, or exposure reset."
        ),
    ),
    "arcade": Stage(
        key="arcade",
        seconds=4,
        output_name="03-complete-continuous-master-20s.mp4",
        prompt=(
            "Continue the exact same camera path from complete architectural "
            "darkness. A small warm opening appears on the established camera-right "
            "travel axis and expands naturally as the camera physically emerges "
            "beneath the Stanford Main Quad arcade. Continue a wide, shallow "
            "rightward glide through the real sandstone colonnade with strong "
            "near-column parallax and stable forward momentum. End on an open, "
            "readable arcade composition. Natural golden-hour light, realistic "
            "stone texture and motion blur. No people, text, morph, dissolve, cut, "
            "flash, or camera reset."
        ),
    ),
}


def prepare_reference() -> None:
    """Create the exact first-frame asset required by the Videos API."""
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)
    ANCHORS.mkdir(parents=True, exist_ok=True)
    image = Image.open(SOURCE).convert("RGB")
    target_ratio = 16 / 9
    source_ratio = image.width / image.height
    if source_ratio > target_ratio:
        crop_width = round(image.height * target_ratio)
        left = round((image.width - crop_width) * 0.52)
        image = image.crop((left, 0, left + crop_width, image.height))
    else:
        crop_height = round(image.width / target_ratio)
        top = round((image.height - crop_height) * 0.44)
        image = image.crop((0, top, image.width, top + crop_height))
    image = image.resize((1280, 720), Image.Resampling.LANCZOS)
    image = ImageEnhance.Color(image).enhance(1.03)
    image = ImageEnhance.Contrast(image).enhance(1.025)
    image.save(REFERENCE, "WEBP", quality=96, method=6)


def read_state() -> dict[str, Any]:
    if not STATE.exists():
        return {"stages": {}}
    return json.loads(STATE.read_text())


def write_state(state: dict[str, Any]) -> None:
    STATE.write_text(json.dumps(state, indent=2) + "\n")


def write_manifest(model: str) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    payload = {
        "status": "ready_for_video_api_credential",
        "provider": "OpenAI Videos API",
        "api_base": API_BASE,
        "model": model,
        "size": SIZE,
        "reference": str(REFERENCE.relative_to(ROOT)),
        "generation_strategy": (
            "Create Hong Kong from the real first-frame reference, then extend "
            "the completed cumulative video twice. Never generate independent clips."
        ),
        "review_gate": (
            "Approve the 8-second Hong Kong spatial scale-change before executing "
            "the Stanford or arcade extensions."
        ),
        "stages": [asdict(STAGES[key]) for key in ("hk", "stanford", "arcade")],
        "final_edit": {
            "source_duration_seconds": 20,
            "target_duration_seconds": 18,
            "method": "retime cumulative master only; no visual transition effects",
        },
    }
    MANIFEST.write_text(json.dumps(payload, indent=2) + "\n")


def load_api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if key:
        return key
    if CREDENTIAL_FILE.exists():
        for raw_line in CREDENTIAL_FILE.read_text().splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            if name.removeprefix("export ").strip() == "OPENAI_API_KEY":
                return value.strip().strip('"').strip("'")
    return ""


def headers() -> dict[str, str]:
    key = load_api_key()
    if not key:
        raise RuntimeError(
            f"Add a direct OpenAI Platform key to {CREDENTIAL_FILE}. A key with "
            "Videos API access is required; the TrueFoundry image proxy cannot "
            "run this."
        )
    return {"Authorization": f"Bearer {key}"}


def checked_json(response: requests.Response) -> dict[str, Any]:
    if response.ok:
        return response.json()
    try:
        detail = response.json()
    except ValueError:
        detail = response.text[:1000]
    raise RuntimeError(f"OpenAI API returned HTTP {response.status_code}: {detail}")


def poll(video_id: str) -> dict[str, Any]:
    last_progress: Any = None
    while True:
        response = requests.get(
            f"{API_BASE}/videos/{video_id}", headers=headers(), timeout=60
        )
        video = checked_json(response)
        status = video.get("status")
        progress = video.get("progress")
        if progress != last_progress:
            print(f"{video_id}: {status} {progress if progress is not None else ''}")
            last_progress = progress
        if status == "completed":
            return video
        if status in {"failed", "cancelled", "expired"}:
            raise RuntimeError(f"Video job {video_id} ended as {status}: {video}")
        time.sleep(POLL_SECONDS)


def download(video_id: str, target: Path) -> None:
    with requests.get(
        f"{API_BASE}/videos/{video_id}/content",
        headers=headers(),
        params={"variant": "video"},
        timeout=300,
        stream=True,
    ) as response:
        response.raise_for_status()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    handle.write(chunk)


def create_hong_kong(stage: Stage, model: str) -> dict[str, Any]:
    with REFERENCE.open("rb") as reference:
        response = requests.post(
            f"{API_BASE}/videos",
            headers=headers(),
            data={
                "model": model,
                "prompt": stage.prompt,
                "size": SIZE,
                "seconds": str(stage.seconds),
            },
            files={
                "input_reference": (
                    REFERENCE.name,
                    reference,
                    "image/webp",
                )
            },
            timeout=120,
        )
    return checked_json(response)


def extend_video(stage: Stage, source_video_id: str) -> dict[str, Any]:
    response = requests.post(
        f"{API_BASE}/videos/extensions",
        headers={**headers(), "Content-Type": "application/json"},
        json={
            "video": {"id": source_video_id},
            "prompt": stage.prompt,
            "seconds": str(stage.seconds),
        },
        timeout=120,
    )
    return checked_json(response)


def execute_stage(stage_key: str, model: str) -> None:
    state = read_state()
    stage = STAGES[stage_key]
    if stage_key == "hk":
        job = create_hong_kong(stage, model)
    else:
        predecessor = "hk" if stage_key == "stanford" else "stanford"
        predecessor_state = state.get("stages", {}).get(predecessor, {})
        source_video_id = predecessor_state.get("video_id")
        if predecessor_state.get("status") != "completed" or not source_video_id:
            raise RuntimeError(
                f"Stage {stage_key} requires completed stage {predecessor}."
            )
        job = extend_video(stage, source_video_id)

    video_id = job["id"]
    state.setdefault("stages", {})[stage_key] = {
        "video_id": video_id,
        "status": job.get("status", "queued"),
        "output": stage.output_name,
    }
    write_state(state)
    completed = poll(video_id)
    target = OUTPUT / stage.output_name
    download(video_id, target)
    state["stages"][stage_key].update(
        {
            "status": "completed",
            "downloaded_to": str(target.relative_to(ROOT)),
            "seconds": completed.get("seconds"),
            "size": completed.get("size"),
        }
    )
    write_state(state)
    print(target)


def make_review_copy() -> None:
    source = OUTPUT / STAGES["arcade"].output_name
    if not source.exists():
        raise FileNotFoundError(source)
    target = OUTPUT / "04-continuous-master-18s-review.mp4"
    subprocess.run(
        [
            "/opt/homebrew/bin/ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(source),
            "-an",
            "-vf",
            "setpts=0.9*PTS",
            "-t",
            "18",
            "-c:v",
            "libx264",
            "-preset",
            "slow",
            "-crf",
            "17",
            "-g",
            "6",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(target),
        ],
        check=True,
    )
    print(target)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--execute",
        choices=["hk", "stanford", "arcade"],
        help="Run one billable generation stage. Omit for a local dry run.",
    )
    parser.add_argument(
        "--model",
        default="sora-2",
        choices=["sora-2", "sora-2-pro"],
        help="Use sora-2 for motion tests and sora-2-pro for final-quality rerenders.",
    )
    parser.add_argument(
        "--make-review-copy",
        action="store_true",
        help="Retime the completed cumulative 20-second master to 18 seconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    prepare_reference()
    write_manifest(args.model)
    print(REFERENCE)
    print(MANIFEST)
    if args.make_review_copy:
        make_review_copy()
    if args.execute:
        execute_stage(args.execute, args.model)
    else:
        print("Dry run complete; no API request was made.")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise
