import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { readFileSync } from "node:fs";
import { fileURLToPath, URL } from "node:url";
import { defineConfig, type Plugin } from "vite";

// Dev server only: serve the data.json and downloads of the last `pdc build`.
function runData(): Plugin {
  const site = fileURLToPath(new URL("../build/site/", import.meta.url));
  return {
    name: "pdc-run-data",
    apply: "serve",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const path = (req.url ?? "").split("?")[0];
        if (path !== "/data.json") return next();
        try {
          res.setHeader("Content-Type", "application/json; charset=utf-8");
          res.end(readFileSync(`${site}data.json`));
        } catch {
          res.statusCode = 404;
          res.end();
        }
      });
    },
  };
}

// The build lands inside the Python package, so `uv run pdc build` and `pdc serve`
// work without Node. `pdc build` copies it next to data.json.
export default defineConfig({
  base: "./",
  plugins: [react(), tailwindcss(), runData()],
  resolve: { alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) } },
  build: {
    outDir: "../src/product_data_checker/dashboard/web",
    emptyOutDir: true,
    assetsInlineLimit: 0, // fonts and icons stay files: the CSP allows no data: fonts
    modulePreload: { polyfill: false }, // no inline helper script
    chunkSizeWarningLimit: 1200,
    rolldownOptions: {
      output: {
        // vendor libraries in their own files: they change rarely and cache well
        codeSplitting: {
          groups: [
            { name: "react", test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
            { name: "charts", test: /node_modules[\\/](recharts|d3-[^\\/]+|victory-vendor|internmap|decimal\.js-light|@reduxjs|redux|reselect|immer|es-toolkit|eventemitter3)[\\/]/ },
            { name: "motion", test: /node_modules[\\/](motion|framer-motion|motion-dom|motion-utils)[\\/]/ },
            { name: "ui", test: /node_modules[\\/](@radix-ui|@floating-ui|lucide-react|class-variance-authority|clsx|tailwind-merge)[\\/]/ },
          ],
        },
        // stable font name: the server's error page (public/error.css) loads it too
        assetFileNames: (info) =>
          info.names?.some((n) => n.endsWith(".woff2")) ? "assets/[name][extname]" : "assets/[name]-[hash][extname]",
      },
    },
  },
  server: { port: 5230, strictPort: false },
});
