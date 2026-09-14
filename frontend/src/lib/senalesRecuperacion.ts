/**
 * El texto humano del semáforo de recuperación.
 *
 * Existe porque la pantalla decía "Recuperación baja" en rojo grande y
 * nada más: ni qué significa, ni cuál de las seis cifras de debajo la
 * había puesto en rojo, ni qué hacer al respecto. Las tres preguntas del
 * usuario, literales: *"¿qué significa? ¿estoy descansado o no? ¿por qué
 * está en rojo, por qué está baja, cómo puedo ayudarlo?"*.
 *
 * Reparto de responsabilidades: el backend manda códigos estables
 * (`senal`, `estado`) y los UMBRALES con los que decidió
 * (`engine/periodization.py`); aquí solo se escribe el castellano. Por
 * eso ninguna función de este archivo contiene un umbral: el `30` de
 * Body Battery llega en `umbral_rojo`, y si mañana el motor lo mueve a
 * 35, la frase que lo explica se mueve con él. Duplicar el número aquí
 * era garantizar que un día la explicación mintiera sobre el veredicto.
 */
import type { ReadinessResult, Signal, SignalCode, SignalState } from "./api";
import { formatNumero } from "./numeros";

/** Signo menos tipográfico (U+2212): el guion de teclado se lee como
 *  separador y a cuerpo pequeño casi no se ve delante de una cifra. */
const MENOS = "−";

/**
 * Etiquetas de señal. Cortas pero sin jerga (doctrina 8): "ACWR" es el
 * nombre del cálculo, no algo que nadie quiera leer en su móvil a las
 * siete de la mañana; lo que la persona quiere saber es que habla de su
 * carga de entrenamiento.
 *
 * La VFC aparece dos veces a propósito: son dos preguntas distintas
 * ("cómo estoy hoy" y "hacia dónde va la semana") y el caso que motivó
 * todo esto fue justo un día en rojo por la tendencia mientras el dato
 * de hoy estaba un 16 % POR ENCIMA de la media.
 */
export const ETIQUETA_SENAL: Record<SignalCode, string> = {
  hrv_delta: "VFC frente a tu media",
  hrv_trend: "VFC, tendencia 7 días",
  training_readiness: "Preparación del reloj",
  body_battery: "Body Battery al despertar",
  acwr: "Carga de entrenamiento",
  sleep: "Calidad del sueño",
  joint_pain: "Dolor articular",
};

/**
 * El mismo nombre, pero escrito para ir dentro de una frase.
 *
 * Separado de `ETIQUETA_SENAL` porque un `toLowerCase()` sobre las
 * etiquetas de la tabla escribía "body battery" y "vfc": los nombres
 * propios y las siglas no se minusculizan, y el artículo tampoco se
 * puede añadir por fuera sin acertar el género de cada uno.
 */
export const NOMBRE_EN_FRASE: Record<SignalCode, string> = {
  hrv_delta: "tu VFC de hoy",
  hrv_trend: "la tendencia de VFC de la semana",
  training_readiness: "la preparación que calcula el reloj",
  body_battery: "el Body Battery al despertar",
  acwr: "la carga de entrenamiento",
  sleep: "la calidad del sueño",
  joint_pain: "el dolor articular",
};

/** Orden de lectura: primero lo que el motor pondera como señal de
 *  fatiga fisiológica, y el dolor articular al final por ser el único
 *  que la persona introduce a mano (y el único que, si está, decide
 *  solo). */
export const ORDEN_SENALES: readonly SignalCode[] = [
  "hrv_delta",
  "hrv_trend",
  "body_battery",
  "sleep",
  "training_readiness",
  "acwr",
  "joint_pain",
];

/** Clase de tinta por estado. Los cuatro son información, no adorno
 *  (doctrina 1): rojo y ámbar son las señales que empujan el veredicto,
 *  verde es "esta no es tu culpa hoy" - que es media respuesta a "¿estoy
 *  descansado o no?" - y `unknown` va en tinta apagada porque una señal
 *  sin medir no es una señal buena (doctrina 6). */
export const CLASE_POR_ESTADO: Record<SignalState, string> = {
  red: "text-neg",
  yellow: "text-warn",
  ok: "text-pos",
  unknown: "text-ink-3",
};

