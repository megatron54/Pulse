import { Activity, Bike, Dumbbell, Footprints, Mountain, Waves } from "lucide-react";
import type { LucideIcon } from "lucide-react";

/**
 * El icono de cada deporte, para la tabla de sesiones.
 *
 * Es el único uso de icono que la doctrina permite además de la
 * navegación: identificar algo (la regla cero cita literalmente "la
 * categoría de un deporte"). No es adorno de título ni un chip de color:
 * en una lista de 27 sesiones mezcladas, es lo que permite encontrar las
 * carreras sin leer las 27 etiquetas, que es justo lo que la tabla no
 * dejaba hacer.
 *
 * Va en tinta apagada y del tamaño del texto: el dato es el nombre de la
 * sesión, el icono solo lo localiza. Y `aria-hidden`, porque el nombre
 * del deporte ya está escrito al lado - un lector de pantalla no debe
 * oír "carrera" dos veces.
 *
 * El mapeo es por palabra clave sobre el `typeKey` de Garmin, igual que
 * `nombreActividad`: el catálogo de Garmin es largo y cambia, y un tipo
 * nuevo cae en el icono genérico en vez de dejar la celda descuadrada.
 */
const POR_PALABRA: readonly [string, LucideIcon][] = [
  ["trail", Mountain],
  ["hik", Mountain],
  ["run", Footprints],
  ["walk", Footprints],
  ["cycl", Bike],
  ["bik", Bike],
  ["ride", Bike],
  ["swim", Waves],
  ["row", Waves],
  ["strength", Dumbbell],
  ["weight", Dumbbell],
];

export function IconoDeporte({ tipo }: { tipo: string }) {
  const clave = tipo.toLowerCase();
  const Icono = POR_PALABRA.find(([palabra]) => clave.includes(palabra))?.[1] ?? Activity;
  return <Icono aria-hidden="true" className="size-4 shrink-0 text-ink-3" />;
}
