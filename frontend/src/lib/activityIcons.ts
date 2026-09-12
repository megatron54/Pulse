import { Bike, Dumbbell, PersonStanding, Waves, type LucideIcon } from "lucide-react";

/**
 * Icono representativo por tipo crudo de actividad de Garmin (usado en
 * el feed mixto `GarminActivitiesCard`, donde conviven varios
 * deportes - las vistas ya filtradas por categoría, ej.
 * `SportActivityHistoryCard`, reciben su icono fijo como prop). Si el
 * tipo no coincide con ninguno conocido se usa `Dumbbell` como
 * genérico - nunca se oculta la actividad por no reconocer su icono.
 */
export function iconForActivityType(tipo: string): LucideIcon {
  const normalizado = tipo.toLowerCase();
  if (normalizado.includes("run")) return PersonStanding;
  if (normalizado.includes("cycl") || normalizado.includes("bik")) return Bike;
  if (normalizado.includes("swim")) return Waves;
  return Dumbbell;
}
