/**
 * Rango de referencia para las cifras de composición corporal que SÍ
 * tienen un umbral poblacional reconocido y normalizado (independiente
 * de la altura o la complexión de cada persona). Deliberadamente NO
 * cubre peso, músculo (kg) ni hueso (kg): son cifras absolutas sin una
 * banda universal válida, y el propio proyecto ya rechaza la precisión
 * falsa en este mismo archivo (`BodyCompositionTile`, comentario sobre
 * el rango Navy). Inventar un umbral de "hueso normal" en kg sin
 * normalizar por altura sería mentir con una cifra que parece objetiva
 * y no lo es.
 *
 * Fuentes:
 *  - IMC: categorías de la OMS (bajo peso / normal / sobrepeso /
 *    obesidad), iguales para ambos sexos.
 *  - % de grasa corporal: bandas de ACE (American Council on Exercise),
 *    con "atlético" y "fitness" fusionados en un único rango "normal"
 *    porque para este uso (báscula doméstica, no un estudio deportivo)
 *    la distinción no aporta.
 *  - % de agua corporal: rango normal de Tanita/InBody para báscula de
 *    bioimpedancia (50–65 % hombres, 45–60 % mujeres). Solo se marca
 *    "bajo" por debajo del rango: un agua corporal alta no es un
 *    problema de salud conocido (suele ir con poca grasa), así que
 *    marcarla en amarillo/rojo sería inventar un riesgo que no existe -
 *    por eso el agua nunca devuelve "alto"/"muy_alto".
 */
export type EstadoRango = "bajo" | "normal" | "alto" | "muy_alto";

/** Clase de texto del token semántico de cada estado. "bajo" reutiliza
 *  `--data` (el único azul de la paleta) en vez de sumar un token
 *  nuevo: aquí significa "por debajo del rango", nunca una serie de
 *  gráfica, pero es el mismo azul discreto en ambos usos. */
export const CLASE_POR_ESTADO: Record<EstadoRango, string> = {
  bajo: "text-data",
  normal: "text-pos",
  alto: "text-warn",
  muy_alto: "text-neg",
};

export function estadoImc(imc: number): EstadoRango {
  if (imc < 18.5) return "bajo";
  if (imc < 25) return "normal";
  if (imc < 30) return "alto";
  return "muy_alto";
}

export function estadoGrasaCorporal(pct: number, sexo: "M" | "F"): EstadoRango {
  if (sexo === "M") {
    if (pct < 8) return "bajo";
    if (pct < 20) return "normal";
    if (pct < 25) return "alto";
    return "muy_alto";
  }
  if (pct < 18) return "bajo";
  if (pct < 30) return "normal";
  if (pct < 35) return "alto";
  return "muy_alto";
}

export function estadoAguaCorporal(pct: number, sexo: "M" | "F"): EstadoRango {
  const minimo = sexo === "M" ? 50 : 45;
  return pct < minimo ? "bajo" : "normal";
}
