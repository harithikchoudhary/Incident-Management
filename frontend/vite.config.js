import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The FastAPI backend runs on port 8002. All /api calls are proxied there
// during development so the frontend can use same-origin relative URLs.
const BACKEND_URL = process.env.VITE_BACKEND_URL || "http://127.0.0.1:8002";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: BACKEND_URL,
        changeOrigin: true,
      },
    },
  },
});
