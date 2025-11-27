import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
        secure: false,
        rewrite: (path) => path,
      },
    },
    port: 5173,
    host: "0.0.0.0", // Izinkan akses dari jaringan
    cors: true,
  },
  define: {
    // Global constant untuk mendapatkan IP otomatis
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version),
  },
});
