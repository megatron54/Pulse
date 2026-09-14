"use client";

import { useEffect, useState } from "react";
import { api, ApiError, type BodyMeasurement, type User } from "@/lib/api";
import { dedupeUltimaPorDia } from "@/lib/dedupe";
import { FASES_NUTRICION, nombreFase } from "@/lib/fasesNutricion";
import { diasDesdeHoy, fechaCorta, fechaMenosDias, plural } from "@/lib/fechas";
import { Card } from "./ui/Card";
import { DataList, DataRow } from "./ui/DataList";
import { EmptyState } from "./ui/EmptyState";
import { ErrorState } from "./ui/ErrorState";
import { LoadingState } from "./ui/LoadingState";

/** Ancho de la ventana de comparación, en días, contados hacia atrás
 *  desde la ÚLTIMA pesada (no desde hoy - ver docstring). */
const DIAS_VENTANA = 30;
/** Cuánto historial se pide para poder encontrar esa última pesada
 *  aunque sea antigua. Un año es de sobra y sigue siendo una respuesta
 *  pequeña (una fila por pesada). */
const DIAS_CONSULTA = 365;
/** A partir de aquí la tarjeta avisa de que habla del pasado. Dos
 *  semanas sin pesarse ya no describen "cómo va la fase ahora". */
const DIAS_DATO_VIEJO = 14;
// Por debajo de este umbral relativo el cambio de peso se trata como
// "estable" - una fluctuación de agua/comida de un día a otro no debe
// leerse como progreso o retroceso real.
const UMBRAL_ESTABLE_PCT = 1;

type Alineacion = "en_linea" | "desviado" | "sin_señal";

function evaluarAlineacion(fase: User["fase_peso_actual"], deltaPct: number): Alineacion {
  const estable = Math.abs(deltaPct) < UMBRAL_ESTABLE_PCT;
  if (fase === "cut")
    return deltaPct < -UMBRAL_ESTABLE_PCT / 2 ? "en_linea" : estable ? "sin_señal" : "desviado";
  if (fase === "surplus")
    return deltaPct > UMBRAL_ESTABLE_PCT / 2 ? "en_linea" : estable ? "sin_señal" : "desviado";
  // maintenance / recomp: el objetivo es la estabilidad de peso.
  return estable ? "en_linea" : "desviado";
}

/** Veredicto en palabras + un color que solo refuerza lo que ya dice el
 *  texto (WCAG 1.4.1 y doctrina 1). */
const VEREDICTO: Record<Alineacion, { titulo: string; color: string }> = {
  en_linea: { titulo: "Vas en línea con tu objetivo", color: "text-pos" },
  desviado: { titulo: "Tu peso no va en la dirección esperada", color: "text-warn" },
  sin_señal: { titulo: "Todavía sin señal clara", color: "text-ink-2" },
};

/**
 * Compara la tendencia de peso real (báscula Feelfit, vía
 * `getBodyMeasurementHistory`) contra la fase de peso objetivo del
 * usuario (`UserProfile.fase_peso_actual`) - petición explícita del
 * usuario: "que muestre insights de los datos de la báscula Feelfit
 * comparado con mis objetivos". No hay ningún objetivo numérico de peso
 * en el backend (ni se inventa uno aquí): la comparación es honesta,
 * dirección observada contra dirección esperada por la fase activa, y
 * exige dos días distintos con medición para no leer el ruido de una
 * sola pesada como progreso.
 *
 * La ventana de 30 días se cuenta desde la última pesada, NO desde hoy.
 * Con la ventana de calendario la tarjeta quedaba muerta: el usuario
 * tenía 247 días con dato y su última pesada era del 1 de julio, así
 * que en septiembre la tarjeta afirmaba "hacen falta pesadas en dos
 * días distintos" - falso, y además decía "tu peso de los últimos 30
 * días" sobre una ventana vacía. Anclar la ventana al dato hace que el
 * veredicto siempre se refiera a pesadas reales; que puedan ser de hace
 * semanas se dice en voz alta en vez de disimularse (doctrina 6).
 *
 * v3: el veredicto era un rectángulo teñido de verde o rojo al 10% con
 * el texto del mismo color - una tarjeta dentro de otra (doctrina 2) y
 * un bloque de color grande para una frase (doctrina 1). Ahora el
 * veredicto es un titular con la frase debajo, y el color vive solo en
 * el titular. Se va además la jerga: "cut/surplus" en el texto dirigido
 * al usuario se decía en inglés.
 */
