#!/usr/bin/env python3
"""Build the clean SkyReels 14B/A100-80 production notebook."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import nbformat

import build_skyreels_cinematic_v2_colab as cinematic


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "skyreels_v2_cinematic_14b_a10080_colab.ipynb"


TITLE = cinematic.TITLE.replace(
    "# SkyReels V2 — cinematic route v2 with automatic candidate rejection",
    "# SkyReels V2 14B — A100-80 cinematic production run",
    1,
).replace(
    "This notebook replaces the rejected slow-drift render",
    "This clean production notebook is isolated from every rejected 1.3B render and replaces the slow-drift attempt",
    1,
)


def replace_setting(source: str, name: str, value: str) -> str:
    pattern = rf"^{re.escape(name)}\s*=.*$"
    replacement = f"{name} = {value}"
    updated, count = re.subn(pattern, replacement, source, count=1, flags=re.MULTILINE)
    if count != 1:
        raise RuntimeError(f"Could not replace setting {name}")
    return updated


def build_notebook():
    notebook = cinematic.build_notebook()
    notebook.cells[0].source = TITLE.strip() + "\n"

    settings = next(
        cell
        for cell in notebook.cells
        if cell.cell_type == "code" and cell.source.startswith("# Production controls")
    )
    settings.source = replace_setting(
        settings.source,
        "RUN_ID",
        '"intro_cinematic_14b_a10080_v1"',
    )
    settings.source = replace_setting(settings.source, "FORCE_PROFILE", '"14b_720p"')
    settings.source = replace_setting(
        settings.source,
        "NOTEBOOK_LOGIC_VERSION",
        '"cinematic-14b-a10080-v1.0.0"',
    )
    settings.outputs = []
    settings.execution_count = None

    preflight = next(
        cell
        for cell in notebook.cells
        if cell.cell_type == "code" and cell.source.startswith("# Hardware and storage preflight")
    )
    marker = 'gpu_name = gpu.name\n'
    requirement = (
        'gpu_name = gpu.name\n'
        'if "A100" not in gpu_name or gpu.total_memory / (1024 ** 3) < 75:\n'
        '    raise RuntimeError(f"This notebook requires an A100 80GB; found {gpu_name} with "\n'
        '                       f"{gpu.total_memory / (1024 ** 3):.1f} GiB VRAM")\n'
    )
    if marker not in preflight.source:
        raise RuntimeError("A100 preflight insertion point changed")
    preflight.source = preflight.source.replace(marker, requirement, 1)
    preflight.outputs = []
    preflight.execution_count = None

    cinematic.audit(notebook)
    joined = "\n".join(cell.source for cell in notebook.cells)
    for required in (
        'RUN_ID = "intro_cinematic_14b_a10080_v1"',
        'FORCE_PROFILE = "14b_720p"',
        'NOTEBOOK_LOGIC_VERSION = "cinematic-14b-a10080-v1.0.0"',
        "This notebook requires an A100 80GB",
    ):
        if required not in joined:
            raise AssertionError(required)
    if "intro_cinematic_v2_1_1p3b" in joined:
        raise AssertionError("1.3B recovery run leaked into the production notebook")
    return notebook


def main() -> None:
    notebook = build_notebook()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT)
    print("sha256", hashlib.sha256(OUTPUT.read_bytes()).hexdigest())
    print("bytes", OUTPUT.stat().st_size)


if __name__ == "__main__":
    main()
