import { forwardRef, useImperativeHandle, useLayoutEffect, useRef } from "react";
import * as THREE from "three";

export type DepthEnvironmentHandle = {
  setTravel: (progress: number) => void;
};

type DepthEnvironmentProps = {
  onReady?: () => void;
};

type CameraFrame = {
  at: number;
  position: THREE.Vector3;
  target: THREE.Vector3;
  fov: number;
};

type ReconstructionOptions = {
  colorSource: string;
  depthSource: string;
  center: THREE.Vector3;
  referenceCamera: THREE.Vector3;
  width: number;
  height: number;
  depthStrength: number;
  segmentsX: number;
  segmentsY: number;
};

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));
const smoothstep = (value: number) => {
  const t = clamp(value, 0, 1);
  return t * t * (3 - 2 * t);
};
const lerp = (start: number, end: number, amount: number) => start + (end - start) * amount;

function seededRandom(seed: number) {
  let state = seed >>> 0;
  return () => {
    state = (state * 1664525 + 1013904223) >>> 0;
    return state / 0xffffffff;
  };
}

function interpolateCamera(progress: number, frames: CameraFrame[]) {
  const value = clamp(progress, frames[0].at, frames[frames.length - 1].at);
  let right = frames.findIndex((frame) => frame.at >= value);
  if (right <= 0) right = 1;
  const left = right - 1;
  const start = frames[left];
  const end = frames[right];
  const amount = smoothstep((value - start.at) / (end.at - start.at));
  return {
    position: start.position.clone().lerp(end.position, amount),
    target: start.target.clone().lerp(end.target, amount),
    fov: lerp(start.fov, end.fov, amount),
  };
}

function loadDepthPixels(source: string, width: number, height: number) {
  return new Promise<Uint8ClampedArray>((resolve, reject) => {
    const image = new Image();
    image.decoding = "async";
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      if (!context) {
        reject(new Error(`Could not sample depth map: ${source}`));
        return;
      }
      context.drawImage(image, 0, 0, width, height);
      resolve(context.getImageData(0, 0, width, height).data);
    };
    image.onerror = () => reject(new Error(`Could not load depth map: ${source}`));
    image.src = source;
  });
}

function makeCloudTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 256;
  canvas.height = 256;
  const context = canvas.getContext("2d");
  if (context) {
    const gradient = context.createRadialGradient(128, 128, 2, 128, 128, 126);
    gradient.addColorStop(0, "rgba(255, 247, 238, .96)");
    gradient.addColorStop(0.28, "rgba(255, 239, 222, .78)");
    gradient.addColorStop(0.66, "rgba(237, 217, 201, .32)");
    gradient.addColorStop(1, "rgba(224, 205, 190, 0)");
    context.fillStyle = gradient;
    context.fillRect(0, 0, 256, 256);
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

function makeArchTexture() {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const context = canvas.getContext("2d");
  if (context) {
    context.clearRect(0, 0, 512, 512);
    const gradient = context.createLinearGradient(0, 0, 0, 512);
    gradient.addColorStop(0, "#070809");
    gradient.addColorStop(1, "#0c0d0e");
    context.fillStyle = gradient;
    context.shadowColor = "#090a0b";
    context.shadowBlur = 14;
    context.beginPath();
    context.moveTo(92, 512);
    context.lineTo(92, 226);
    context.arc(256, 226, 164, Math.PI, 0, false);
    context.lineTo(420, 512);
    context.closePath();
    context.fill();
  }
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  return texture;
}

export const DepthEnvironment = forwardRef<DepthEnvironmentHandle, DepthEnvironmentProps>(
  function DepthEnvironment({ onReady }, forwardedRef) {
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const renderTravelRef = useRef<(progress: number) => void>(() => undefined);

    useImperativeHandle(
      forwardedRef,
      () => ({ setTravel: (progress) => renderTravelRef.current(progress) }),
      [],
    );

    useLayoutEffect(() => {
      const canvas = canvasRef.current;
      if (!canvas) return;

      let renderer: THREE.WebGLRenderer;
      try {
        renderer = new THREE.WebGLRenderer({
          canvas,
          alpha: false,
          antialias: true,
          powerPreference: "high-performance",
        });
      } catch {
        canvas.dataset.webgl = "unavailable";
        onReady?.();
        return;
      }

      renderer.setPixelRatio(Math.min(window.devicePixelRatio, window.innerWidth < 768 ? 1.2 : 1.6));
      renderer.outputColorSpace = THREE.SRGBColorSpace;
      renderer.toneMapping = THREE.ACESFilmicToneMapping;
      renderer.toneMappingExposure = 1;

      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xc6a78e);
      const fog = new THREE.FogExp2(0xd9c0aa, 0.0005);
      scene.fog = fog;

      const camera = new THREE.PerspectiveCamera(35, 1, 0.1, 520);
      scene.add(camera);

      const textures = new Set<THREE.Texture>();
      const materials = new Set<THREE.Material>();
      const geometries = new Set<THREE.BufferGeometry>();
      const textureLoader = new THREE.TextureLoader();
      let cancelled = false;
      let currentTravel = 0;
      let ready = false;

      const createReconstruction = async (options: ReconstructionOptions) => {
        const sampleWidth = options.segmentsX + 1;
        const sampleHeight = options.segmentsY + 1;
        const [colorTexture, depthPixels] = await Promise.all([
          textureLoader.loadAsync(options.colorSource),
          loadDepthPixels(options.depthSource, sampleWidth, sampleHeight),
        ]);
        colorTexture.colorSpace = THREE.SRGBColorSpace;
        colorTexture.anisotropy = Math.min(8, renderer.capabilities.getMaxAnisotropy());
        textures.add(colorTexture);

        const geometry = new THREE.PlaneGeometry(
          options.width,
          options.height,
          options.segmentsX,
          options.segmentsY,
        );
        geometries.add(geometry);
        const positions = geometry.getAttribute("position") as THREE.BufferAttribute;
        const uvs = geometry.getAttribute("uv") as THREE.BufferAttribute;
        const base = new THREE.Vector3();
        const warped = new THREE.Vector3();

        for (let index = 0; index < positions.count; index += 1) {
          const pixelX = clamp(Math.round(uvs.getX(index) * options.segmentsX), 0, options.segmentsX);
          const pixelY = clamp(
            Math.round((1 - uvs.getY(index)) * options.segmentsY),
            0,
            options.segmentsY,
          );
          const u = uvs.getX(index);
          const v = uvs.getY(index);
          const edgeDistance = Math.min(u, 1 - u, v, 1 - v);
          const edgeFade = smoothstep(edgeDistance / 0.12);
          const depth = (depthPixels[(pixelY * sampleWidth + pixelX) * 4] / 255) * edgeFade;
          const rayAmount = 1 - depth * options.depthStrength;
          base.set(
            positions.getX(index) + options.center.x,
            positions.getY(index) + options.center.y,
            options.center.z,
          );
          warped.copy(options.referenceCamera).lerp(base, rayAmount);
          positions.setXYZ(index, warped.x, warped.y, warped.z);
        }
        positions.needsUpdate = true;
        geometry.computeBoundingBox();
        geometry.computeBoundingSphere();

        const material = new THREE.MeshBasicMaterial({
          map: colorTexture,
          toneMapped: false,
          side: THREE.DoubleSide,
          fog: true,
        });
        materials.add(material);
        const mesh = new THREE.Mesh(geometry, material);
        mesh.frustumCulled = false;
        scene.add(mesh);
        return mesh;
      };

      const cloudTexture = makeCloudTexture();
      textures.add(cloudTexture);
      const cloudMaterial = new THREE.SpriteMaterial({
        map: cloudTexture,
        color: 0xffead8,
        transparent: true,
        opacity: 0,
        depthWrite: false,
        fog: true,
      });
      const cloudDenseMaterial = cloudMaterial.clone();
      cloudDenseMaterial.color.set(0xf2ddca);
      materials.add(cloudMaterial);
      materials.add(cloudDenseMaterial);

      const clouds = new THREE.Group();
      const cloudRandom = seededRandom(2029);
      const cloudCenters = [
        new THREE.Vector3(15, 22, 20),
        new THREE.Vector3(35, 42, -5),
        new THREE.Vector3(65, 55, -52),
        new THREE.Vector3(100, 46, -82),
        new THREE.Vector3(132, 28, -103),
      ];
      cloudCenters.forEach((center, centerIndex) => {
        for (let index = 0; index < 22; index += 1) {
          const sprite = new THREE.Sprite(centerIndex > 0 && centerIndex < 4 ? cloudDenseMaterial : cloudMaterial);
          sprite.position.set(
            center.x + lerp(-18, 18, cloudRandom()),
            center.y + lerp(-10, 10, cloudRandom()),
            center.z + lerp(-15, 15, cloudRandom()),
          );
          const scale = lerp(0.8, 2.2, cloudRandom());
          sprite.scale.set(scale * lerp(12, 20, cloudRandom()), scale * lerp(6, 10, cloudRandom()), 1);
          clouds.add(sprite);
        }
      });
      scene.add(clouds);

      const archTexture = makeArchTexture();
      textures.add(archTexture);
      const archMaterial = new THREE.MeshBasicMaterial({
        map: archTexture,
        transparent: true,
        alphaTest: 0.01,
        depthTest: false,
        depthWrite: false,
        toneMapped: false,
      });
      materials.add(archMaterial);
      const archGeometry = new THREE.PlaneGeometry(2.2, 2.2);
      geometries.add(archGeometry);
      const archOccluder = new THREE.Mesh(archGeometry, archMaterial);
      archOccluder.position.set(0, -0.38, -3);
      archOccluder.renderOrder = 20;
      archOccluder.visible = false;
      camera.add(archOccluder);

      // The three photographs live in independent reconstructed coordinate
      // spaces. Keeping a separate camera path for each prevents the camera
      // from interpolating through empty space during a source change.
      const hongKongFrames: CameraFrame[] = [
        { at: 0, position: new THREE.Vector3(-4, 0, 70), target: new THREE.Vector3(-4, 0, -90), fov: 35 },
        { at: 0.19, position: new THREE.Vector3(2, 0.8, 64), target: new THREE.Vector3(2, 0, -90), fov: 33 },
        { at: 0.35, position: new THREE.Vector3(9, 2, 57), target: new THREE.Vector3(9, 1, -90), fov: 30 },
        { at: 0.47, position: new THREE.Vector3(10, 8, 52), target: new THREE.Vector3(10, 18, -90), fov: 36 },
      ];
      const bridgeFrames: CameraFrame[] = [
        { at: 0.47, position: new THREE.Vector3(10, 8, 52), target: new THREE.Vector3(10, 18, -90), fov: 36 },
        { at: 0.55, position: new THREE.Vector3(72, 30, -58), target: new THREE.Vector3(105, 34, -126), fov: 43 },
        { at: 0.63, position: new THREE.Vector3(160, 5, -110), target: new THREE.Vector3(160, 32, -170), fov: 34 },
      ];
      const churchFrames: CameraFrame[] = [
        { at: 0.63, position: new THREE.Vector3(160, 5, -110), target: new THREE.Vector3(160, 32, -170), fov: 34 },
        { at: 0.7, position: new THREE.Vector3(160, 2, -110), target: new THREE.Vector3(160, 12, -170), fov: 38 },
        { at: 0.76, position: new THREE.Vector3(160, 0, -110), target: new THREE.Vector3(160, -12, -170), fov: 40 },
        { at: 0.86, position: new THREE.Vector3(160, -2, -114), target: new THREE.Vector3(160, -25, -170), fov: 38 },
        { at: 0.9, position: new THREE.Vector3(160, -4, -120), target: new THREE.Vector3(160, -34, -170), fov: 36 },
        { at: 0.925, position: new THREE.Vector3(160, -5, -126), target: new THREE.Vector3(160, -42, -170), fov: 36 },
      ];
      const arcadeFrames: CameraFrame[] = [
        { at: 0.925, position: new THREE.Vector3(210, 0, -135), target: new THREE.Vector3(210, 8, -170), fov: 40 },
        { at: 0.955, position: new THREE.Vector3(205, 0, -122), target: new THREE.Vector3(210, 0, -170), fov: 43 },
        { at: 1, position: new THREE.Vector3(210, 0, -110), target: new THREE.Vector3(210, 0, -170), fov: 42 },
        { at: 1.08, position: new THREE.Vector3(216, 0, -116), target: new THREE.Vector3(216, 0, -170), fov: 44 },
      ];

      let hongKong: THREE.Mesh;
      let church: THREE.Mesh;
      let arcade: THREE.Mesh;

      const renderTravel = (progress: number) => {
        currentTravel = clamp(progress, 0, 1.08);
        const frame = currentTravel < 0.47
          ? interpolateCamera(currentTravel, hongKongFrames)
          : currentTravel < 0.63
            ? interpolateCamera(currentTravel, bridgeFrames)
            : currentTravel < 0.925
              ? interpolateCamera(currentTravel, churchFrames)
              : interpolateCamera(currentTravel, arcadeFrames);
        camera.position.copy(frame.position);
        camera.fov = frame.fov;
        camera.updateProjectionMatrix();
        camera.lookAt(frame.target);

        const cloudPeak = 1 - Math.min(1, Math.abs(currentTravel - 0.565) / 0.19);
        const cloudArrival = smoothstep((currentTravel - 0.34) / 0.12);
        const cloudDeparture = 1 - smoothstep((currentTravel - 0.71) / 0.1);
        const cloudPresence = cloudArrival * cloudDeparture;
        const fogExit = 1 - smoothstep((currentTravel - 0.585) / 0.045);
        fog.density = lerp(0.0005, 0.009, smoothstep(cloudPeak) * fogExit);
        cloudMaterial.opacity = 0.24 * cloudPresence;
        cloudDenseMaterial.opacity = 0.42 * cloudPresence;
        clouds.rotation.y = currentTravel * 0.052;
        clouds.position.y = (currentTravel - 0.5) * -8;

        if (ready) {
          hongKong.visible = currentTravel < 0.47;
          church.visible = currentTravel >= 0.63 && currentTravel < 0.925;
          arcade.visible = currentTravel >= 0.925;
        }
        const archEntering = smoothstep((currentTravel - 0.9) / 0.025);
        const archCoverage = currentTravel < 0.925
          ? lerp(0.08, 4.2, archEntering)
          : 4.2;
        archMaterial.opacity = currentTravel < 0.925
          ? 1
          : 1 - smoothstep((currentTravel - 0.928) / 0.022);
        archOccluder.visible = currentTravel > 0.895 && currentTravel < 0.96;
        archOccluder.scale.setScalar(archCoverage);
        renderer.render(scene, camera);
      };
      renderTravelRef.current = renderTravel;

      const resize = () => {
        const rect = canvas.getBoundingClientRect();
        const width = Math.max(1, Math.round(rect.width));
        const height = Math.max(1, Math.round(rect.height));
        renderer.setSize(width, height, false);
        camera.aspect = width / height;
        camera.updateProjectionMatrix();
        renderTravel(currentTravel);
      };
      const resizeObserver = new ResizeObserver(resize);
      resizeObserver.observe(canvas);
      resize();

      const segmentsX = window.innerWidth < 768 ? 96 : 160;
      const segmentsY = Math.round(segmentsX * 0.5625);
      void (async () => {
        try {
          [hongKong, church, arcade] = await Promise.all([
            createReconstruction({
              colorSource: "/media/depth/hong-kong.webp",
              depthSource: "/media/depth/hong-kong-depth.png",
              center: new THREE.Vector3(0, 0, -90),
              referenceCamera: new THREE.Vector3(0, 0, 70),
              width: 180,
              height: 120,
              depthStrength: 0.36,
              segmentsX,
              segmentsY,
            }),
            createReconstruction({
              colorSource: "/media/depth/stanford-church.webp",
              depthSource: "/media/depth/stanford-church-depth.png",
              center: new THREE.Vector3(160, 0, -170),
              referenceCamera: new THREE.Vector3(160, 0, -110),
              width: 240,
              height: 187.5,
              depthStrength: 0.31,
              segmentsX,
              segmentsY,
            }),
            createReconstruction({
              colorSource: "/media/depth/stanford-arcade.webp",
              depthSource: "/media/depth/stanford-arcade-depth.png",
              center: new THREE.Vector3(210, 0, -170),
              referenceCamera: new THREE.Vector3(210, 0, -110),
              width: 120,
              height: 80,
              depthStrength: 0.36,
              segmentsX,
              segmentsY,
            }),
          ]);
          if (cancelled) return;

          const skyTexture = await textureLoader.loadAsync("/media/depth/shared-sky.webp");
          skyTexture.colorSpace = THREE.SRGBColorSpace;
          textures.add(skyTexture);
          scene.background = skyTexture;

          ready = true;
          renderTravel(currentTravel);
          onReady?.();
        } catch (error) {
          console.error(error);
          canvas.dataset.webgl = "unavailable";
          onReady?.();
        }
      })();

      return () => {
        cancelled = true;
        resizeObserver.disconnect();
        renderTravelRef.current = () => undefined;
        textures.forEach((texture) => texture.dispose());
        geometries.forEach((geometry) => geometry.dispose());
        materials.forEach((material) => material.dispose());
        renderer.dispose();
      };
    }, [onReady]);

    return <canvas ref={canvasRef} className="world-canvas" aria-hidden="true" />;
  },
);
