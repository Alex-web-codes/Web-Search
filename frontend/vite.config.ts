import path from "node:path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"

// `npm run build` writes straight into gui/static, which the Python server serves.
// `npm run dev` proxies /api to `python run.py` on port 8000.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: { "@": path.resolve(import.meta.dirname, "src") },
  },
  build: {
    outDir: path.resolve(import.meta.dirname, "../gui/static"),
    emptyOutDir: true,
  },
  server: {
    proxy: { "/api": "http://127.0.0.1:8000" },
  },
})
