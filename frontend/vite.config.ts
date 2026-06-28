import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const isPublic = env.VITE_PUBLIC_MODE === "true";
  const apiPort = env.VITE_API_PORT || (isPublic ? "8080" : "8081");
  const base = process.env.VITE_BASE_PATH || env.VITE_BASE_PATH || "/";

  return {
    base,
    plugins: [react(), tailwindcss()],
    server: {
      port: 5173,
      proxy: {
        "/api": isPublic
          ? {
              // Public backend mounts routes under /api — do not strip the prefix.
              target: `http://127.0.0.1:${apiPort}`,
              changeOrigin: true,
            }
          : {
              // Full PaperLens library backend uses bare paths (/papers, /categories, …).
              target: `http://127.0.0.1:${apiPort}`,
              changeOrigin: true,
              rewrite: (path) => path.replace(/^\/api/, ""),
            },
      },
    },
  };
});
