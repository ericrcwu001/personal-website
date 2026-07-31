#!/usr/bin/env python3
"""Build a clean Colab continuation that resumes approved S0/S1 and reviews one S2."""

from __future__ import annotations

import ast
import hashlib
import re
from pathlib import Path

import nbformat

import build_skyreels_cinematic_14b_a10080_colab as production


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "notebooks" / "skyreels_v2_14b_continue_from_s2_colab.ipynb"


TITLE = """
# SkyReels V2 14B — resume approved S0/S1 and review one controlled S2

This continuation uses the existing Drive run `intro_cinematic_14b_a10080_v1` and deliberately preserves its original configuration fingerprint. After configuration is locked, it re-applies the exact in-runtime stage definitions used to publish approved S0 seed `41201` and approved derived S1 seed `42212`, validates their hashed Drive artifacts, and renders exactly one replacement S2 candidate.

The rejected S2 seed `43211` descended convincingly but rolled around a foreground building and failed to level into the street. Replacement seed `43217` asks for a controlled, level-horizon descent through a clear building gap. The notebook stops after displaying and persisting that candidate; it does not accept S2 or generate later stages automatically.

Run on a fresh **Colab High-RAM A100 80 GB**. Generated media remains on Drive. Because model caching is disabled, a fresh runtime redownloads the pinned 14B checkpoint.
"""


RESUME_PATCH = r'''
# Re-apply the exact post-configuration stage definitions used by approved Drive candidates.
# CONFIG_FINGERPRINT intentionally remains the original production fingerprint.
s0 = stage_by_id("S0_skyline_push")
s0["seeds"] = [41201]
s0["prompt"] = (
    "Photorealistic Hong Kong at late golden hour. An FPV cinema drone immediately "
    "accelerates forward from Braemar Hill toward Central. The foreground hillside "
    "and nearby buildings rush outward past both edges with strong differential "
    "parallax. Bank of China Tower and Two IFC enlarge rapidly through real forward "
    "translation. Keep the camera level and the city filling the frame. Fixed 24mm "
    "lens, no static hold, digital zoom, sky-only shot, crossfade or morph."
)

s1 = stage_by_id("S1_tower_flight")
s1["mode"] = "i2v_open_drop_first"
s1["seeds"] = [42211]
s1.pop("end_anchor", None)
s1["prompt"] = (
    "The camera begins already moving at extreme speed above Hong Kong. Immediately "
    "accelerate forward and descend between the nearest skyscrapers. Foreground towers "
    "rush outward past both edges while Central enlarges rapidly ahead. Bank slightly "
    "right and lose altitude with unmistakable physical translation and strong depth "
    "parallax. Fixed 20mm cinema lens. No static drift, hovering, digital zoom, open-sky "
    "hold, crossfade or morph."
)

s2 = stage_by_id("S2_street_arrival")
s2["mode"] = "i2v_open_drop_first"
s2["seeds"] = [43217]
s2.pop("start_anchor", None)
s2.pop("endpoint_mae_max", None)
s2["prompt"] = (
    "Continue forward from the exact Hong Kong aerial frame with a controlled steep descent "
    "through a clear gap between skyscrapers. Keep the horizon level with less than five "
    "degrees of roll. The camera pitches down smoothly while nearby facades rise along both "
    "edges, never blocking the center. The street grid expands in the middle of frame, then "
    "the camera levels naturally at tram-wire height facing a red double-decker tram. Strong "
    "physical translation and parallax, stable straight buildings, no orbit, spin, open water, "
    "central foreground wall, crossfade, morph, digital zoom or camera cut."
)

approved = {}
for stage, expected_seed in ((s0, 41201), (s1, 42212)):
    result = accepted_candidate(stage)
    if result is None:
        ok, reason, manifest = validate_candidate(stage, expected_seed)
        raise RuntimeError(
            f"Approved {stage['id']} seed {expected_seed} did not validate: {reason}. "
            f"Candidate manifest present={manifest is not None}"
        )
    seed, manifest = result
    if seed != expected_seed:
        raise RuntimeError(f"Expected approved {stage['id']} seed {expected_seed}, found {seed}")
    approved[stage["id"]] = {"seed": seed, "metrics": manifest["metrics"]}

downstream_pointer_state = {
    downstream["id"]: accepted_pointer(downstream["id"]).is_file()
    for downstream in STAGES[2:]
}

print("Validated approved continuation parents:")
print(json.dumps(approved, indent=2))
print("Existing downstream pointers were left untouched:")
print(json.dumps(downstream_pointer_state, indent=2))
'''