/**
 * El estado en una palabra, con la DIRECCIÓN correcta.
 *
 * No es un `Record` porque "rojo" no significa lo mismo en todas las
 * señales: en Body Battery rojo es "muy baja", pero en carga de
 * entrenamiento rojo es "muy ALTA" (más carga es peor). De ahí
 * `peor_hacia`, que viaja con cada señal justo para poder escribir esto
 * sin volver a codificar a mano la dirección de cada regla.
 */
export function etiquetaEstado(senal: Signal): string {
  if (senal.estado === "unknown") return "Sin dato";
  if (senal.senal === "joint_pain") return senal.estado === "red" ? "Sí" : "No";
  // La preparación del reloj es una categoría de Garmin ("high",
  // "moderate"...), así que su estado se escribe con las palabras de
  // Garmin y no con un "Bien" genérico: es el único caso en que el
  // estado ocupa la casilla del valor, porque valor no tiene.
  if (senal.senal === "training_readiness" && senal.estado === "ok") return "Media o alta";
  if (senal.estado === "ok") return "Bien";
  const hacia = senal.peor_hacia === "arriba";
  if (senal.estado === "red") return hacia ? "Muy alta" : "Muy baja";
  return hacia ? "Alta" : "Baja";
}

/** El valor tal y como se lee, o `null` si esa señal no tiene cifra
 *  (dolor articular es un sí/no; la preparación del reloj es una
 *  categoría, no un número). */
export function textoValor(senal: Signal): string | null {
  if (senal.valor === null) return null;
  switch (senal.senal) {
    case "hrv_delta":
    case "hrv_trend": {
      // El backend manda una fracción (−0.19), no un porcentaje: es
      // relativa a la media personal de 28 días, nunca un valor absoluto
      // en ms comparable entre personas.
      const pct = senal.valor * 100;
      const signo = pct < 0 ? MENOS : "+";
      return `${signo}${formatNumero(Math.abs(pct), 0)} %`;
    }
    case "acwr":
      return formatNumero(senal.valor, 2);
    default:
      return formatNumero(senal.valor, 0);
  }
}

/**
 * El valor a partir del cual esa señal deja de empujar el veredicto:
 * "≥ 50", "≤ 1.3". Es la columna que convierte la tabla en una
 * explicación - un 42 suelto no dice si es bueno.
 *
 * Se usa el umbral ÁMBAR cuando existe, porque es el primero que se
 * cruza: el rojo es el segundo escalón, y enseñar solo el rojo haría
 * parecer que un día en ámbar está dentro de rango.
 */
export function textoReferencia(senal: Signal): string | null {
  // Las dos señales sin umbral numérico: su referencia se escribe con
  // palabras en vez de dejar la casilla a "—", que aquí se leería como
  // "no se sabe qué es bueno" y sí se sabe.
  if (senal.senal === "joint_pain") return "No";
  if (senal.senal === "training_readiness") return "Media o alta";
  const frontera = senal.umbral_amarillo ?? senal.umbral_rojo;
  if (frontera === null || frontera === undefined) return null;
  const esFraccion = senal.senal === "hrv_delta" || senal.senal === "hrv_trend";
  const cifra = esFraccion
    ? `${frontera < 0 ? MENOS : ""}${formatNumero(Math.abs(frontera * 100), 0)} %`
    : formatNumero(frontera, senal.senal === "acwr" ? 2 : 0);
  return senal.peor_hacia === "arriba" ? `≤ ${cifra}` : `≥ ${cifra}`;
}

/**
 * Qué significa el veredicto y qué hacer hoy con él.
 *
 * La pregunta era exactamente esta: *"¿significa que estoy
 * correctamente descansado, o no?"*. Un color no la responde, y
 * "Recuperación baja" tampoco: describe una medida, no una decisión. La
 * frase dice en qué estado está el cuerpo Y qué hacer con el
 * entrenamiento de hoy, que es lo único que la persona va a decidir
 * después de leer la tarjeta.
 */
export const SIGNIFICADO_VEREDICTO: Record<ReadinessResult["resultado"], string> = {
  green:
    "Estás recuperado: hoy el cuerpo aguanta el entrenamiento tal y como lo tenías planeado.",
  yellow:
    "Estás a medio recuperar. Puedes entrenar, pero con menos volumen y sin acercarte al fallo: hoy no es el día de buscar un máximo.",
  red: "No estás recuperado. Hoy toca descanso o trabajo suave y técnico; forzar con estas señales es cómo se acumulan las lesiones.",
};

