# Eric Wu portfolio

Scroll-driven personal site built with React, Vite, GSAP, and Three.js. The
opening is one real-time 3D world with a scroll-controlled camera: Braemar Hill,
a cloud-covered geographic jump, Memorial Church, and a Main Quad arcade. A
local Depth Anything model converts the approved source photography into dense
depth meshes, so camera motion produces genuine perspective and parallax rather
than rotating flat image planes. The recognizable architecture remains sourced
from real photographs instead of procedural low-poly substitutes.

## Run locally

```sh
npm install
npm run dev
```

Open `http://127.0.0.1:4173/`. If the browser or operating system requests reduced motion, use `http://127.0.0.1:4173/?motion=1` to review the full cinematic sequence.

## Build

```sh
npm run build
```

The production output is written to `dist/`.

Project titles live in `src/data/projects.ts`. The project routes intentionally use placeholders until their individual showcases are designed.

## Scene implementation

`src/components/DepthEnvironment.tsx` owns both locations and the complete
camera path. Hong Kong and Stanford never dissolve into one another: the camera
cranes through a dense 3D cloud volume, and the inactive reconstruction switches
only while the frame is occluded. `scripts/generate_depth_assets.py` regenerates
the source-grounded color/depth pairs used by the browser.
