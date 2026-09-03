import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Configurazione Vite: durante lo sviluppo locale (npm run dev) le chiamate
// a /api vengono inoltrate al backend FastAPI in esecuzione su localhost:8000.
// In produzione (Docker) e' invece nginx a fare da reverse proxy verso il
// container backend (vedi frontend/nginx.conf).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
