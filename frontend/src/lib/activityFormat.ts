/**
 * Formato compartido de actividades Garmin, usado tanto por
 * `GarminActivitiesCard` (lista sin filtrar de `/garmin`) como por
 * `SportActivityHistoryCard` (Épica G, páginas por deporte) - extraído
 * para no duplicar esta lógica en dos componentes (hallazgo de
 * @code-reviewer).
 */
export function formatDuracion(seg: number | null): string {
  if (seg === null) return "—";
  const minutos = Math.round(seg / 60);
  return `${minutos} min`;
}

export function formatDistancia(m: number | null): string {
  if (m === null) return "—";
  return `${(m / 1000).toFixed(1)} km`;
}