export function BodyGoalInsightCard({ userId }: { userId: number }) {
  const [usuario, setUsuario] = useState<User | null>(null);
  const [mediciones, setMediciones] = useState<BodyMeasurement[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);

  useEffect(() => {
    let cancelado = false;
    Promise.all([api.getUser(userId), api.getBodyMeasurementHistory(userId, DIAS_CONSULTA)])
      .then(([u, m]) => {
        if (cancelado) return;
        setUsuario(u);
        setMediciones(m);
        setError(null);
      })
      .catch((err) => {
        if (cancelado) return;
        setError(
          err instanceof ApiError
            ? err.message
            : "No se pudo cargar tu objetivo de composición corporal."
        );
      });
    return () => {
      cancelado = true;
    };
  }, [userId, intentos]);

  // La ventana se ancla a la última pesada y no a hoy. Se calcula antes
  // del encabezado porque el subtítulo tiene que decir de qué fechas
  // habla: "los últimos 30 días" era mentira si la última pesada era de
  // hace dos meses.
  const diario = mediciones
    ? dedupeUltimaPorDia(mediciones).sort((a, b) => a.fecha.localeCompare(b.fecha))
    : [];
  const ultimo = diario.at(-1);
  const desde = ultimo ? fechaMenosDias(ultimo.fecha, DIAS_VENTANA - 1) : null;
  const ventana = desde ? diario.filter((m) => m.fecha >= desde) : [];
  const primero = ventana.at(0);
  // 0 y no `null` cuando no hay ninguna pesada: así el tipo es `number`
  // en todos los textos que lo escriben, y "0 días" nunca se muestra
  // porque sin pesadas la tarjeta entra por otra rama.
  const diasSinPesarse = ultimo ? diasDesdeHoy(ultimo.fecha) : 0;
  const datoViejo = diasSinPesarse > DIAS_DATO_VIEJO;

  const encabezado = (
    <div>
      <h2 className="t-section text-ink">Tu objetivo</h2>
      <p className="t-secondary mt-1 text-pretty text-ink-3">
        {ultimo && datoViejo
          ? `Tus pesadas de los ${DIAS_VENTANA} días hasta el ${fechaCorta(ultimo.fecha)}, frente a la fase que tienes activa.`
          : `Tu peso de los últimos ${DIAS_VENTANA} días frente a la fase que tienes activa.`}
      </p>
    </div>
  );

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

  if (usuario === null || mediciones === null) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        <LoadingState lines={2} />
      </Card>
    );
  }

  const fase = usuario.fase_peso_actual;

  const filaFase = (
    <DataList>
      <DataRow label="Fase activa" nota={FASES_NUTRICION[fase]?.explicacion}>
        {nombreFase(fase)}
      </DataRow>
    </DataList>
  );

  // Dos pesadas del mismo día no son una ventana: comparar dos
  // mediciones de la misma mañana daría un "cambio" que es solo ruido.
  if (!primero || !ultimo || primero.fecha === ultimo.fecha) {
    return (
      <Card>
        <div className="mb-4">{encabezado}</div>
        {filaFase}
        <div className="mt-4">
          <EmptyState
            message={
              !ultimo
                ? "Todavía no hay pesadas registradas, así que no hay tendencia que comparar con tu objetivo."
                : datoViejo
                  ? // Con una sola pesada Y vieja, el motivo de que la
                    // tarjeta esté vacía no es la ventana: es que hace
                    // meses que nadie se pesa. Eso, y qué hacer.
                    `Tu última pesada es del ${fechaCorta(ultimo.fecha)}, hace ${plural(
                      diasSinPesarse,
                      "día",
                      "días"
                    )}. Vuelve a pesarte para poder comparar tu evolución con la fase que tienes activa.`
                  : `Solo hay una pesada en los ${DIAS_VENTANA} días hasta el ${fechaCorta(ultimo.fecha)}. Hacen falta dos días distintos para ver una dirección.`
            }
          />
        </div>
      </Card>
    );
  }

  const deltaPct = ((ultimo.peso_kg - primero.peso_kg) / primero.peso_kg) * 100;
  const alineacion = evaluarAlineacion(fase, deltaPct);
  const veredicto = VEREDICTO[alineacion];
  const deltaTexto = `${deltaPct > 0 ? "+" : deltaPct < 0 ? "−" : ""}${Math.abs(deltaPct).toFixed(1)} %`;

  return (
    <Card plano>
      <div className="flex flex-col gap-4 p-5">
        {encabezado}
        <div>
          <p className={`t-section ${veredicto.color}`}>{veredicto.titulo}</p>
          <p className="t-body mt-1 max-w-prose text-pretty text-ink-2">
            {alineacion === "en_linea" &&
              `Tu peso se mueve como toca para una fase de ${nombreFase(fase).toLowerCase()}.`}
            {alineacion === "desviado" &&
              `Para una fase de ${nombreFase(fase).toLowerCase()}, esperaríamos otra dirección. Si se mantiene, revisa tu objetivo de calorías o la fase misma.`}
            {alineacion === "sin_señal" &&
              "El peso se ha mantenido casi igual. Es normal al principio de una fase o si va despacio: hacen falta más semanas para saberlo."}
          </p>
          {/* El veredicto es real, pero es del pasado: decirlo es
              obligatorio, porque leído sin fecha suena a "ahora". */}
          {datoViejo && (
            <p className="t-secondary mt-2 max-w-prose text-pretty text-warn">
              Tu última pesada es de hace {plural(diasSinPesarse, "día", "días")}, así que esto
              habla de entonces y no de esta semana. Vuelve a pesarte para tener una lectura al
              día.
            </p>
          )}
        </div>
        {filaFase}
      </div>

      <div className="border-t border-line px-5 py-4">
        <DataList>
          <DataRow
            label="Cambio de peso"
            nota={`del ${fechaCorta(primero.fecha)} al ${fechaCorta(ultimo.fecha)}`}
          >
            <span className="tabular">{deltaTexto}</span>
          </DataRow>
          <DataRow label="Peso" nota={`antes ${primero.peso_kg.toFixed(1)} kg`}>
            <span className="tabular">{ultimo.peso_kg.toFixed(1)} kg</span>
          </DataRow>
        </DataList>
      </div>
    </Card>
  );
}
