"""Build the self-contained Phase 3 Colab notebook from reviewed sources."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_NOTEBOOK = ROOT / "notebooks" / "reconstruction_phase2_full_colab.ipynb"
OUTPUT_NOTEBOOK = ROOT / "notebooks" / "reconstruction_phase3_animatic_colab.ipynb"


def lines(text: str) -> list[str]:
    return text.splitlines(keepends=True)


def markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": lines(text)}


def code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines(text),
    }


phase2 = json.loads(SOURCE_NOTEBOOK.read_text())
utility_source = "".join(phase2["cells"][3]["source"]).replace(
    "Eric-Wu-Personal-Website-Phase2/1.0",
    "Eric-Wu-Personal-Website-Phase3/1.0",
)
hk_source = "".join(phase2["cells"][4]["source"])
stanford_source = "".join(phase2["cells"][5]["source"])

script_names = [
    "phase3_render_hong_kong.py",
    "phase3_render_stanford.py",
    "phase3_assemble_animatic.py",
    "reconstruction_phase3_animatic.py",
]
script_payload = {
    name: (ROOT / "notebooks" / name).read_text()
    for name in script_names
}

write_scripts_source = """# Install the reviewed Phase 3 render scripts into this runtime.
PHASE3_SCRIPT_ROOT = Path('/content/phase3_scripts')
PHASE3_SCRIPT_ROOT.mkdir(parents=True, exist_ok=True)

SCRIPT_PAYLOAD = %s
for filename, source in SCRIPT_PAYLOAD.items():
    destination = PHASE3_SCRIPT_ROOT / filename
    destination.write_text(source)
    compile(source, str(destination), 'exec')
    print('Installed:', destination, len(source), 'characters')
""" % repr(script_payload)

cells = [
    markdown(
        """# Personal website reconstruction — Phase 3 source-geometry animatic

This notebook renders the complete approved homepage intro choreography against the cached reconstruction sources:

- selected Hong Kong A2 → B2 camera route on the official Open3Dhk geometry;
- the approved vertical crane bridge, with Hong Kong physically leaving below frame;
- a persistent sky-only apex with **no environment crossfade**;
- Stanford entering naturally from below into the selected Wide / Gliding route;
- temporary identity-copy timing beneath the geometry pass.

This is the full low-resolution animatic gate, not the final photoreal surface render. Hong Kong uses authoritative geometry with neutral materials so Eevee remains within Colab memory; official texture projection returns in the later surface gate. Stanford uses the public-domain LiDAR for real scale and campus massing; the church and arcade remain source-positioned blocking geometry until the HABS detail pass.

Run every cell from top to bottom. The notebook reuses `MyDrive/Personal_Website_Phase2_Cache`, persists individual render frames in `MyDrive/Personal_Website_Phase3_Render_Cache` so it can resume after a disconnect, and saves compact review artifacts to `MyDrive/Personal_Website_Phase3_Animatic`. The render cache can be deleted after the animatic is approved.

Expected first-run time is roughly 45–150 minutes, dominated by official glTF import and 256 low-resolution geometry frames. An A100 is acceptable, although these Eevee renders remain partly CPU/OpenGL bound.
"""
    ),
    code(
        """# Configuration and persistent Drive paths.
from pathlib import Path
from google.colab import drive

drive.mount('/content/drive')

WORK_ROOT = Path('/content/reconstruction_phase1')
HK_ROOT = WORK_ROOT / 'hong_kong'
STANFORD_ROOT = WORK_ROOT / 'stanford'
SOURCE_OUTPUT_ROOT = WORK_ROOT / 'source_outputs'
PHASE2_OUTPUT_ROOT = SOURCE_OUTPUT_ROOT  # Compatibility with the acquisition cells below.

DRIVE_CACHE_ROOT = Path('/content/drive/MyDrive/Personal_Website_Phase2_Cache')
DRIVE_OUTPUT_ROOT = Path('/content/drive/MyDrive/Personal_Website_Phase3_Animatic')
PHASE3_RUNTIME_OUTPUT = Path('/content/drive/MyDrive/Personal_Website_Phase3_Render_Cache/approved_crane_v2_neutral')

for path in [WORK_ROOT, HK_ROOT, STANFORD_ROOT, SOURCE_OUTPUT_ROOT,
             DRIVE_CACHE_ROOT, DRIVE_OUTPUT_ROOT, PHASE3_RUNTIME_OUTPUT]:
    path.mkdir(parents=True, exist_ok=True)

HK_SHEETS = {
    'braemar_hill': '11-SE-7A',
    'two_ifc': '11-SW-8B',
    'bank_of_china': '11-SW-14A',
}

STANFORD_BBOX_WGS84 = {
    'west': -122.1740,
    'south': 37.4240,
    'east': -122.1660,
    'north': 37.4310,
}

print('Reconstruction work root:', WORK_ROOT)
print('Reusing persistent cache:', DRIVE_CACHE_ROOT)
print('Saving compact outputs to:', DRIVE_OUTPUT_ROOT)
"""
    ),
    code(
        """# Deterministic toolchain. Re-running this cell is safe.
