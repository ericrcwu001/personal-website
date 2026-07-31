# Phase 3 source-geometry animatic runbook

Status: notebook prepared and statically validated on July 18, 2026. The real-data render must run in Google Colab because the authoritative reconstruction cache and Blender toolchain are not present on the local Mac.

## Deliverable

Run [the Phase 3 Colab notebook](../notebooks/reconstruction_phase3_animatic_colab.ipynb) from top to bottom. It produces one complete 18-second, 960×540, 15-fps homepage-intro animatic containing:

1. the selected Hong Kong A2 balanced composition;
2. the selected Hong Kong B2 telephoto composition;
3. the approved vertical crane into a sky-only atmospheric apex;
4. Stanford entering from below into the selected Wide / Gliding route;
5. the broad Stanford A approach and long Stanford B arcade glide;
6. temporary approved identity-copy timing beneath the geometry pass.

Hong Kong and Stanford remain fully opaque. Hong Kong leaves through the lower frame edge before Stanford exists in frame, and Stanford later enters through the lower edge. Frames 121–134 contain only the persistent sky and atmosphere.

## Reused inputs

The notebook restores existing files from `MyDrive/Personal_Website_Phase2_Cache`:

- official Open3Dhk sheets `11-SE-7A`, `11-SW-8B`, and `11-SW-14A`;
- Stanford Main Quad LiDAR crop, DSM, and centered PLY mesh.

It does not ask Eric to gather, photograph, upload, or model any source asset. Missing cached inputs are reacquired with resumable downloads and without the unreliable `HEAD` requests that previously triggered Hong Kong map-server failures.

## Persistence

Individual rendered frames are stored under:

`MyDrive/Personal_Website_Phase3_Render_Cache/approved_crane_v2_neutral`

That cache lets a disconnected Colab runtime resume instead of repeating completed geometry frames. It can be deleted after the animatic is approved.

Compact review artifacts are saved under:

`MyDrive/Personal_Website_Phase3_Animatic`

The final cell creates `Personal_Website_Phase3_Animatic.zip` in that folder.

## Review gate

This run approves or rejects spatial rhythm and real-source coverage. Hong Kong is intentionally rendered with neutral materials after the first textured attempt exceeded the Colab memory limit during Eevee synchronization. It does not approve photorealism, final church or arcade detail, licensed Hong Kong projection plates, vegetation, final typography, or foreground-object alpha masks.

If this animatic passes, the next work is the HABS-derived Stanford detail build and the licensed Hong Kong surface-projection test. If it fails, the camera path or source coverage changes before any detailed surface work begins.
