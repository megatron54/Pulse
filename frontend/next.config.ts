import type { NextConfig } from "next";

// Épica K del plan de expansión (02-roadmap/03-vision-produccion.md,
// 00-research/09-app-nativa-escritorio.md): prueba de concepto de Tauri.
// Tauri exige exportación estática ("Tauri doesn't support server-based
// solutions", docs oficiales) - se activa SOLO con TAURI_BUILD=1 para no
// romper el build de producción actual (Docker/`next start`, ya probado
// en CI) mientras la migración sigue siendo solo una prueba de concepto,
// no la vía de producción decidida.
const esBuildDeTauri = process.env.TAURI_BUILD === "1";
const tauriDevHost = process.env.TAURI_DEV_HOST || "localhost";

const nextConfig: NextConfig = {
  ...(esBuildDeTauri && {
    output: "export",
    images: { unoptimized: true },
    assetPrefix: process.env.NODE_ENV === "production" ? undefined : `http://${tauriDevHost}:3000`,
    // El worker de chequeo de tipos de `next build` usa un binding
    // nativo que revienta en esta máquina Windows concreta con
    // "invalid type: unit value, expected usize" (mismo tipo de bug ya
    // documentado para SWC/Turbopack en 00-research/
    // 09-app-nativa-escritorio.md, sin relación con el código de
    // Pulse) - se omite SOLO en el build de escritorio (Tauri), nunca
    // en el build de producción normal (Docker), que no define
    // TAURI_BUILD y ya corre `tsc --noEmit` aparte en CI.
    typescript: { ignoreBuildErrors: true },
  }),
};

export default nextConfig;
