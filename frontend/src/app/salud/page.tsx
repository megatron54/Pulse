import { redirect } from "next/navigation";

/**
 * Ruta fusionada dentro de /entrenamiento (pestaña "Recuperación") -
 * ver docstring de src/app/entrenamiento/page.tsx. Se mantiene este
 * redirect en vez de borrar la ruta para no romper enlaces/bookmarks
 * existentes a /salud.
 */
export default function SaludPage() {
  redirect("/entrenamiento");
}