S2_REVIEW = r'''
# Render or restore exactly one controlled S2 candidate, persist it, and stop for review.
from IPython.display import Video, display

def generate_open_drop_first(stage, seed):
    if not stage.get("parent"):
        raise RuntimeError(f"{stage['id']} requires an accepted parent")
    pipe = get_pipeline("i2v")
    first = restored_final(stage["parent"])
    output = pipe(
        image=first,
        last_image=None,
        prompt=stage["prompt"],
        negative_prompt=NEGATIVE_PROMPT,
        height=MODEL["height"],
        width=MODEL["width"],
        num_frames=stage["display_frames"] + 1,
        base_num_frames=stage["display_frames"] + 1,
        overlap_history=None,
        addnoise_condition=0,
        num_inference_steps=INFERENCE_STEPS,
        guidance_scale=GUIDANCE_SCALE,
        fps=FPS,
        generator=torch.Generator(device="cuda").manual_seed(seed),
        output_type="np",
        ar_step=0,
        causal_block_size=None,
    )
    forward = normalize_output_frames(output)
    expected = stage["display_frames"] + 1
    if len(forward) != expected:
        raise RuntimeError(f"I2V returned {len(forward)} frames, expected {expected}")
    forward[0] = np.asarray(first, dtype=np.uint8)
    frames = forward[1:]
    return publish_candidate(
        stage,
        seed,
        frames,
        {
            "seed": seed,
            "stage": stage,
            "conditioning": "controlled open I2V from approved S1 final frame",
            "completed_at_unix": time.time(),
        },
    )

seed = s2["seeds"][0]
ok, reason, manifest = validate_candidate(s2, seed)
if not ok:
    print("Generating replacement S2 candidate", seed, "because", reason)
    try:
        manifest = generate_open_drop_first(s2, seed)
    except Exception:
        dispose_pipeline()
        raise
else:
    print("Restored existing replacement S2 candidate", seed)

directory = candidate_dir(s2["id"], seed)
print(json.dumps(manifest["metrics"], indent=2))
print("Persistent review directory:", directory)
display(Image.open(directory / "contact_sheet.jpg"))
display(Video(str(directory / "clip.mp4"), embed=True, width=960))
print("S2 was NOT accepted. Send contact_sheet.jpg and clip.mp4 for review before continuing.")
'''


def build_notebook():
    notebook = production.build_notebook()
    notebook.cells[0].source = TITLE.strip() + "\n"

    contract_index = next(
        index
        for index, cell in enumerate(notebook.cells)
        if cell.cell_type == "code" and cell.source.startswith("# Fast synthetic contract tests")
    )
    notebook.cells = notebook.cells[: contract_index + 1]
    notebook.cells.append(nbformat.v4.new_code_cell(RESUME_PATCH.strip() + "\n"))
    notebook.cells.append(nbformat.v4.new_code_cell(S2_REVIEW.strip() + "\n"))
    return notebook


def audit(notebook) -> None:
    nbformat.validate(notebook)
    joined = "\n".join(cell.source for cell in notebook.cells)
    for index, cell in enumerate(notebook.cells):
        if cell.cell_type == "code":
            ast.parse(cell.source, filename=f"continuation-cell-{index}")
            if cell.outputs or cell.execution_count is not None:
                raise AssertionError(f"Notebook output leaked into cell {index}")

    required = (
        'RUN_ID = "intro_cinematic_14b_a10080_v1"',
        'FORCE_PROFILE = "14b_720p"',
        'NOTEBOOK_LOGIC_VERSION = "cinematic-14b-a10080-v1.0.0"',
        's0["seeds"] = [41201]',
        's1["seeds"] = [42211]',
        'expected_seed in ((s0, 41201), (s1, 42212))',
        's2["seeds"] = [43217]',
        "Existing downstream pointers were left untouched",
        "S2 was NOT accepted",
    )
    for marker in required:
        if marker not in joined:
            raise AssertionError(marker)

    forbidden = (
        "intro_cinematic_v2_1_1p3b",
        'accepted_pointer(downstream["id"]).unlink',
        "for stage in STAGES:\n    already = accepted_candidate",
        "# Assemble the accepted 432 frames",
    )
    for marker in forbidden:
        if marker in joined:
            raise AssertionError(f"Forbidden continuation behavior: {marker}")

    for pattern in (
        r"sk-[A-Za-z0-9_-]{20,}",
        r"hf_[A-Za-z0-9]{20,}",
        r"AIza[A-Za-z0-9_-]{20,}",
    ):
        if re.search(pattern, joined):
            raise AssertionError("Credential found")


def main() -> None:
    notebook = build_notebook()
    audit(notebook)
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, OUTPUT)
    print(OUTPUT)
    print("sha256", hashlib.sha256(OUTPUT.read_bytes()).hexdigest())
    print("bytes", OUTPUT.stat().st_size)


if __name__ == "__main__":
    main()
