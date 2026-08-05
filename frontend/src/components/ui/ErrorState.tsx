import { Button } from "./Button";

/**
 * Estado de error estandarizado con reintento (auditoría UI/UX,
 * hallazgo H6): antes, cuando un fetch de tarjeta fallaba (red caída,
 * API caída), el usuario veía un texto rojo sin ninguna acción
 * disponible salvo recargar la página ENTERA - ninguna tarjeta de
 * solo lectura (Garmin, resumen semanal, carga de entrenamiento,
 * tendencias) ofrecía un botón "Reintentar". `onRetry` es opcional
 * para los pocos casos donde reintentar no tiene sentido (p.ej. un
 * error de validación tras un submit, que ya se resuelve corrigiendo
 * el formulario, no reintentando la misma petición).
 */
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="flex flex-col items-start gap-2">
      <p className="text-red-400 text-sm text-pretty">{message}</p>
      {onRetry && (
        <Button variant="ghost" onClick={onRetry} className="px-0 normal-case tracking-normal">
          Reintentar
        </Button>
      )}
    </div>
  );
}
