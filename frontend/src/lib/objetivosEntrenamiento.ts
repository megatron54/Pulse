/**
 * Nombres de los objetivos de un bloque de entrenamiento, en español y
 * en un solo sitio.
 *
 * El backend guarda texto libre (`objetivo_prioritario`, `String(50)`),
 * así que la etiqueta legible solo existe en el frontend. Estaba dentro
 * de `WeeklyScheduleForm` (el formulario que la escribe); al aparecer un
 * segundo consumidor que la LEE (`PlanesActivosCard`), o se comparte o
 * acaban siendo dos listas que divergen - el mismo problema que ya
 * resolvió `fasesNutricion.ts`.
 */
export const OBJETIVOS_ENTRENAMIENTO = [
  { valor: "fuerza", label: "Ganar fuerza" },
  { valor: "hipertrofia", label: "Ganar masa muscular" },
  { valor: "resistencia", label: "Mejorar resistencia" },
  { valor: "artes_marciales", label: "Artes marciales" },
  { valor: "recomposicion", label: "Recomposición corporal" },
  { valor: "mantenimiento", label: "Mantenerme" },
] as const;

/** Un plan creado antes de que existiera la lista de opciones (o desde
 *  la API a mano) puede traer cualquier cadena: se devuelve tal cual
 *  como último recurso, pero sin el "_" que delataría el formato
 *  interno en pantalla (doctrina 8). */
export function nombreObjetivo(valor: string): string {
  const conocido = OBJETIVOS_ENTRENAMIENTO.find((o) => o.valor === valor);
  return conocido ? conocido.label : valor.replace(/_/g, " ");
}
