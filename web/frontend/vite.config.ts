// web/frontend/vite.config.ts
import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, "../", "");
  return {
    plugins: [react()],
    server: {
      port: Number(env.FRONTEND_PORT) || 5173,
      proxy: {
        "/api": {
          target: `http://localhost:${env.BACKEND_PORT || 8000}`,
          changeOrigin: true,
          configure: (proxy) => {
            proxy.on("proxyRes", (res) => {
              if (res.headers["content-type"]?.includes("text/event-stream")) {
                res.headers["cache-control"] = "no-cache";
                res.headers["x-accel-buffering"] = "no";
              }
            });
          },
        },
      },
    },
  };
});
