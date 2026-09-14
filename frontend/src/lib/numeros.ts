/** Espacio fino irrompible (U+202F): separador de miles. */
const ESPACIO_FINO = " ";

/**
 * Formatea una cifra para leerla, no para depurarla.
 *
 * Hallazgo de la auditoría v3: los pasos del día se mostraban como
 * `13893`, cinco dígitos seguidos que hay que contar con el dedo para
 * saber si son trece mil o ciento treinta y ocho mil.
 *
 * El separador es un espacio fino irrompible y NO un punto: la app
 * escribe los decimales con punto (`78.4 kg`), así que "13.893" sería
 * ambiguo. El espacio es además lo que recomienda la RAE para agrupar
 * miles, y al ser irrompible nunca parte la cifra en dos líneas.
 *
 * Por debajo de 10 000 no se agrupa nada (ISO 80000-1 lo deja opcional
 * para cuatro dígitos): "2 450 kcal" se lee peor que "2450 kcal".
 */
export function formatNumero(valor: number, decimales = 0): string {
  const texto = valor.toFixed(decimales);
  if (Math.abs(valor) < 10_000) return texto;
  const [entera, decimal] = texto.split(".");
  const agrupada = entera.replace(/\B(?=(\d{3})+(?!\d))/g, ESPACIO_FINO);
  return decimal ? `${agrupada}.${decimal}` : agrupada;
}
