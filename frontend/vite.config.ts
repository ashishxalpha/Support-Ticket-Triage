import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '');
  const frontendUrl = env.FRONTEND_URL || process.env.FRONTEND_URL || 'http://localhost:5173';
  
  let allowedHost = undefined;
  try {
    const hostname = new URL(frontendUrl).hostname;
    if (hostname !== 'localhost') {
      allowedHost = [hostname];
    }
  } catch (e) {
    console.error("Invalid FRONTEND_URL:", frontendUrl);
  }

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
    server: {
      port: 5173,
      host: true,
      allowedHosts: allowedHost,
      proxy: {
        "/api": {
          target: "http://localhost:8000",
          changeOrigin: true,
        },
      },
    },
  };
});
