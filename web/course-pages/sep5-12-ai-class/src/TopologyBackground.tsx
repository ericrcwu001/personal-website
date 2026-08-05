import { useEffect, useRef } from "react";

type Point = {
  baseX: number;
  baseY: number;
  phase: number;
  drift: number;
};

type Edge = {
  from: number;
  to: number;
  opacity: number;
  phase: number;
};

type Position = {
  x: number;
  y: number;
};

const lineColor = "62, 75, 75";

function seededValue(seed: number) {
  const value = Math.sin(seed * 12.9898) * 43758.5453;
  return value - Math.floor(value);
}

function createTopology(width: number, height: number) {
  const spacing = Math.max(84, Math.min(116, Math.round(Math.sqrt(width * height) / 10.8)));
  const points: Point[] = [];
  let row = 0;

  for (let y = -spacing; y <= height + spacing; y += spacing) {
    const rowOffset = row % 2 === 0 ? 0 : spacing * 0.5;

    for (let x = -spacing; x <= width + spacing; x += spacing) {
      const index = points.length + 1;
      const jitter = spacing * 0.16;

      points.push({
        baseX: x + rowOffset + (seededValue(index * 3) - 0.5) * jitter,
        baseY: y + (seededValue(index * 7) - 0.5) * jitter,
        phase: seededValue(index * 11) * Math.PI * 2,
        drift: 0.58 + seededValue(index * 17) * 0.42,
      });
    }

    row += 1;
  }

  const maximumDistance = spacing * 1.28;
  const maximumDistanceSquared = maximumDistance * maximumDistance;
  const edges: Edge[] = [];

  for (let from = 0; from < points.length; from += 1) {
    for (let to = from + 1; to < points.length; to += 1) {
      const xDistance = points[from].baseX - points[to].baseX;
      const yDistance = points[from].baseY - points[to].baseY;
      const distanceSquared = xDistance * xDistance + yDistance * yDistance;

      if (distanceSquared <= maximumDistanceSquared) {
        edges.push({
          from,
          to,
          opacity: 0.11 + seededValue((from + 1) * (to + 7)) * 0.1,
          phase: seededValue((from + 3) * (to + 11)) * Math.PI * 2,
        });
      }
    }
  }

  return { points, edges, spacing };
}

/**
 * A light canvas treatment inspired by topology maps. It stays behind the
 * course content and uses a still rendering when reduced motion is requested.
 */
export default function TopologyBackground({ disabled = false }: { disabled?: boolean }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");

    if (!canvas || !context) {
      return;
    }

    const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
    const finePointerQuery = window.matchMedia("(pointer: fine)");
    const pointer = { x: 0, y: 0, active: false };
    let reduced = disabled || motionQuery.matches;
    let width = 0;
    let height = 0;
    let devicePixelRatio = 1;
    let points: Point[] = [];
    let edges: Edge[] = [];
    let spacing = 120;
    let frame: number | null = null;
    const positions: Position[] = [];

    const pointPosition = (point: Point, now: number): Position => {
      const movement = reduced ? 0 : 13 * point.drift;
      const meshSway = reduced ? 0 : 7;
      let x =
        point.baseX +
        Math.sin(now * 0.00024 * point.drift + point.phase) * movement +
        Math.sin(now * 0.00012 + point.baseY * 0.01) * meshSway;
      let y =
        point.baseY +
        Math.cos(now * 0.00019 * point.drift + point.phase * 1.3) * movement +
        Math.cos(now * 0.0001 + point.baseX * 0.012) * meshSway;

      if (!reduced && pointer.active) {
        const xDistance = x - pointer.x;
        const yDistance = y - pointer.y;
        const distance = Math.hypot(xDistance, yDistance);
        const radius = Math.max(180, spacing * 1.8);

        if (distance > 0 && distance < radius) {
          const force = (1 - distance / radius) * 8;
          x += (xDistance / distance) * force;
          y += (yDistance / distance) * force;
        }
      }

      return { x, y };
    };

    const draw = (now: number) => {
      context.clearRect(0, 0, width, height);
      positions.length = 0;
      points.forEach((point) => positions.push(pointPosition(point, now)));

      context.lineWidth = 1;
      context.lineCap = "round";

      edges.forEach((edge) => {
        const from = positions[edge.from];
        const to = positions[edge.to];
        const pulse = reduced ? 1 : 0.72 + Math.sin(now * 0.0007 + edge.phase) * 0.28;

        context.strokeStyle = `rgba(${lineColor}, ${edge.opacity * pulse})`;
        context.beginPath();
        context.moveTo(from.x, from.y);
        context.lineTo(to.x, to.y);
        context.stroke();
      });

      context.fillStyle = `rgba(${lineColor}, ${reduced ? 0.16 : 0.17})`;
      positions.forEach((point) => {
        context.beginPath();
        context.arc(point.x, point.y, 1.15, 0, Math.PI * 2);
        context.fill();
      });
    };

    const render = (now: number) => {
      draw(now);
      frame = reduced ? null : window.requestAnimationFrame(render);
    };

    const start = () => {
      if (!reduced && frame === null) {
        frame = window.requestAnimationFrame(render);
      }
    };

    const stop = () => {
      if (frame !== null) {
        window.cancelAnimationFrame(frame);
        frame = null;
      }
    };

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      width = Math.max(1, Math.round(bounds.width));
      height = Math.max(1, Math.round(bounds.height));
      devicePixelRatio = Math.min(window.devicePixelRatio || 1, 1.5);

      canvas.width = Math.round(width * devicePixelRatio);
      canvas.height = Math.round(height * devicePixelRatio);
      context.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0);

      const topology = createTopology(width, height);
      points = topology.points;
      edges = topology.edges;
      spacing = topology.spacing;
      draw(performance.now());
      start();
    };

    const updateMotionPreference = () => {
      reduced = disabled || motionQuery.matches;

      if (reduced) {
        stop();
      }

      draw(performance.now());
      start();
    };

    const movePointer = (event: PointerEvent) => {
      if (!finePointerQuery.matches) {
        return;
      }

      pointer.x = event.clientX;
      pointer.y = event.clientY;
      pointer.active = true;
    };

    const clearPointer = () => {
      pointer.active = false;
    };

    resize();
    window.addEventListener("resize", resize, { passive: true });
    window.addEventListener("pointermove", movePointer, { passive: true });
    window.addEventListener("blur", clearPointer);
    motionQuery.addEventListener("change", updateMotionPreference);

    return () => {
      stop();
      window.removeEventListener("resize", resize);
      window.removeEventListener("pointermove", movePointer);
      window.removeEventListener("blur", clearPointer);
      motionQuery.removeEventListener("change", updateMotionPreference);
    };
  }, [disabled]);

  return <canvas ref={canvasRef} className="topology-background" aria-hidden="true" />;
}
