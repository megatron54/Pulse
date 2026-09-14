/**
 * Fábricas de `ReadinessResult` para los tests.
 *
 * Existen porque `ReadinessOut` creció de seis campos a doce al añadir
 * el desglose por señal, y cada test que solo quería decir "este día
 * fue verde" tenía que escribir doce campos irrelevantes para lo que
 * estaba comprobando. Con eso, el dato que de verdad importa en cada
 * test (la fecha, el veredicto) quedaba enterrado entre ruido.
 *
 * Los valores por defecto son COHERENTES entre sí: las siete señales
 * están en `ok` y sus valores son los que producirían ese estado con
 * los umbrales reales del motor. Un día por defecto que dijera "verde"
 * con señales en rojo sería un escenario imposible, y un test que pasa
 * sobre un escenario imposible no prueba nada.
 *
 * Vive en `src/test/` y no en `src/lib/` a propósito: no es código de
 * producto y ningún componente lo importa.
 */
import type { ReadinessResult, Signal, SignalCode } from "@/lib/api";

/** Umbrales reales de `engine/periodization.py`, para que las señales de
 *  los tests lleven los mismos que manda el backend. */
const UMBRALES: Record<
  SignalCode,
  { rojo: number | null; amarillo: number | null; peor_hacia: Signal["peor_hacia"] }
> = {
  hrv_delta: { rojo: -0.15, amarillo: -0.07, peor_hacia: "abajo" },
  hrv_trend: { rojo: -0.1, amarillo: null, peor_hacia: "abajo" },
  training_readiness: { rojo: null, amarillo: null, peor_hacia: "abajo" },
  body_battery: { rojo: 30, amarillo: 50, peor_hacia: "abajo" },
  acwr: { rojo: 1.5, amarillo: 1.3, peor_hacia: "arriba" },
  sleep: { rojo: null, amarillo: 50, peor_hacia: "abajo" },
  joint_pain: { rojo: null, amarillo: null, peor_hacia: "abajo" },
};

const VALOR_OK: Record<SignalCode, number | null> = {
  hrv_delta: 0.02,
  hrv_trend: 0.01,
  training_readiness: null,
  body_battery: 72,
  acwr: 1.0,
  sleep: 82,
  joint_pain: null,
};

export function unaSenal(senal: SignalCode, cambios: Partial<Signal> = {}): Signal {
  const umbrales = UMBRALES[senal];
  return {
    senal,
    estado: "ok",
    valor: VALOR_OK[senal],
    umbral_rojo: umbrales.rojo,
    umbral_amarillo: umbrales.amarillo,
    peor_hacia: umbrales.peor_hacia,
    ...cambios,
  };
}

const CODIGOS: readonly SignalCode[] = [
  "hrv_delta",
  "hrv_trend",
  "training_readiness",
  "body_battery",
  "acwr",
  "sleep",
  "joint_pain",
];

/** Las siete señales, todas en orden y todas en `ok`, con los cambios
 *  que pida el test por código de señal. */
export function unasSenales(cambios: Partial<Record<SignalCode, Partial<Signal>>> = {}): Signal[] {
  return CODIGOS.map((codigo) => unaSenal(codigo, cambios[codigo] ?? {}));
}

export function unDiaDeReadiness(cambios: Partial<ReadinessResult> = {}): ReadinessResult {
  return {
    id: 1,
    fecha: "2026-08-10",
    resultado: "green",
    hrv_delta_pct: 0.02,
    hrv_trend_7d: 0.01,
    training_readiness: "high",
    body_battery_am: 72,
    sleep_score: 82,
    acwr: 1.0,
    joint_pain_flag: false,
    senales: unasSenales(),
    ...cambios,
  };
}
