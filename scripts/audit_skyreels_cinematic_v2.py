#!/usr/bin/env python3
"""Static and synthetic smoke tests for the cinematic SkyReels Colab notebook."""

from __future__ import annotations

import ast
import base64
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

import nbformat
import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NOTEBOOK = ROOT / "notebooks" / "skyreels_v2_cinematic_v2_colab.ipynb"


def code_cell(notebook, prefix: str) -> str:
    return next(
        cell.source
        for cell in notebook.cells
        if cell.cell_type == "code" and cell.source.startswith(prefix)
    )


def assigned_literal(source: str, name: str):
    tree = ast.parse(source)
    assignment = next(
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
    )
    return ast.literal_eval(assignment.value)


def main(notebook_path: Path = DEFAULT_NOTEBOOK) -> None:
    notebook_path = notebook_path.expanduser().resolve()
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
    joined = "\n".join(cell.source for cell in notebook.cells)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=f"notebook-cell-{index}")
            assert cell.execution_count is None
            assert not cell.outputs

    for pattern in (
        r"sk-[A-Za-z0-9_-]{20,}",
        r"hf_[A-Za-z0-9]{20,}",
        r"AIza[A-Za-z0-9_-]{20,}",
    ):
        assert re.search(pattern, joined) is None

    config_source = code_cell(notebook, "# Lock the nine-stage")
    stages = assigned_literal(config_source, "STAGES")
    captions = assigned_literal(config_source, "CAPTION_TIMELINE")
    assert [stage["display_frames"] for stage in stages] == [49, 48, 48, 72, 24, 48, 60, 48, 35]
    assert sum(stage["display_frames"] for stage in stages) == 432
    assert len(stages) == 9
    assert [caption["scroll_progress"] for caption in captions] == [
        [0.0, 0.25], [0.25, 0.5], [0.5, 0.75], [0.75, 1.0]
    ]
    assert captions[1]["visible_video_frames"] == [72, 217]
    assert captions[2]["visible_video_frames"] == [241, 349]
    for stage in stages:
        if stage["mode"] == "i2v":
            model_frames = stage["display_frames"]
        elif stage["mode"] in {"i2v_drop_first", "reverse_i2v"}:
            model_frames = stage["display_frames"] + 1
        else:
            continue
        assert model_frames <= 49

    history = 17
    for stage in (stage for stage in stages if stage["mode"] == "v2v"):
        desired = stage["display_frames"]
        minimum = desired + history
        model_frames = ((minimum - 1 + 3) // 4) * 4 + 1
        combined = list(range(history + model_frames))
        new_motion = combined[2 * history : 2 * history + desired]
        assert len(new_motion) == desired
        assert new_motion[0] == 34

    sentinel = list(range(49))
    assert sentinel[1:] == list(range(1, 49))
    assert list(reversed(sentinel))[1:] == list(range(47, -1, -1))

    anchor_source = code_cell(notebook, "# Restore the six bundled")
    match = re.search(r"EMBEDDED_ANCHORS = json\.loads\(r'''(.*?)'''\)", anchor_source, re.S)
    assert match
    anchors = json.loads(match.group(1))
    assert len(anchors) == 6
    for record in anchors.values():
        payload = base64.b64decode(record["base64"])
        assert hashlib.sha256(payload).hexdigest() == record["sha256"]

    for marker in (
        "pipe.vae.enable_tiling()",
        "from_pipe(previous, torch_dtype=None)",
        "contact_sheet.jpg",
        "accepted_timeline_contact_sheet.jpg",
        "intro_cinematic_v2_bidirectional-proof.mp4",
        "intro_cinematic_v2_scrub_1080p24.mp4",
        "maximum_keyframe_gap",
        "parent_boundary_mae",
        "opening_sky_too_long",
        "opening_dark_too_long",
    ):
        assert marker in joined

    utilities = code_cell(notebook, "# Candidate persistence")
    namespace = {
        "Path": Path,
        "FPS": 24,
        "hashlib": hashlib,
        "json": json,
        "os": os,
        "shutil": shutil,
        "subprocess": subprocess,
        "uuid": uuid,
    }
    exec(utilities, namespace)

    counts = [stage["display_frames"] for stage in stages]
    with tempfile.TemporaryDirectory(prefix="skyreels-v2-audit-") as temporary:
        root = Path(temporary)
        clips = []
        for clip_index, count in enumerate(counts):
            frames = []
            for frame_index in range(count):
                frame = np.zeros((180, 320, 3), dtype=np.uint8)
                frame[:, :, 0] = (clip_index * 23 + frame_index * 2) % 255
                frame[:, :, 1] = np.arange(320, dtype=np.uint8)[None, :]
                frame[:, :, 2] = np.arange(180, dtype=np.uint8)[:, None]
                frames.append(frame)
            clip = root / f"stage-{clip_index}.mp4"
            namespace["encode_video"](frames, clip)
            assert namespace["probe_video"](clip)["frames"] == count
            sheet = root / f"stage-{clip_index}.jpg"
            namespace["write_contact_sheet"](frames, sheet, stages[clip_index]["id"], 1000 + clip_index)
            assert sheet.stat().st_size > 0
            clips.append(clip)

        master = root / "master.mp4"
        command = ["ffmpeg", "-y", "-v", "error"]
        for clip in clips:
            command.extend(["-i", str(clip)])
        labels = "".join(f"[v{index}]" for index in range(len(clips)))
        filters = [
            f"[{index}:v]scale=320:180:flags=lanczos,setsar=1,setpts=PTS-STARTPTS[v{index}]"
            for index in range(len(clips))
        ]
        filters.append(f"{labels}concat=n={len(clips)}:v=1:a=0,format=yuv420p[vout]")
        command.extend(
            [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[vout]",
                "-an",
                "-r",
                "24",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(master),
            ]
        )
        subprocess.run(command, check=True)
        assert namespace["probe_video"](master)["frames"] == 432

        ping_pong = root / "ping-pong.mp4"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-v",
                "error",
                "-i",
                str(master),
                "-filter_complex",
                "[0:v]split=2[f][r];[f]setpts=PTS-STARTPTS[fwd];"
                "[r]reverse,setpts=PTS-STARTPTS[rev];"
                "[fwd][rev]concat=n=2:v=1:a=0,format=yuv420p[vout]",
                "-map",
                "[vout]",
                "-an",
                "-r",
                "24",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                str(ping_pong),
            ],
            check=True,
        )
        assert namespace["probe_video"](ping_pong)["frames"] == 864

    print(
        json.dumps(
            {
                "status": "passed",
                "notebook": str(notebook_path),
                "sha256": hashlib.sha256(notebook_path.read_bytes()).hexdigest(),
                "cells": len(notebook.cells),
                "stages": len(stages),
                "frames": sum(counts),
                "duration_seconds": sum(counts) / 24,
                "synthetic_bidirectional_frames": 864,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    selected = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_NOTEBOOK
    main(selected)
