import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// During development the page is served by Vite (port 5173) and forwards
// /stt (WebSocket) and /tts to the web-voice-kit server on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/stt": { target: "ws://localhost:8000", ws: true },
      "/tts": { target: "http://localhost:8000" },
    },
  },
});