import os
import shutil
import subprocess
import sys


def run(command, *, check=True, env=None):
    print('+', command if isinstance(command, str) else ' '.join(map(str, command)))
    return subprocess.run(
        command,
        shell=isinstance(command, str),
        check=check,
        env=env,
    )

run('apt-get update -qq')
run('DEBIAN_FRONTEND=noninteractive apt-get install -y -qq blender ffmpeg unzip python3-numpy xvfb xauth libgl1-mesa-dri fonts-dejavu-core')
os.environ['LIBGL_ALWAYS_SOFTWARE'] = '1'
run([sys.executable, '-m', 'pip', 'install', '-q',
     'requests>=2.31', 'tqdm>=4.66', 'pandas>=2.0', 'Pillow>=10.0',
     'pyproj>=3.6', 'rasterio>=1.3', 'trimesh>=4.0', 'laspy[lazrs]>=2.5',
     'opencv-python-headless>=4.9'])

MICROMAMBA = Path('/content/bin/micromamba')
PDAL_ENV = Path('/content/pdal-env')
PDAL = PDAL_ENV / 'bin/pdal'
if not MICROMAMBA.exists():
    run('mkdir -p /content/bin && curl -Ls https://micro.mamba.pm/api/micromamba/linux-64/latest | tar -xj -C /content bin/micromamba')
if not PDAL.exists():
    run([str(MICROMAMBA), 'create', '-y', '-p', str(PDAL_ENV), '-c', 'conda-forge', 'pdal'])

run(['blender', '--background', '--python-expr', "import numpy; print('Blender NumPy', numpy.__version__)"])
run(['xvfb-run', '-a', 'blender', '--background', '--python-exit-code', '1',
     '--python-expr', "import bpy; print('Xvfb Blender ready', bpy.app.version_string)"])
run([str(PDAL), '--version'])
run(['ffmpeg', '-version'])
print('Free temporary storage:', shutil.disk_usage('/content'))
"""
    ),
    code(utility_source),
    markdown(
        """## Restore the authoritative reconstruction inputs

The next two cells first restore your completed Drive cache. They download only an input that is genuinely absent. The Hong Kong acquisition deliberately avoids `HEAD` requests because the government server intermittently rejects them.
"""
    ),
    code(hk_source),
    code(stanford_source),
    markdown(
        """## Render and assemble the complete animatic

The scripts below are embedded in this notebook, so no separate upload is required. Existing completed frame ranges are reused after a runtime disconnect.
"""
    ),
    code(write_scripts_source),
    code(
        """# Render Hong Kong, render Stanford, composite the shared atmosphere, and save compact outputs.
runner = PHASE3_SCRIPT_ROOT / 'reconstruction_phase3_animatic.py'
run([
    sys.executable,
    str(runner),
    '--work-root', str(WORK_ROOT),
    '--output-root', str(PHASE3_RUNTIME_OUTPUT),
    '--drive-output', str(DRIVE_OUTPUT_ROOT),
    '--width', '960',
    '--height', '540',
    '--fps', '15',
    '--samples', '16',
    '--neutral-hong-kong',
])
"""
    ),
    code(
        """# Package and preview the review artifacts.
import shutil
from IPython.display import Image as DisplayImage, Video, display

archive_base = Path('/content/Personal_Website_Phase3_Animatic')
drive_archive = DRIVE_OUTPUT_ROOT / f'{archive_base.name}.zip'
drive_archive.unlink(missing_ok=True)  # Prevent a prior archive from being archived into itself.
archive_path = Path(shutil.make_archive(str(archive_base), 'zip', root_dir=DRIVE_OUTPUT_ROOT))
shutil.copy2(archive_path, drive_archive)

video_path = DRIVE_OUTPUT_ROOT / 'phase3_source_geometry_animatic.mp4'
keyframes_path = DRIVE_OUTPUT_ROOT / 'phase3_animatic_keyframes.jpg'
report_path = DRIVE_OUTPUT_ROOT / 'phase3_report.md'

display(Video(str(video_path), embed=True, width=960))
display(DisplayImage(filename=str(keyframes_path)))
print(report_path.read_text())
print('Downloadable ZIP:', drive_archive)
"""
    ),
    markdown(
        """## Review handoff

After the run finishes, download `MyDrive/Personal_Website_Phase3_Animatic/Personal_Website_Phase3_Animatic.zip` and place it in the local website workspace. The review decision is the complete spatial rhythm: Hong Kong A → Hong Kong B → vertical atmospheric bridge → Stanford A → Stanford B. Final textures, landmark detail, vegetation, typography spacing, and object-specific text masks are deliberately later gates.
"""
    ),
]

for index, cell in enumerate(cells):
    cell["id"] = f"phase3-{index:02d}"

notebook = {
    "cells": cells,
    "metadata": {
        "accelerator": "GPU",
        "colab": {"name": OUTPUT_NOTEBOOK.name, "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.x"},
    },
    "nbformat": 4,
    "nbformat_minor": 5,
}

OUTPUT_NOTEBOOK.write_text(json.dumps(notebook, indent=1))
print(OUTPUT_NOTEBOOK)
