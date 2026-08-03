/**
 * Colapsa una serie append-only (varias filas por fecha permitidas,
 * ver docstrings de get_weight_history/get_readiness_history en el
 * backend) a una sola fila por fecha, quedándose con el `id` más alto
 * de cada día.
 *
 * Deliberadamente NO depende del orden de llegada del array (aunque el
 * backend hoy entrega orden cronológico ascendente con desempate por
 * id ascendente) - comparar `id` explícitamente hace que este cálculo
 * sea correcto sin importar si esa garantía de orden cambiara alguna
 * vez en la API (code-review: acoplamiento silencioso entre capas es
 * un modo de fallo peligroso para un tracker de salud).
 */
export function dedupeUltimaPorDia<T extends { fecha: string; id: number }>(
  filas: T[]
): T[] {
  const porFecha = new Map<string, T>();
  for (const fila of filas) {
    const anterior = porFecha.get(fila.fecha);
    if (!anterior || fila.id > anterior.id) {
      porFecha.set(fila.fecha, fila);
    }
  }
  return Array.from(porFecha.values());
}
