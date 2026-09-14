import type { GarminHealthDay, GarminIntradayMetrica } from "./api";

/**
 * Las métricas de salud del reloj, con su nombre en español, su unidad y
 * qué significan.
 *
 * Vivían dentro de `GarminHealthHistoryCard`, que era el único sitio que
 * las dibujaba. Salen a un módulo porque ahora hay dos: esa tarjeta y la
 * página de detalle de cada métrica (`/salud/[metrica]`), a la que se
 * llega pulsando su cifra en "Hoy". Duplicar la lista habría garantizado
 * que un día la misma métrica se llamara de dos formas distintas según
 * desde dónde se mirara.
 *
 * `slug` es la parte de la URL, y está en español porque la URL la lee
 * una persona: `/salud/sueno`, no `/salud/sleep_score`. El nombre del
 * campo del backend nunca aparece en pantalla ni en la barra de
 * direcciones (doctrina 8).
 */
export type CampoMetrica = keyof Pick<
  GarminHealthDay,
  | "hrv_value"
  | "body_battery_am"
  | "sleep_score"
  | "stress_avg"
  | "resting_hr"
  | "pasos"
  | "vo2max"
>;

export type MetricaSalud = {
  slug: string;
  campo: CampoMetrica;
  /** Nombre completo, para el título de su propia página. */
  titulo: string;
  /** Nombre corto, para la cifra de "Hoy" y la cabecera de una tabla. */
  tituloCorto: string;
  unidad: string;
  decimales: number;
  explicacion: string;
  /** Límites físicos de la métrica, cuando los tiene: el eje de la
   *  gráfica no debe rotular un Body Battery de -8 ni de 102. */
  rango?: readonly [number, number];
  /** Hacia dónde es mejor que se mueva. Responde a la pregunta que una
   *  cifra sola no responde nunca ("¿16 de estrés es bueno?"), y por eso
   *  es obligatorio: si una métrica no tiene dirección buena, no se
   *  puede interpretar y no debería estar en una pantalla de estado. */
  mejorHacia: "arriba" | "abajo";
  /** Cómo se nombra un registro de esta métrica: el sueño se mide por
   *  noches y no por días, y llamar "día" a una noche obliga al usuario
   *  a traducir cada vez que lee la tabla (doctrina 8). */
  nombreDelRegistro: "día" | "noche";
  /** Qué guarda el reloj de UN registro concreto, más allá de la cifra
   *  del día. Es lo que hace que merezca la pena poder pulsar una fila:
   *  sin esto, el detalle de una métrica sería la misma cifra otra vez.
   *  `undefined` en las que solo tienen un valor al día (VFC nocturna,
   *  pasos, VO₂ máx). */
  detalleDelRegistro?:
    | { tipo: "fases-sueno" }
    | {
        tipo: "intradia";
        serie: GarminIntradayMetrica;
        /** Qué dibuja exactamente esa serie, para titular la gráfica del
         *  día. No es decorativo: en "Pulso en reposo" la cifra del día
         *  era 52 ppm y la línea del detalle subía a 180, porque el reloj
         *  guarda el pulso de TODO el día y el reposo es solo su tramo
         *  más bajo. Sin decirlo, la gráfica parecía desmentir la cifra
         *  que se acababa de pulsar. */
        leyenda: string;
      };
};

