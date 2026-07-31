# Reconstruction and Asset Feasibility Audit

Status: Phase 1 technical truth test passed on 2026-07-17. The official Hong Kong geometry, Stanford LiDAR, and rights-safe Stanford reference set were acquired and verified. No final stock asset has been purchased.

## Decision

The intro is feasible without asking Eric to photograph, scan, record, or prepare either location.

The recommended route is a source-grounded hybrid:

1. Use authoritative open 3D or LiDAR data to lock geography, scale, silhouettes, and camera positions.
2. Use licensed or public-domain real photography for the high-frequency appearance that mapping data cannot provide.
3. Reconstruct only the camera corridors needed by the four approved shots; do not build two complete explorable cities.
4. Use AI for camera/depth estimation, restoration, seam repair, and tightly masked environmental completion. Never let it redesign a recognizable building.
5. Render the camera paths offline and deliver optimized scrubbed media to the website. The browser does not need to run the production reconstruction.

The two locations should not be forced through the same reconstruction technique:

- **Hong Kong:** official textured 3D data is already available, so it should establish geometry and camera truth. Licensed Braemar Hill sunset imagery should supply the final photographic surface quality.
- **Stanford:** no complete rights-safe Memorial Church model was found. Public-domain LiDAR should establish the campus massing, while the church facade and Main Quad arcade are rebuilt as clean geometry from rights-safe architectural photographs.

This is the best balance of photorealism, authenticity, controllable motion, legal reuse, and performance.

## Authenticity contract

The finished environment can be AI-assisted, but it must satisfy all of the following:

- The skyline, church, arcade, terrain, and camera relationships come from real source data.
- Landmark silhouettes and visible architectural details remain source-verifiable.
- AI-generated pixels cannot introduce or remove identifiable windows, rooflines, columns, mosaics, towers, or signage.
- Camera travel stays inside a source-supported corridor. We do not reveal unseen sides of a landmark by hallucinating them.
- Every production input has a saved source URL, license, retrieval date, checksum, permitted use, and transformation log.
- Any AI-assisted cleanup is disclosed on a compact site credits/provenance page, not in the cinematic copy.

## Hong Kong source audit

### Authoritative geometry

