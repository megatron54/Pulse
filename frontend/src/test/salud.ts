import type { GarminHealthDay } from "@/lib/api";

/**
 * Fábrica de días de salud para los tests.
 *
 * `GarminHealthDay` tiene trece campos y casi todos son `null` en un día
 * real (ningún reloj calcula VO₂ máx todas las noches), así que cada
 * prueba escribía trece líneas para decir una sola cosa: "un día con un
 * sueño de 82". El ruido escondía el dato que se estaba probando.
 *
 * Por defecto todo es `null` - el estado honesto de un día del que no se
 * sabe nada - y cada test enciende solo lo que necesita. Vive en
 * `src/test/` y no en `src/lib/` porque no es código de producto: no
 * debe acabar en el bundle.
 */
export function unDiaDeSalud(cambios: Partial<GarminHealthDay> = {}): GarminHealthDay {
  return {
    fecha: "2026-09-14",
    hrv_value: null,
    hrv_status: null,
    body_battery_am: null,
    training_readiness: null,
    sleep_score: null,
    stress_avg: null,
    resting_hr: null,
    vo2max: null,
    pasos: null,
    deep_sleep_seg: null,
    light_sleep_seg: null,
    rem_sleep_seg: null,
    awake_sleep_seg: null,
    ...cambios,
  };
}

/** Una noche con puntuación y las cuatro fases repartidas, que es el
 *  caso con el que se dibuja la barra de fases. */
export function unaNoche(cambios: Partial<GarminHealthDay> = {}): GarminHealthDay {
  return unDiaDeSalud({
    sleep_score: 82,
    deep_sleep_seg: 5_400,
    rem_sleep_seg: 4_800,
    light_sleep_seg: 16_200,
    awake_sleep_seg: 900,
    ...cambios,
  });
}
