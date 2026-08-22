import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/collectors": "http://127.0.0.1:8000",
      "/products": "http://127.0.0.1:8000",
      "/incidents": "http://127.0.0.1:8000",
      "/alerts": "http://127.0.0.1:8000",
      "/research": "http://127.0.0.1:8000",
      "/rag": "http://127.0.0.1:8000",
      "/me": "http://127.0.0.1:8000",
      "/insights": "http://127.0.0.1:8000",
      "/operations": "http://127.0.0.1:8000",
      "/health": "http://127.0.0.1:8000",
    },
  },
  preview: { port: 4173 },
});
