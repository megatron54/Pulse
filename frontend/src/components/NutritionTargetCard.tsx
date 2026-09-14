"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, ApiError, todayLocalDate, type NutritionTarget } from "@/lib/api";
import { FASES_NUTRICION } from "@/lib/fasesNutricion";
import { Card } from "./ui/Card";
import { DataList, DataRow } from "./ui/DataList";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";
import { MacroBar } from "./ui/MacroBar";

/**
 * Objetivo de macros de hoy (Nutrición).
 *
 * Rehecha para v3. El defecto que señaló el usuario era de fondo, no de
 * estilo: "el objetivo nutricional de hoy con el botón de calcular
 * macros hoy carece de sentido". Tenía razón dos veces.
 *
 *  1. Estaba en la pantalla de Hoy, que responde "¿qué entreno y cómo
 *     estoy?". De ahí ya se quitó: su sitio es Nutrición.
 *  2. Exigía pulsar "Calcular macros de hoy" para ver un número que el
 *     sistema puede calcular solo. Un botón que solo sirve para pedir
 *     lo que la pantalla debería mostrar al abrirse no es una acción:
 *     es un dato escondido detrás de un clic. Ahora se calcula al
 *     entrar.
 *
 * El cálculo es un POST porque deja constancia en `AuditLog` de qué
 * regla se aplicó (explicabilidad del motor, ver
 * `services/nutrition_service.compute_daily_nutrition_target`). Eso
 * significa una fila de auditoría por visita a esta página, que es el
 * precio aceptado por no esconder el dato: el registro es append-only y
 * de un solo usuario.
 *
 * También desaparece el donut "Ver como anillo": era el mismo reparto
 * de macros que la barra de arriba, dibujado otra vez con tres colores
 * saturados.
 */
export function NutritionTargetCard({ userId }: { userId: number }) {
  const [resultado, setResultado] = useState<NutritionTarget | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [faltaPeso, setFaltaPeso] = useState(false);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    api
      .getNutritionTarget(userId, todayLocalDate())
      .then((r) => {
        if (!cancelado) setResultado(r);
      })
      .catch((err) => {
        if (cancelado) return;
        // El 400 de este endpoint tiene una causa única y accionable:
        // sin ninguna pesada no hay TDEE que calcular.
        if (err instanceof ApiError && err.status === 400) {
          setFaltaPeso(true);
          return;
        }
        setError(
          err instanceof ApiError ? err.message : "No se pudo calcular el objetivo de hoy."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  const encabezado = <h2 className="t-section text-ink">Objetivo de hoy</h2>;

  if (error) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <ErrorState
          message={error}
          onRetry={() => {
            setError(null);
            setIntentos((n) => n + 1);
          }}
        />
      </Card>
    );
  }

  if (faltaPeso) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <EmptyState
          message="Para calcular tus calorías hace falta tu peso: es la base del gasto diario."
          accion={
            <Link
              href="/cuerpo"
              className="t-body inline-flex min-h-11 items-center rounded-md border border-line px-4 text-ink hover:bg-canvas focus:outline-none focus-visible:ring-2 focus-visible:ring-ink"
            >
              Registrar mi peso
            </Link>
          }
        />
      </Card>
    );
  }

  if (resultado === null) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <LoadingState lines={3} />
      </Card>
    );
  }

  const fase = FASES_NUTRICION[resultado.fase_aplicada] ?? {
    label: resultado.fase_aplicada,
    explicacion: "",
  };

  return (
    <Card plano>
      <div className="flex flex-col gap-5 p-5">
        {encabezado}

        <div>
          <p className="t-hero tabular text-ink">
            {Math.round(resultado.kcal_objetivo)}
            <span className="t-body text-ink-2"> kcal</span>
          </p>
          <p className="t-secondary mt-1 text-ink-3">Para hoy, con tu actividad habitual.</p>
        </div>

        <MacroBar
          macros={[
            { label: "Proteína", gramos: resultado.proteina_g, kcal: resultado.proteina_g * 4 },
            {
              label: "Carbohidratos",
              gramos: resultado.carbohidratos_g,
              kcal: resultado.carbohidratos_g * 4,
            },
            { label: "Grasa", gramos: resultado.grasa_g, kcal: resultado.grasa_g * 9 },
          ]}
        />
      </div>

      <div className="border-t border-line px-5 py-4">
        <DataList>
          <DataRow label="Fase aplicada" nota={fase.explicacion || undefined}>
            {fase.label}
          </DataRow>
        </DataList>
        {resultado.deficit_pausado_por_guardrail && (
          // Aviso en texto, no un icono de alerta: el motor ha cambiado
          // de fase por su cuenta y eso hay que explicarlo, no señalarlo.
          // El backend solo expone el booleano, no cuál de los dos
          // disparadores (readiness o sueño) actuó - de ahí el "o".
          <p className="t-body mt-3 max-w-prose text-pretty text-warn">
            Tu déficit está en pausa: tu recuperación o tu sueño llevan varios días por debajo de
            lo saludable, así que hoy comes en mantenimiento. Se reanudará solo cuando vuelvan a su
            sitio.
          </p>
        )}
      </div>
    </Card>
  );
}
