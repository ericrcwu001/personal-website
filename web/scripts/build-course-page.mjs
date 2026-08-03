import { rmSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import react from "@vitejs/plugin-react";
import { build } from "vite";

const scriptsDir = dirname(fileURLToPath(import.meta.url));
const webRoot = resolve(scriptsDir, "..");
const pageRoot = resolve(webRoot, "course-pages/sep5-12-ai-class");
const outDir = resolve(webRoot, "public/sep5-12-ai-class");

rmSync(outDir, { recursive: true, force: true });

await build({
  base: "/sep5-12-ai-class/",
  build: {
    emptyOutDir: true,
    outDir,
  },
  plugins: [react()],
  root: pageRoot,
});
