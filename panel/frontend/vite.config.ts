import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

const backend = "http://localhost:8080";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": { target: backend, changeOrigin: true, ws: true },
      "/grafana": { target: backend, changeOrigin: true, ws: true },
    },
  },
  build: { outDir: "dist" },
  test: { environment: "jsdom", globals: false },
});
