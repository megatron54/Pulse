/**
 * Formato de fechas y selección del registro más reciente.
 *
 * `masRecientePorFecha` existe por un bug real, no por gusto: el hero de
 * "Hoy" mostraba durante semanas los datos de hace 7 días etiquetados
 * como de hoy. `GET /garmin/health-history` devuelve orden DESCENDENTE
 * ("más reciente primero", según su propio docstring) pero el
 * componente leía `historial.at(-1)` - el más ANTIGUO de la ventana -
 * porque ese `.at(-1)` venía de otro endpoint (`readiness/history`, sí
 * ascendente) y se copió sin comprobar el orden del nuevo.
 *
 * La lección: no depender del orden de la respuesta, porque el tipo de
 * TypeScript no lo expresa y nada avisa cuando cambia. Se elige por
 * fecha máxima, que es correcto con cualquier orden.
 */

const MS_POR_DIA = 86_400_000;

export function masRecientePorFecha<T extends { fecha: string }>(items: readonly T[]): T | null {
  if (items.length === 0) return null;
  return items.reduce((masReciente, item) =>
    item.fecha > masReciente.fecha ? item : masReciente
  );
}

/** Fecha ISO (`YYYY-MM-DD`) a fecha local, sin desfase de zona horaria.
 *  `new Date("2026-09-13")` se interpreta como UTC y en husos negativos
 *  retrocede un día - de ahí el desglose manual. */
function aFechaLocal(iso: string): Date {
  const [anio, mes, dia] = iso.split("-").map(Number);
  return new Date(anio, mes - 1, dia);
}

/** Días transcurridos desde `iso` hasta hoy (0 = hoy). Público porque
 *  hay tarjetas que necesitan avisar de que su dato está viejo: la de
 *  objetivo corporal hablaba de "los últimos 30 días" cuando la última
 *  pesada era de hacía 75. */
export function diasDesdeHoy(iso: string): number {
  const hoy = new Date();
  const inicioHoy = new Date(hoy.getFullYear(), hoy.getMonth(), hoy.getDate());
  return Math.round((inicioHoy.getTime() - aFechaLocal(iso).getTime()) / MS_POR_DIA);
}

// Abreviaturas propias en vez de `toLocaleDateString(..., {month:"short"})`:
// su salida depende de la versión de ICU del entorno (Node devuelve
// "sept" para septiembre, algunos navegadores "sep.") y eso hace que la
// misma fecha se escriba distinto en el servidor y en el cliente.
const MESES_ABREVIADOS = [
  "ene", "feb", "mar", "abr", "may", "jun",
  "jul", "ago", "sep", "oct", "nov", "dic",
] as const;

/** "12 sep" - sin año cuando es del año en curso. */
export function fechaCorta(iso: string): string {
  const fecha = aFechaLocal(iso);
  const base = `${fecha.getDate()} ${MESES_ABREVIADOS[fecha.getMonth()]}`;
  return fecha.getFullYear() === new Date().getFullYear()
    ? base
    : `${base} ${fecha.getFullYear()}`;
}

/** "Hoy" / "Ayer" / "12 sep" - nunca ISO en la interfaz (doctrina 9). */
export function fechaRelativa(iso: string): string {
  const dias = diasDesdeHoy(iso);
  if (dias === 0) return "Hoy";
  if (dias === 1) return "Ayer";
  return fechaCorta(iso);
}

/** Fecha ISO de `dias` días antes de `iso`. Para ventanas ancladas a un
 *  dato real y no al calendario ("los 30 días anteriores a la última
 *  pesada"), que es la única forma de que la ventana no salga vacía
 *  cuando el usuario lleva semanas sin registrar nada. */
export function fechaMenosDias(iso: string, dias: number): string {
  const fecha = aFechaLocal(iso);
  fecha.setDate(fecha.getDate() - dias);
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

/** Concordancia de plural resuelta: la auditoría encontró "1 días con
 *  dato" en la tarjeta de peso. */
export function plural(cantidad: number, singular: string, plural_: string): string {
  return `${cantidad} ${cantidad === 1 ? singular : plural_}`;
}