The Hong Kong Lands Department [fully launched its territory-wide 3D Digital Map in March 2025](https://www.landsd.gov.hk/en/survey-mapping/mapping/3d-mapping.html). The relevant products are:

- [3D Visualisation Map — Individualised models](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1671676915450_88604): textured, object-separated models in MAX, FBX, and glTF.
- [3D Visualisation Map — Non-textured models](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1742809441342_98380): geometry-only models in MAX, FBX, and glTF.
- [3D Visualisation Map — Tile-based models](https://portal.csdi.gov.hk/geoportal/?datasetId=landsd_rcd_1671677054006_62261): an oblique-aerial-image mesh in OBJ, OSGB, and Cesium 3D Tiles.
- [Open3Dhk source-download API](https://3d.map.gov.hk/download-api): accepts a format and 1:1000 sheet number and returns a ZIP archive.

The portal metadata uses Hong Kong 1980 Grid, EPSG:2326. Its stated absolute accuracy is approximately ±0.30 m horizontally and ±0.50 m vertically, with approximately ±0.20 m relative accuracy in each axis.

The exact production sheets have already been identified from the official index:

| Subject | Coordinate used for lookup | Official sheet | Current index revision | Individualised glTF ZIP | Tile-mesh OBJ ZIP |
| --- | --- | --- | --- | ---: | ---: |
| Braemar Hill Lookout | 22.2854710, 114.2071475 | `11-SE-7A` | 2026-07-17 | 2.00 GiB | 6.06 GiB |
| Two IFC | 22.2853762, 114.1590347 | `11-SW-8B` | 2025-12-22 | 0.83 GiB | 2.72 GiB |
| Bank of China Tower | 22.2792403, 114.1615832 | `11-SW-14A` | 2025-12-22 | 0.89 GiB | 5.10 GiB |

The first technical spike should download the three glTF archives, approximately 3.72 GiB compressed in total. The much larger OBJ archives are fallback inputs only if their oblique-aerial textures visibly outperform the individualised models in the approved camera views.

The Open3Dhk terms permit browsing, downloading, reproducing, and distributing the data for commercial and non-commercial purposes with source acknowledgement and the other stated conditions. The final site needs a credit to the Lands Department, the Government of the Hong Kong SAR, and Open3Dhk/CSDI. The current [DATA.GOV.HK terms](https://data.gov.hk/en/terms-and-conditions) express the same commercial and non-commercial reuse permission and attribution requirement. Terms and dataset metadata must be snapshotted again when production assets are acquired because the terms can change.

### Photographic appearance

The official geometry is strong enough for parallax, occlusion, camera matching, and the wide skyline. It is not by itself strong enough for a tight, cinematic inspection of Bank of China Tower and Two IFC.

There is usable late-day stock coverage without asking Eric to capture anything:

- Getty currently lists [21 Braemar Hill sunset clips](https://www.gettyimages.com/videos/braemar-hill-sunset). Particularly relevant source-grounded camera studies include clips `2149466475`, `2149466457`, `2149463426`, `2149461444`, and `2149461189`, all described as views captured around sunset from the summit of Braemar Hill.
- PIXTA currently returns [a large Braemar Hill image set](https://www.pixtastock.com/search?keyword=braemar%20hill%20hong%20kong), including a same-session sunset sequence `92566421` through `92566430` and sunset footage such as `81535942`, `81535947`, and `81535944`.

Watermarked previews are suitable only for internal composition tests. Any frame or texture used in the public render must be purchased under a license that covers website/promotional use and derivative compositing. The source license remains relevant even after projection, splatting, or AI cleanup.

### Hong Kong production route

1. Import and georeference the three individualised glTF sheets in Blender.
2. Place the virtual camera at the real lookout and solve the initial lens against a licensed wide Braemar plate.
3. Use the government geometry for all skyline silhouettes, depth, and parallax throughout the continuous Hong Kong camera corridor.
4. Camera-project licensed sunset frames onto the visible geometry and build a constrained gsplat only if a licensed moving clip contains enough parallax for the approved shot.
5. Retain the real photographed harbour, haze, and sky where possible. Build the controllable shared sky and volumetric-haze pass required for the selected Hong Kong-to-Stanford atmospheric bridge.
6. Use a separate high-detail projection for the Bank of China/Two IFC telephoto shot; do not enlarge the wide plate and invent detail.
7. Render beauty, depth, object-ID, and foreground-occluder passes from the same camera.

## Stanford source audit

### Campus-scale geometry

The [2020 Santa Clara County LiDAR collection](https://noaa-nos-coastal-lidar-pds.s3.amazonaws.com/laz/geoid18/9329/index.html) is available from NOAA/USGS as LAZ and an Entwine point tile service. Its metadata reports:

- 0.35 m planned nominal pulse spacing; approximately 0.21 m aggregate tested spacing.
- Building points in classification 6, plus ground and vegetation classes.
- Actual non-vegetated RMSEz of approximately 4.72 cm.
- Collection in early 2020.

[USGS-authored data are considered public domain](https://www.usgs.gov/information-policies-and-instructions/copyrights-and-credits), with credit requested. This LiDAR can lock terrain, rooflines, building footprints, arcade height, and alignment. It cannot provide facade mosaics, sandstone detail, capitals, or clean vertical walls.

### Rights-safe image inventory

The Library of Congress [HABS survey CA-2172-A](https://www.loc.gov/item/ca1003/) contains 20 downloadable church photographs: 18 black-and-white photographs and two color transparencies. It includes frontal, oblique, rear, mosaic, entrance-arcade, capital, and column-shaft details. The record states no known restrictions for images made by the U.S. Government.

The current Wikimedia inventory is also large enough for source selection:

- [Exterior of Stanford Memorial Church](https://commons.wikimedia.org/wiki/Category:Exterior_of_Stanford_Memorial_Church): 77 files. At the audit date, 28 are marked public domain and one CC0. Another five are marked no restrictions and 12 use non-ShareAlike CC BY licenses.
- [Stanford University Main Quad](https://commons.wikimedia.org/wiki/Category:Stanford_University_Main_Quad): 207 direct files. At the audit date, 54 are marked public domain and 11 CC0. Another four are marked no restrictions and 50 use non-ShareAlike CC BY licenses.
- [Carol M. Highsmith's Memorial Church photograph](https://www.loc.gov/item/2013634782/) provides a modern, high-resolution public-domain facade reference.

The lower-friction first pass should use public-domain and CC0 files. Non-ShareAlike CC BY files can fill a verified coverage gap with visible credit. CC BY-SA files should be excluded from the first production bundle to avoid an unnecessary license-compatibility question around projected textures and rendered derivatives.

The image set is broad enough to model and texture the approved views, but it is not a coherent photogrammetry capture. Different dates, cameras, weather, and lighting make a one-click NeRF or Gaussian reconstruction unreliable. A clean explicit mesh is the primary Stanford method.

### Stanford production route

1. Stream only the Memorial Church/Main Quad area of interest from the public LiDAR rather than downloading the county.
2. Convert ground, roof, and building-class points into a campus-scale proxy and align all photo cameras to it.
3. Build the church facade as clean, source-matched geometry. Use the HABS frontal and oblique views for proportions and detail placement.
4. Build the Main Quad arcade procedurally from a verified bay: column, capital, arch, roof, and spacing. Repetition makes this more accurate and lighter than a noisy photogrammetry mesh.
5. Project public-domain/CC0 photography into base-color textures, remove baked lighting conservatively, and derive restrained roughness/normal detail.
6. Render real late-golden-hour lighting in Blender. The light is synthetic and controllable; the architecture is not.
7. Use real or scanned vegetation assets for foreground parallax and the final column reveal.
8. Render beauty, depth, object-ID, and foreground-occluder passes from the same camera.

## AI and reconstruction tool policy

Preferred stack:

| Tool | Role | License posture | Production rule |
| --- | --- | --- | --- |
| Blender/Cycles | Geometry, materials, lighting, animation, offline render | GPL application; rendered outputs are not required to be GPL | Primary deterministic scene and camera tool. |
| COLMAP | Conventional camera solve and sparse reconstruction | BSD-style, subject to dependency licenses | First choice when the source set has real overlap. |
| [VGGT](https://github.com/facebookresearch/vggt) | Camera, depth, and point estimates from inconsistent image sets | Meta custom license, updated 2025-07-29; it contains no stated non-commercial restriction but is not an OSI license | Optional assistant only. Freeze the exact commit/license and re-check before production. Never treat its inferred geometry as landmark truth. |
| [gsplat](https://github.com/nerfstudio-project/gsplat) | Limited-view Gaussian rendering from licensed, coherent imagery | Apache-2.0 | Use only where a real clip provides enough parallax. Not the Stanford base. |
| [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) | Local restoration/upscale tests | BSD-3-Clause code | Use on reversible texture copies and compare against the source at 100–200%. |
| Topaz Photo/Video | Optional denoise, deblur, and upscale | Current individual plans permit commercial use for entities under US$1M annual revenue | Use only if local restoration is insufficient; save the subscription/license receipt. |
| Adobe Firefly/Photoshop | Masked generative fill for peripheral gaps | Adobe says Firefly output may be used commercially; qualifying plans have narrower indemnification terms | Sky, haze, foliage, and seam repair only. Never generate landmark geometry or facade detail. |

Explicitly avoid in this production:

- VGGT-Omega, MASt3R, DUSt3R, and any InstantSplat pipeline that inherits their non-commercial restrictions.
- The original Graphdeco Gaussian Splatting implementation, whose license is non-commercial, when the Apache-licensed gsplat route is available.
- Google Earth/Earth Studio as a source for the promotional hero.
- Google Photorealistic 3D Tiles for offline extraction or derived geometry. The [Map Tiles API policies](https://developers.google.com/maps/documentation/tile/policies) restrict caching, extraction, and offline use in ways that do not fit this production.
- Unlicensed YouTube, Instagram, Flickr, or photography-blog frames, regardless of whether they are publicly viewable.

## AI boundary masks

Every AI-assisted image edit should be saved with a mask and assigned one of these classes:

- `RESTORE`: denoise, deblur, compression repair, or upscale with no new structure.
- `ENVIRONMENT`: sky, haze, distant water, or foliage completion outside landmark masks.
- `SEAM`: projection-hole or texture-seam repair, constrained by adjacent real pixels.
- `FORBIDDEN`: any edit touching an identifiable facade, roofline, tower silhouette, window arrangement, mosaic, arch, capital, signage, or transition edge.

`FORBIDDEN` masks cannot enter a production render. The original and edited texture should be visually diffed and retained together.

## Production phases and gates

### Phase 0 — provenance bundle

- Create an asset manifest with source, author, URL, license, purchase receipt, retrieval date, checksum, location, and intended use.
- Snapshot official terms and metadata.
- Define landmark-protection masks before generative cleanup.

Gate: every input is either rights-safe for public use or explicitly marked internal-preview-only.

### Phase 1 — technical truth test

- Run the [Phase 1 Google Colab notebook](../notebooks/reconstruction_phase1_colab.ipynb) to provision the toolchain, acquire the exact rights-safe inputs, save provenance, and create neutral source-coverage diagnostics.
- Hong Kong: import sheet `11-SE-7A` plus the two Central sheets, solve one wide camera and one telephoto camera, and render ungraded geometry/texture stills.
- Stanford: stream a small LiDAR AOI, create one church-facade proxy and one finished arcade bay, then render the two approved camera angles.
- Use temporary real imagery and 720p output. Do not spend time on final polish.

Gate: the four identity compositions are recognizably the correct places and both continuous camera corridors fit available source coverage.

### Phase 2 — camera blocking

- Run the [standalone Phase 2 Colab notebook](../notebooks/reconstruction_phase2_full_colab.ipynb). It restores or acquires every required input, caches expensive sources in private Drive storage, renders three neutral composition candidates for each approved view, and writes contact sheets and camera manifests to `MyDrive/Personal_Website_Phase2`.
- Eric selects or rejects the large camera compositions rather than forcing an arbitrary default into production.

Completed decision: Hong Kong uses A2 balanced and B2 telephoto. Stanford uses the Wide / Gliding direction, with the broad A1 approach and longest B1 arcade route as the geometry-animatic anchors.

Gate: passed for the four anchor compositions and the proxy atmospheric-bridge motion.

### Phase 3 — source-geometry animatic

- Run the [Phase 3 source-geometry Colab notebook](../notebooks/reconstruction_phase3_animatic_colab.ipynb), which reuses the persistent Phase 2 reconstruction cache and resumes rendered frames after a disconnect.
- Assemble one continuous Hong Kong camera corridor, the approved vertical sky-and-haze bridge, and one continuous Stanford camera corridor.
- Add the approved semantic text timing beneath the geometry pass.
- Verify that the official Hong Kong geometry and LiDAR-scaled Stanford corridor support the complete spatial rhythm before detailed surface work.

Gate: Eric approves the full real-source camera choreography and information rhythm. Minor type spacing is not a gate.

### Phase 4 — final geometry and surfaces

- Clean only what the camera sees.
- Purchase the final Hong Kong plate/footage licenses.
- Finish Stanford church and arcade geometry from the selected rights-safe images.
- Produce source-grounded materials and protected AI cleanup masks.

Gate: no visible projection smear, double edge, melted detail, or AI-invented architecture at the final camera resolution.

### Phase 5 — offline render and web delivery

- Render beauty, depth, object-ID, and foreground passes at master resolution.
- Grade the two locations into one natural late-golden-hour continuum.
- Encode separate desktop and mobile assets.
- Test video scrubbing versus a progressively loaded frame sequence; choose by real device performance.
- Keep a static poster and reduced-motion sequence derived from the same masters.

Gate: stable scroll playback on the agreed device tier without sacrificing a correct static first frame.

## Practical compute route

The current Mac is an M2 Pro with 16 GB unified memory and only about 14 GiB free disk space at the audit date. Blender, PDAL, and COLMAP are not currently installed. The source archives should therefore not be expanded in the website workspace.

To keep the process hands-off for Eric:

1. Use a temporary GPU workstation with at least 100–200 GB of fast working storage for reconstruction and Cycles rendering.
2. Keep source archives and intermediate geometry in temporary object storage.
3. Pull only lightweight proxies, review renders, provenance records, and final web media into this repository.
4. Delete temporary cloud compute after the final masters and manifests are safely stored.

This avoids asking Eric to manage disks or install a 3D toolchain locally. It also makes the production repeatable instead of depending on one nearly full laptop.

## Cost and schedule reality

The first capture-free proof is modest: a few focused production days plus dataset transfer and render time. The final hero is still a real visual-effects job, not a one-prompt generation.

Planning ranges, to be refined after Phase 1:

- Rights/stock: approximately US$100–1,000 depending on which and how many Getty/PIXTA assets are selected. Public-domain Stanford sources cost nothing but still require provenance work.
- Temporary GPU/storage: approximately US$50–300 for the proof and final renders if scenes are kept camera-specific.
- Production effort: roughly 2–4 weeks of focused solo reconstruction, look development, animation, rendering, optimization, and device QA after the animatic is approved.
- Optional specialist polish: a 3D environment artist can compress the church/arcade cleanup phase, but the pipeline does not require Eric to create any inputs.

These are not purchase authorizations. The low-resolution proof should determine whether the final quality merits the full spend.

## Primary risks and fallbacks

| Risk | Early test | Fallback |
| --- | --- | --- |
| Government Hong Kong textures fail under telephoto inspection | Render Bank of China/Two IFC at the final screen size in Phase 1 | Use a licensed telephoto plate projected onto the official silhouettes and constrain the camera move. |
| Stock footage has the wrong lens or insufficient parallax | Solve all shortlisted previews against the official mesh | Use still-photo projection with a smaller 2.5D move; preserve photorealism over excessive camera travel. |
| Stanford public images do not support a free camera | Photo-match all selected cameras before detailed modeling | Lock the camera path to two narrow source-supported corridors and spend detail only there. |
| LiDAR walls/columns are too soft | Inspect building-class cross sections | Use LiDAR only for scale/massing and explicit procedural architecture for visible surfaces. |
| Atmospheric bridge reads as a dissolve or effect | Render a neutral-material geometry proof with persistent clouds, volumetric noise, and camera motion; inspect optical flow frame by frame | Lengthen the zero-landmark atmospheric center, reduce the geometry visibility overlap, and preserve one shared cloud or particulate cue across the handoff. |
| AI restoration invents facade detail | Diff every edit inside protected masks | Revert the landmark region to source pixels and accept lower local sharpness. |
| Two synchronized media layers drift in browser playback | Build a 5-second desktop/mobile occlusion proof | Use segmented frame sequences for the masked beats or dual platform-specific alpha encodes. |
| Full media misses the performance budget | Measure the animatic on ordinary hardware | Shorten motion, reduce frame count, or use real keyframe transitions while retaining the same four identity beats. |

## Recommendation

Proceed with the Phase 1 technical truth test before designing any project-specific showcases. It directly answers the only unresolved feasibility question: whether the approved Hong Kong telephoto move and Stanford arcade move can look genuinely photographic with capture-free source coverage.

No manual asset production from Eric is required. Eric's next input should be creative approval or rejection of the resulting four camera studies, not source gathering.
