import { defineConfig } from "vite";

export default defineConfig({
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/requirements": "http://localhost:8000",
      "/epics": "http://localhost:8000",
      "/stories": "http://localhost:8000",
      "/jira": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