/**
 * La palanca real de cada señal, para la pregunta *"¿cómo puedo
 * ayudarlo?"*.
 *
 * Solo se muestra de las señales que están empujando el veredicto: un
 * consejo por cada una de las siete sería un muro de texto que nadie
 * lee, y encima daría consejos sobre cosas que hoy están bien.
 */
export const COMO_AYUDARLO: Record<SignalCode, string> = {
  hrv_delta:
    "La variabilidad cardíaca sube con noches largas y regulares, y baja con alcohol, cenas tardías y carga acumulada.",
  hrv_trend:
    "Lleva varios días cayendo: eso no se arregla con una noche buena, sino con dos o tres días seguidos de carga baja.",
  training_readiness:
    "El reloj mezcla sueño, variabilidad cardíaca y carga reciente. Sube sola en cuanto duermas más y entrenes más suave.",
  body_battery:
    "El Body Battery al despertar depende casi entero de la noche anterior: acostarte antes es lo que más lo mueve.",
  acwr: "Has subido la carga más rápido de lo que tu cuerpo se ha adaptado. Mantén el volumen de esta semana en vez de subirlo otra vez.",
  sleep:
    "Dormir más horas, y a la misma hora, es la palanca con más efecto sobre todas las demás señales.",
  joint_pain:
    "Con dolor articular no se entrena la zona afectada: descanso hasta que desaparezca, y si sigue más de unos días, consulta.",
};

/** Las señales que están empujando el veredicto hacia abajo, rojas
 *  primero. Es lo que se resume arriba y lo único de lo que se dan
 *  consejos. */
export function senalesQuePesan(senales: readonly Signal[]): Signal[] {
  return [
    ...senales.filter((s) => s.estado === "red"),
    ...senales.filter((s) => s.estado === "yellow"),
  ];
}

/**
 * Tope de consejos. Con seis señales en rojo (existe: una semana mala de
 * verdad) la lista se convertía en un párrafo de seis frases, y una
 * lista de seis acciones no es una lista de acciones: es un muro que se
 * salta. Tres, las más graves, sí se leen y se pueden hacer hoy.
 */
const MAXIMO_CONSEJOS = 3;

/**
 * De qué señales se dan consejos: las que pesan, sin repetirse, y como
 * mucho tres.
 *
 * Las dos señales de VFC se colapsan en una: el motor ya las cuenta
 * como un único flag (ver `_GRUPOS_DE_FLAG` en `periodization.py`), y
 * sus dos consejos hablan de lo mismo con otras palabras. Se conserva el
 * de la tendencia porque dice algo que el de hoy no: que esto no se
 * arregla con una sola noche buena.
 */
export function senalesAAconsejar(senales: readonly Signal[]): Signal[] {
  const pesan = senalesQuePesan(senales);
  const pesaLaTendencia = pesan.some((s) => s.senal === "hrv_trend");
  return pesan
    .filter((s) => !(s.senal === "hrv_delta" && pesaLaTendencia))
    .slice(0, MAXIMO_CONSEJOS);
}

/** Enumeración en castellano: "A, B y C". */
function enumerar(partes: readonly string[]): string {
  if (partes.length <= 1) return partes[0] ?? "";
  return `${partes.slice(0, -1).join(", ")} y ${partes[partes.length - 1]}`;
}

/**
 * La frase que nombra a los culpables: *"Hoy pesan la tendencia de VFC
 * y el Body Battery al despertar"*.
 *
 * Va antes de la tabla porque es la respuesta directa a "¿por qué está
 * en rojo?", y una tabla de siete filas obliga a buscarla. Devuelve
 * `null` cuando no hay ninguna señal en rojo ni en ámbar: ahí el
 * veredicto ya se explica solo y una frase de más solo añadiría ruido.
 */
export function resumenDeSenales(senales: readonly Signal[]): string | null {
  const pesan = senalesQuePesan(senales);
  if (pesan.length === 0) return null;
  const nombres = pesan.map((s) => NOMBRE_EN_FRASE[s.senal]);
  return pesan.length === 1
    ? `Lo que baja el veredicto hoy es una sola señal: ${nombres[0]}.`
    : `Lo que baja el veredicto hoy: ${enumerar(nombres)}.`;
}