export const METRICAS_SALUD: readonly MetricaSalud[] = [
  {
    slug: "sueno",
    campo: "sleep_score",
    titulo: "Calidad del sueño",
    tituloCorto: "Sueño",
    unidad: "",
    decimales: 0,
    explicacion:
      "Puntuación de Garmin de 0 a 100 combinando cuánto has dormido, en qué fases y cuánto te has despertado. Por debajo de 50 cuenta como señal de mala recuperación.",
    rango: [0, 100],
    mejorHacia: "arriba",
    nombreDelRegistro: "noche",
    detalleDelRegistro: { tipo: "fases-sueno" },
  },
  {
    slug: "body-battery",
    campo: "body_battery_am",
    titulo: "Body Battery al despertar",
    tituloCorto: "Body Battery",
    unidad: "",
    decimales: 0,
    explicacion:
      "La estimación de energía disponible de Garmin al levantarte, de 0 a 100. Depende casi entera de la noche anterior, así que es la métrica que más se mueve al acostarse antes.",
    rango: [0, 100],
    mejorHacia: "arriba",
    nombreDelRegistro: "día",
    detalleDelRegistro: {
      tipo: "intradia",
      serie: "body_battery",
      leyenda: "Body Battery minuto a minuto",
    },
  },
  {
    slug: "vfc",
    campo: "hrv_value",
    titulo: "Variabilidad cardíaca",
    tituloCorto: "VFC",
    unidad: " ms",
    decimales: 0,
    explicacion:
      "Cuánto varía el tiempo entre latidos mientras duermes. Es la señal principal de recuperación, y solo significa algo comparada contigo mismo: no hay un valor bueno universal, pero varios días seguidos por debajo de tu media indican fatiga acumulada.",
    mejorHacia: "arriba",
    nombreDelRegistro: "noche",
  },
  {
    slug: "estres",
    campo: "stress_avg",
    titulo: "Estrés medio del día",
    tituloCorto: "Estrés",
    unidad: "",
    decimales: 0,
    explicacion:
      "Media diaria de 0 a 100 que Garmin estima a partir del pulso y su variabilidad. Mide activación del sistema nervioso, no cómo te sientes: un día de entrenamiento duro la sube igual que un día de mal dormir.",
    rango: [0, 100],
    mejorHacia: "abajo",
    nombreDelRegistro: "día",
    detalleDelRegistro: {
      tipo: "intradia",
      serie: "stress",
      leyenda: "Estrés minuto a minuto",
    },
  },
  {
    slug: "pulso-reposo",
    campo: "resting_hr",
    titulo: "Pulso en reposo",
    tituloCorto: "Pulso reposo",
    unidad: " ppm",
    decimales: 0,
    explicacion:
      "Tu pulso más bajo del día, normalmente de madrugada. Baja con los meses de entrenamiento aeróbico; las subidas de varios días suelen acompañar a fatiga, falta de sueño o una infección.",
    mejorHacia: "abajo",
    nombreDelRegistro: "día",
    detalleDelRegistro: {
      tipo: "intradia",
      serie: "heart_rate",
      leyenda: "Pulso de todo el día, minuto a minuto",
    },
  },
  {
    slug: "pasos",
    campo: "pasos",
    titulo: "Pasos",
    tituloCorto: "Pasos",
    unidad: "",
    decimales: 0,
    explicacion:
      "Los pasos del día completo, entrenamiento incluido. No es una métrica de rendimiento: es cuánto te has movido fuera de las sesiones, que es lo que sostiene el gasto diario.",
    mejorHacia: "arriba",
    nombreDelRegistro: "día",
  },
  {
    slug: "vo2max",
    campo: "vo2max",
    titulo: "VO₂ máx",
    tituloCorto: "VO₂ máx",
    unidad: " ml/kg/min",
    decimales: 1,
    explicacion:
      "Estimación de tu capacidad aeróbica: cuánto oxígeno puede usar tu cuerpo por minuto. Se mueve despacio, en semanas y no en días, así que un cambio de un día no es un cambio.",
    mejorHacia: "arriba",
    nombreDelRegistro: "día",
  },
];

export function metricaPorSlug(slug: string): MetricaSalud | undefined {
  return METRICAS_SALUD.find((m) => m.slug === slug);
}

export function metricaPorCampo(campo: CampoMetrica): MetricaSalud {
  // `!` justificado: `campo` es una clave de la propia lista, así que la
  // búsqueda no puede fallar sin que falle antes el tipo.
  return METRICAS_SALUD.find((m) => m.campo === campo)!;
}
