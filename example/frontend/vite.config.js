import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// base "/" -> assets are referenced absolutely (/assets/app.[hash].js), which is
// exactly what django-spa serves at the root mount.
export default defineConfig({
  base: "/",
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
