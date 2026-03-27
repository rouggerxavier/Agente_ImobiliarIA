import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react-swc";
import path from "path";
import { componentTagger } from "lovable-tagger";

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const backendTarget = (env.VITE_BACKEND_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

  return {
    server: {
      host: "::",
      port: 8080,
      proxy: {
        "/webhook": {
          target: backendTarget,
          changeOrigin: true,
        },
        "/health": {
          target: backendTarget,
          changeOrigin: true,
        },
        "/imoveis": {
          target: backendTarget,
          changeOrigin: true,
        },
        "/imoveis-img": {
          target: backendTarget,
          changeOrigin: true,
        },
      },
      hmr: {
        overlay: false,
      },
    },
    plugins: [react(), mode === "development" && componentTagger()].filter(Boolean),
    optimizeDeps: {
      include: ["react", "react-dom"],
    },
    resolve: {
      dedupe: ["react", "react-dom"],
      alias: {
        "@": path.resolve(__dirname, "./src"),
      },
    },
  };
});
