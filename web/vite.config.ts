import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
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
