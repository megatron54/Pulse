/**
 * Nombres y explicaciones de las fases de peso, en español y en un solo
 * sitio.
 *
 * El backend las nombra en inglés (`cut`, `maintenance`, `recomp`,
 * `surplus`, ver `WeightPhase`) y v2 traducía cada una a mano en cada
 * componente: la tarjeta de objetivo mostraba la cadena cruda
 * ("Fase aplicada: cut") y la de plan tenía su propio diccionario. Dos
 * traducciones del mismo dato es una que se queda atrás.
 */
export const FASES_NUTRICION: Record<string, { label: string; explicacion: string }> = {
  cut: {
    label: "Déficit",
    explicacion: "Comes por debajo de tu gasto para bajar grasa manteniendo la fuerza.",
  },
  maintenance: {
    label: "Mantenimiento",
    explicacion: "Comes en torno a tu gasto: el peso se queda donde está.",
  },
  recomp: {
    label: "Recomposición",
    explicacion:
      "Cerca de tu gasto y con proteína alta, para cambiar composición sin mover el peso.",
  },
  surplus: {
    label: "Superávit",
    explicacion: "Comes por encima de tu gasto para ganar masa.",
  },
};

/** Nunca deja ver la cadena cruda del backend si apareciera una fase
 *  nueva: devuelve la clave tal cual solo como último recurso. */
export function nombreFase(fase: string): string {
  return FASES_NUTRICION[fase]?.label ?? fase;
}
