import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
    // Épica K (02-roadmap/03-vision-produccion.md): artefactos de build
    // de Rust/Tauri (scaffolding de la prueba de concepto) - nunca son
    // código fuente propio, no deben lintarse.
    "src-tauri/target/**",
  ]),
]);

export default eslintConfig;
