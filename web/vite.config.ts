import react from "@vitejs/plugin-react";
import cesium from "vite-plugin-cesium";
import { defineConfig } from "vitest/config";

function cesiumDevGlobal() {
  let serve = false;
  return {
    name: "cesium-dev-global",
    enforce: "pre" as const,
    config(_cfg: unknown, env: { command: string }) {
      serve = env.command === "serve";
      return {
        optimizeDeps: {
          exclude: ["cesium", "satellite.js"],
        },
      };
    },
    resolveId(id: string) {
      if (serve && id === "cesium") {
        return "\0cesium-global";
      }
      return undefined;
    },
    load(id: string) {
      if (id === "\0cesium-global") {
        return `
          const c = window.Cesium;
          export const Cartesian2 = c.Cartesian2;
          export const Cartesian3 = c.Cartesian3;
          export const Color = c.Color;
          export const ConstantPositionProperty = c.ConstantPositionProperty;
          export const EllipsoidTerrainProvider = c.EllipsoidTerrainProvider;
          export const ImageryLayer = c.ImageryLayer;
          export const OpenStreetMapImageryProvider = c.OpenStreetMapImageryProvider;
          export const Viewer = c.Viewer;
        `;
      }
      const normalized = id.replaceAll("\\", "/");
      if (normalized.includes("satellite.js/wasm-build")) {
        return "export default {}";
      }
      return undefined;
    },
    transformIndexHtml() {
      if (!serve) {
        return [];
      }
      return [
        {
          tag: "script",
          attrs: { src: "/cesium/Cesium.js" },
        },
      ];
    },
  };
}

export default defineConfig({
  plugins: [
    react(),
    cesium(),
    cesiumDevGlobal(),
  ],
  server: {
    proxy: {
      "/api/celestrak": {
        target: "https://celestrak.org",
        changeOrigin: true,
        rewrite: (path) =>
          path.replace(/^\/api\/celestrak/, "/NORAD/elements"),
      },
    },
  },
  test: {
    environment: "jsdom",
  },
});
