import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Vite defaults to binding only 127.0.0.1 -- Codespaces' port-forwarding
    // proxy connects from outside that loopback scope, so without this the
    // forwarded URL 404s at GitHub's own proxy even though Vite is running fine.
    host: true,
    proxy: {
      "/api": "http://localhost:8000",
    },
    watch: {
      // Chokidar's native fs events are unreliable across the Windows-host <-> container
      // bind mount used by this devcontainer, so edits saved from the host can silently
      // never trigger HMR. Polling guarantees change detection at the cost of a bit of CPU.
      usePolling: true,
      interval: 300,
    },
  },
});
