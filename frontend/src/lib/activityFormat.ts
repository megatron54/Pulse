/**
 * Formato de actividades de Garmin, compartido por la tabla de sesiones
 * y por la gráfica de volumen semanal.
 *
 * Dos cambios de v3, los dos por hallazgos de la auditoría:
 *
 *  - **`formatDistancia` devuelve `null`, no "—" ni "0.0 km".** Las
 *    sesiones de fuerza no tienen distancia; v2 pintaba "0.0 km" en cada
 *    una, que no es un dato desconocido presentado como tal sino un cero
 *    inventado (doctrina 6). Quien decide cómo representar la ausencia
 *    es la celda de la tabla (`TdNum`), no el formateador.
 *  - **`nombreActividad` traduce el `typeKey` crudo de Garmin.** La
 *    interfaz mostraba "strength training", "indoor cycling" y hasta
 *    "lap swimming" en inglés y en minúscula, con un `capitalize` de CSS
 *    por encima que además produce "Strength Training" a la inglesa. La
 *    app está en español (doctrina 9).
 */

/** `typeKey` de Garmin -> nombre en español. Se comparan los tipos más
 *  frecuentes de forma exacta y el resto por palabra clave, porque el
 *  catálogo de Garmin es largo y cambia. */
const NOMBRES: Record<string, string> = {
  running: "Carrera",
  treadmill_running: "Carrera en cinta",
  trail_running: "Trail",
  indoor_running: "Carrera en interior",
  track_running: "Carrera en pista",
  cycling: "Ciclismo",
  road_biking: "Ciclismo en carretera",
  indoor_cycling: "Ciclismo en interior",
  virtual_ride: "Ciclismo virtual",
  mountain_biking: "Bici de montaña",
  gravel_cycling: "Gravel",
  strength_training: "Fuerza",
  indoor_cardio: "Cardio en interior",
  hiit: "HIIT",
  yoga: "Yoga",
  pilates: "Pilates",
  walking: "Caminata",
  hiking: "Senderismo",
  lap_swimming: "Natación en piscina",
  open_water_swimming: "Natación en aguas abiertas",
  rowing: "Remo",
  indoor_rowing: "Remo en interior",
  elliptical: "Elíptica",
  stair_climbing: "Escalones",
  mixed_martial_arts: "Artes marciales",
  boxing: "Boxeo",
};

const POR_PALABRA: readonly [string, string][] = [
  ["run", "Carrera"],
  ["cycl", "Ciclismo"],
  ["bik", "Ciclismo"],
  ["swim", "Natación"],
  ["strength", "Fuerza"],
  ["walk", "Caminata"],
  ["hik", "Senderismo"],
  ["row", "Remo"],
  ["cardio", "Cardio"],
  ["yoga", "Yoga"],
];

export function nombreActividad(tipo: string): string {
  const clave = tipo.toLowerCase();
  const exacto = NOMBRES[clave];
  if (exacto) return exacto;
  for (const [palabra, nombre] of POR_PALABRA) {
    if (clave.includes(palabra)) return nombre;
  }
  // Último recurso: el tipo crudo legible (nunca se oculta la actividad
  // por no saber traducir su nombre).
  const legible = clave.replace(/_/g, " ");
  return legible.charAt(0).toUpperCase() + legible.slice(1);
}

/** "1 h 12 min" / "45 min". Las horas se separan porque "132 min" obliga
 *  al usuario a dividir mentalmente. */
export function formatDuracion(seg: number | null): string | null {
  if (seg === null) return null;
  const minutosTotales = Math.round(seg / 60);
  if (minutosTotales < 60) return `${minutosTotales} min`;
  const horas = Math.floor(minutosTotales / 60);
  const minutos = minutosTotales % 60;
  return minutos === 0 ? `${horas} h` : `${horas} h ${minutos} min`;
}

export function formatDistancia(m: number | null): string | null {
  if (m === null || m === 0) return null;
  return `${(m / 1000).toFixed(1)} km`;
}
