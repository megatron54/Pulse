import { redirect } from "next/navigation";

/**
 * Ruta fusionada dentro de /entrenamiento (pestaña "Análisis") - ver
 * docstring de src/app/entrenamiento/page.tsx. Se mantiene este
 * redirect en vez de borrar la ruta para no romper enlaces/bookmarks
 * existentes a /analisis.
 */
export default function AnalisisPage() {
  redirect("/entrenamiento");
}
