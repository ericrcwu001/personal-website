#!/usr/bin/env python3
"""Build the uploadable Stanford continuation notebook from the audited base cells."""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NOTEBOOK = ROOT / "notebooks" / "hunyuanvideo15_portfolio_intro_colab.ipynb"
CONTINUATION_CELL = ROOT / "scripts" / "hunyuan_stanford_column_continuations_cell.py"
DESTINATION = ROOT / "notebooks" / "hunyuanvideo15_stanford_column_continuations_colab.ipynb"
SOURCE_ARCHIVES = {
    "A": Path("/Users/ericwu/Downloads/A_church_to_column.zip"),
    "B": Path("/Users/ericwu/Downloads/B_arcade_to_column.zip"),
}
PAYLOAD_CHARS_PER_CELL = 240_000


def source_lines(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    return lines


base = json.loads(SOURCE_NOTEBOOK.read_text(encoding="utf-8"))

intro = {
    "cell_type": "markdown",
    "metadata": {},
    "source": source_lines(
        """# HunyuanVideo 1.5 — Stanford physical-column continuations

This notebook restores the completed `A_church_to_column` and `B_arcade_to_column`
clips from Google Drive when available, with verified copies embedded as a
self-contained fallback. It generates only two 49-frame physical-motion
continuations from exact source frame 56, splices them without crossfading or
post-production camera zoom, hash-verifies the outputs in Drive, and deletes the
Colab runtime automatically after success. Errors remain visible for two minutes
before automatic cleanup.

Use an **A100 80 GB High-RAM** runtime. Run all cells in order. The generated
media is for local evaluation pending the model-license review already documented
in the main Hunyuan notebook. Generated media and manifests persist in Drive; the
replaceable 50.5 GB model snapshot remains temporary and is deleted with the runtime.
"""
    ),
}

# Settings, Drive setup, A100 preflight, pinned runtime, and utility functions.
selected_indices = [1, 2, 4, 5, 7]
cells = [intro]
for index in selected_indices:
    cell = base["cells"][index]
    source = cell["source"]
    cloned = {
        "cell_type": cell["cell_type"],
        "metadata": cell.get("metadata", {}),
        "source": source,
    }
    if cell["cell_type"] == "code":
        cloned["execution_count"] = None
        cloned["outputs"] = []
    cells.append(cloned)

embedded_sources = {}
for role, archive_path in SOURCE_ARCHIVES.items():
    if not archive_path.is_file():
        raise FileNotFoundError(f"Missing source archive for {role}: {archive_path}")
    with zipfile.ZipFile(archive_path) as archive:
        clip_payload = archive.read("clip.mp4")
    embedded_sources[role] = {
        "origin_archive": archive_path.name,
        "bytes": len(clip_payload),
        "sha256": hashlib.sha256(clip_payload).hexdigest(),
        "base64": base64.b64encode(clip_payload).decode("ascii"),
    }

cells.append(
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source_lines(
            "# Initialize chunked source payloads; small cells keep Colab responsive.\n"
            "EMBEDDED_SOURCE_CLIP_PARTS = {'A': [], 'B': []}\n"
        ),
    }
)

for role in sorted(embedded_sources):
    encoded = embedded_sources[role]["base64"]
    chunks = [encoded[index : index + PAYLOAD_CHARS_PER_CELL] for index in range(0, len(encoded), PAYLOAD_CHARS_PER_CELL)]
    for chunk_index, chunk in enumerate(chunks, start=1):
        cells.append(
            {
                "cell_type": "code",
                "execution_count": None,
                "metadata": {},
                "outputs": [],
                "source": source_lines(
                    f"# Embedded {role} source payload chunk {chunk_index}/{len(chunks)}.\n"
                    f"EMBEDDED_SOURCE_CLIP_PARTS[{role!r}].append({chunk!r})\n"
                ),
            }
        )

embedded_metadata = {
    role: {key: value for key, value in record.items() if key != "base64"}
    for role, record in embedded_sources.items()
}
metadata_json = json.dumps(embedded_metadata, sort_keys=True, separators=(",", ":"))
cells.append(
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source_lines(
            "# Assemble and verify the two embedded source records.\n"
            "_EMBEDDED_SOURCE_METADATA = json.loads(r'''" + metadata_json + "''')\n"
            "EMBEDDED_SOURCE_CLIPS = {\n"
            "    role: {**record, 'base64': ''.join(EMBEDDED_SOURCE_CLIP_PARTS[role])}\n"
            "    for role, record in _EMBEDDED_SOURCE_METADATA.items()\n"
            "}\n"
            "del EMBEDDED_SOURCE_CLIP_PARTS, _EMBEDDED_SOURCE_METADATA\n"
            "print('Embedded source clips ready:', {k: v['sha256'] for k, v in EMBEDDED_SOURCE_CLIPS.items()})\n"
        ),
    }
)

cells.append(
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": source_lines(CONTINUATION_CELL.read_text(encoding="utf-8")),
    }
)

notebook = {
    "cells": cells,
    "metadata": base.get("metadata", {}),
    "nbformat": 4,
    "nbformat_minor": 5,
}
DESTINATION.write_text(json.dumps(notebook, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(DESTINATION)
