"use client";

import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fechaCorta } from "@/lib/fechas";

/**
 * Gráfica de tendencia (Design System v3, doctrina 5: "toda gráfica
 * lleva eje y unidad").
 *
 * Tres cambios respecto a v2, los tres por hallazgos de la auditoría:
 *
 *  - **Los ejes ya no son opcionales.** v2 tenía `mostrarEjes` y por
 *    defecto era `false`: una curva flotando sin una sola cifra ni
 *    fecha, con el valor accesible solo al pasar el cursor - es decir,
 *    inaccesible en móvil, que es donde se usa la app. Si un dato no
 *    merece eje, no merece gráfica: merece una cifra.
 *  - **Un solo color de datos** (`--data`, desaturado), no un color por
 *    métrica elegido a mano en cada llamada (`#5eead4`, `#a78bfa`...).
 *    Ese arcoíris era una de las fuentes directas del aspecto "neón".
 *  - **Fechas en formato humano y determinista** (`fechaCorta`), en vez
 *    de `toLocaleDateString` con `day/month` numérico, cuyo resultado
 *    además varía con la versión de ICU del entorno.
 *
 * Tercera pasada de auditoría, sobre capturas reales: el eje Y salía en
 * cifras arbitrarias ("80 / 63 / 48 / 33 ms") porque el dominio era el
 * de los datos más un 8%, y en las métricas acotadas llegaba a mentir
 * ("-8" y "102" en un Body Battery que solo existe entre 0 y 100). Ahora
 * el eje se redondea a un paso legible y `rango` recorta el dominio a
 * los límites físicos de la métrica.
 *
 * Cuarta pasada, sobre la captura de la tercera: las marcas redondas se
 * dibujaban mal. El eje de VFC salía "80 / 60 / 50 / 40 / 30 ms"
 * (recharts escondía la marca de 70 por creerla solapada, dejando una
 * escala irregular que falsea la pendiente) y el de pulso en reposo
 * partía "70 ppm" en dos líneas. Se corrigen con `interval={0}`, un
 * ancho de eje calculado y un espacio duro ante la unidad.
 *
 * Y el eje X era categórico - una casilla por punto, todas del mismo
 * ancho -, lo que en el historial de peso (donde hay meses sin pesarse)
 * dibujaba el hueco de enero a marzo con la misma anchura que dos
 * pesadas de días seguidos: la forma de la curva no correspondía con el
 * paso del tiempo. Ahora es una escala temporal de verdad.
 *
 * Quinta pasada: se llamaba `AreaTrendChart` y rellenaba el área bajo la
 * curva con un degradado. Dos motivos para quitarlo, y con él el nombre:
 *
 *  - **Miente sobre la magnitud.** El relleno se lee como "cantidad
 *    desde cero", y aquí ninguna serie parte de cero: el eje del peso
 *    empieza en 75 kg, así que el área sombreada no representaba nada
 *    (la mitad de un cuerpo de 76 kg quedaba fuera del dibujo).
 *  - **Inventaba formas.** Con la línea ya partida por los huecos, cada
 *    tramo cerraba el relleno con un tajo vertical hasta la base: la
 *    captura de la auditoría mostraba tres losas grises con paredes
 *    rectas donde solo hay tres rachas de pesadas. La pared no es un
 *    dato.
 *
 * Un degradado bajo la curva es además el cliché de panel "de IA" que
 * había que quitar (doctrina 1: el color es información, nunca adorno).
 */

/** Paso "bonito" (1, 2, 5, 10, 20, 50...) más cercano al bruto, para que
 *  las marcas del eje caigan en cifras redondas. Se redondea al más
 *  cercano y no hacia arriba: hacia arriba, un paso bruto de 11.75
 *  ascendía a 20 y dejaba el eje en cuatro marcas con la mitad de la
 *  altura vacía. */
function pasoBonito(bruto: number): number {
  if (!(bruto > 0)) return 1;
  const base = 10 ** Math.floor(Math.log10(bruto));
  const normalizado = bruto / base;
  const escala = normalizado < 1.5 ? 1 : normalizado < 3 ? 2 : normalizado < 7 ? 5 : 10;
  return escala * base;
}

/** Dominio y marcas del eje Y: múltiplos del paso que cubren la serie,
 *  recortados a los límites de la métrica si los tiene.
 *
 *  Exportada para poder probarla directamente: en jsdom el
 *  `ResponsiveContainer` de recharts mide 0x0 y no dibuja ningún tick,
 *  así que el eje no es observable desde el DOM en los tests. */
export function ejeY(min: number, max: number, rango?: readonly [number, number]) {
  const span = max - min;
  // Series planas (span 0): se inventa un span pequeño relativo al
  // valor para no dividir por cero y dejar la línea centrada.
  const paso = pasoBonito((span > 0 ? span : Math.max(Math.abs(max) * 0.1, 1)) / 4);
  const redondear = (v: number) => Number(v.toPrecision(12));

  let inferior = redondear(Math.floor(min / paso) * paso);
  let superior = redondear(Math.ceil(max / paso) * paso);
  if (inferior === superior) superior = redondear(inferior + paso);
  if (rango) {
    inferior = Math.max(inferior, rango[0]);
    superior = Math.min(superior, rango[1]);
  }

  const marcas: number[] = [];
  for (let v = inferior; v <= superior + paso / 1000; v += paso) marcas.push(redondear(v));
  // El recorte puede dejar la última marca por debajo del techo (ej.
  // dominio [0, 100] con paso 30): se añade el techo para que el eje
  // no acabe en el aire. Si el resto es menos de medio paso, sustituye
  // a la marca anterior en vez de sumarse: dos etiquetas pegadas ("90"
  // y "100" a tres píxeles) se solapan y recharts esconde una.
  const ultima = marcas[marcas.length - 1];
  if (ultima !== superior) {
    if (superior - ultima < paso / 2) marcas[marcas.length - 1] = superior;
    else marcas.push(superior);
  }

  return { dominio: [inferior, superior] as [number, number], marcas };
}

/** ISO (`2026-09-14` o `2026-09-14T08:30:00`) a marca de tiempo local.
 *  Sin `new Date(iso)`: la forma de solo fecha se interpreta como UTC y
 *  en husos negativos retrocede un día. */
function aTimestamp(iso: string): number {
  const [fecha, hora] = iso.split("T");
  const [anio, mes, dia] = fecha.split("-").map(Number);
  if (!hora) return new Date(anio, mes - 1, dia).getTime();
  const [hh, mm] = hora.split(":").map(Number);
  return new Date(anio, mes - 1, dia, hh, mm || 0).getTime();
}

/** Vuelta a ISO de solo fecha, para reutilizar `fechaCorta`. */
function aIso(t: number): string {
  const fecha = new Date(t);
  const mes = String(fecha.getMonth() + 1).padStart(2, "0");
  const dia = String(fecha.getDate()).padStart(2, "0");
  return `${fecha.getFullYear()}-${mes}-${dia}`;
}

/** Parte la serie donde falten datos, insertando un punto nulo que
 *  rompe la línea (recharts no une por encima de un nulo).
 *
 *  Doctrina 6, "lo desconocido no es cero", aplicada a la gráfica: el
 *  historial de peso de este usuario tiene un agujero de febrero a
 *  junio (dejó de pesarse) y la curva lo cruzaba con una recta suave,
 *  que se lee como "cinco meses estable" cuando lo que hubo fue cinco
 *  meses sin dato.
 *
 *  El umbral es relativo a la propia serie - cinco veces el salto
 *  mediano - porque el mismo componente dibuja series diarias (donde un
 *  hueco son días) e intradía (donde son minutos), y una constante en
 *  días no valdría para las dos.
 *
 *  Exportada para poder probarla: el hueco no es observable en el DOM,
 *  recharts no dibuja nada medible en jsdom. */
export function conHuecos(
  serie: readonly { t: number; valor: number }[]
): { t: number; valor: number | null }[] {
  if (serie.length < 3) return [...serie];

  const saltos = serie.slice(1).map((punto, i) => punto.t - serie[i].t);
  const mediana = [...saltos].sort((a, b) => a - b)[Math.floor(saltos.length / 2)];
  // Serie con fechas repetidas o desordenada: sin un salto mediano
  // positivo el umbral no significa nada, así que no se parte nada.
  if (!(mediana > 0)) return [...serie];
  const limite = mediana * 5;

  const salida: { t: number; valor: number | null }[] = [];
  serie.forEach((punto, i) => {
    if (i > 0 && punto.t - serie[i - 1].t > limite) {
      salida.push({ t: (serie[i - 1].t + punto.t) / 2, valor: null });
    }
    salida.push(punto);
  });
  return salida;
}

/** Si el punto `i` no tiene vecino con dato a ningún lado: entonces no
 *  hay segmento que dibujar y hace falta marcarlo con un punto.
 *
 *  Exportada solo para poder probarla, igual que `conHuecos`. */
export function esAislado(
  serie: readonly { valor: number | null }[],
  i: number
): boolean {
  if (serie[i]?.valor === null || serie[i] === undefined) return false;
  return (serie[i - 1]?.valor ?? null) === null && (serie[i + 1]?.valor ?? null) === null;
}

function formatoHora(t: number): string {
  const fecha = new Date(t);
  return `${String(fecha.getHours()).padStart(2, "0")}:${String(fecha.getMinutes()).padStart(2, "0")}`;
}

export function TrendChart({
  data,
  unidad = "",
  alto = 160,
  decimales = 1,
  formatoEjeX = "fecha",
  rango,
  etiqueta,
}: {
  data: { fecha: string; valor: number }[];
  /** Unidad, con su espacio si lo lleva: " km", " ms", "%". */
  unidad?: string;
  alto?: number;
  decimales?: number;
  /** "fecha" (día/mes) u "hora" (HH:mm, series intradía). */
  formatoEjeX?: "fecha" | "hora";
  /** Límites físicos de la métrica, si los tiene (`[0, 100]` para Body
   *  Battery o una puntuación de sueño). Sin esto el eje puede rotular
   *  valores imposibles al añadir margen a los extremos. */
  rango?: readonly [number, number];
  /** Nombre accesible: qué serie es. Sin esto la gráfica es un `img`
   *  sin alt para un lector de pantalla. */
  etiqueta: string;
}) {
  if (data.length === 0) return null;

  /** El eje X es temporal, así que la serie viaja con la fecha ya
   *  convertida a marca de tiempo. */
  const serie = conHuecos(data.map((d) => ({ t: aTimestamp(d.fecha), valor: d.valor })));

  const valores = data.map((d) => d.valor);
  const { dominio, marcas } = ejeY(Math.min(...valores), Math.max(...valores), rango);

  const formatValor = (v: number) => `${v.toFixed(decimales)}${unidad}`;

  /** Unidades largas ("ml/kg/min", "pasos") no caben repetidas en cinco
   *  marcas: "53.0 ml/kg/min" son 102px de eje, un tercio del ancho de
   *  la gráfica en móvil, y cinco veces la misma palabra. Se rotulan una
   *  sola vez encima del eje y las marcas van desnudas. Las cortas
   *  (" kg", " ms", "%", " kcal") siguen en cada marca, que es donde
   *  mejor se leen. */
  const unidadAparte = unidad.trim().length > 4 ? unidad.trim() : null;

  /** Marca del eje con espacio duro antes de la unidad: con un espacio
   *  normal recharts parte la etiqueta por él y "70 ppm" salía en dos
   *  líneas ("70" y "ppm" debajo), o sea texto roto en el eje de una
   *  gráfica (doctrina 4). En el tooltip, en cambio, sobra el ancho. */
  const formatMarca = (v: number) =>
    unidadAparte ? v.toFixed(decimales) : formatValor(v).replace(" ", " ");

  // Y el ancho se calcula a partir de la etiqueta más larga en vez de
  // ser fijo (52px): "1 250 kcal" no cabía y "20 %" desperdiciaba
  // media pulgada de la gráfica. ~6.4px por carácter a 11px, más el
  // margen entre la etiqueta y el área de datos.
  const anchoEje =
    Math.ceil(Math.max(...marcas.map((m) => formatMarca(m).length)) * 6.4) + 12;

  // La etiqueta de unidad ocupa su propia línea: se le resta a la
  // gráfica para que la tarjeta mida lo mismo con y sin ella.
  const ALTO_UNIDAD = 18;
  const altoGrafica = unidadAparte ? alto - ALTO_UNIDAD : alto;

  return (
    <div style={{ width: "100%", height: alto }} role="img" aria-label={etiqueta}>
      {unidadAparte && (
        // Sin `.t-micro`: esa clase pasa el texto a mayúsculas y una
        // unidad no admite mayúsculas arbitrarias ("ML/KG/MIN" son
        // megalitros). Mismo tamaño y color que las marcas del eje.
        <p
          className="text-ink-3"
          style={{ height: ALTO_UNIDAD, paddingLeft: 2, fontSize: 11, lineHeight: "14px" }}
        >
          {unidadAparte}
        </p>
      )}
      <ResponsiveContainer width="100%" height={altoGrafica}>
        {/* `right: 6` para que el punto de un dato aislado al final de
            la serie (la última pesada, a la derecha del todo) quepa
            entero y no salga cortado por el borde. */}
        <LineChart data={serie} margin={{ top: 4, right: 6, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="var(--line)" vertical={false} />
          <XAxis
            dataKey="t"
            // Eje de tiempo de verdad, no una categoría por punto: con
            // el eje categórico el hueco de tres meses del historial de
            // peso (14 ene -> 23 mar) ocupaba lo mismo que dos pesadas
            // de días seguidos, así que la forma de la curva no
            // correspondía con el paso del tiempo.
            type="number"
            scale="time"
            domain={["dataMin", "dataMax"]}
            // Espacios duros por el mismo motivo que en el eje Y:
            // recharts rompe la etiqueta por el espacio cuando la cree
            // ancha, y "18 sep 2025" se partía en tres líneas.
            tickFormatter={
              formatoEjeX === "hora"
                ? formatoHora
                : (t: number) => fechaCorta(aIso(t)).replace(/ /g, " ")
            }
            tick={{ fontSize: 11, fill: "var(--ink-3)" }}
            axisLine={{ stroke: "var(--line)" }}
            tickLine={false}
            minTickGap={28}
          />
          <YAxis
            domain={dominio}
            ticks={marcas}
            width={anchoEje}
            // `interval={0}` obliga a dibujar todas las marcas: por
            // defecto recharts esconde las que cree que chocan y el eje
            // de VFC salía "80 / 60 / 50 / 40 / 30 ms", una escala
            // irregular que invita a leer mal la pendiente. Las marcas
            // ya son pocas (≤6) y redondas, así que caben.
            interval={0}
            tick={{ fontSize: 11, fill: "var(--ink-3)" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={formatMarca}
          />
          <Tooltip
            cursor={{ stroke: "var(--line-strong)" }}
            contentStyle={{
              background: "var(--surface)",
              border: "1px solid var(--line)",
              borderRadius: 8,
              fontSize: 13,
              padding: "6px 10px",
            }}
            labelFormatter={(t) =>
              formatoEjeX === "hora"
                ? // En una serie intradía la hora sola basta: el día ya
                  // lo dice el título de la tarjeta ("Minuto a minuto de
                  // hoy").
                  formatoHora(Number(t))
                : fechaCorta(aIso(Number(t)))
            }
            labelStyle={{ color: "var(--ink-3)" }}
            itemStyle={{ color: "var(--ink)" }}
            formatter={(value) => [formatValor(Number(value)), etiqueta]}
          />
          <Line
            type="monotone"
            dataKey="valor"
            stroke="var(--data)"
            strokeWidth={2}
            // Un dato aislado entre dos huecos no forma segmento y, sin
            // punto, no se dibujaría en absoluto: una pesada suelta
            // desaparecía de la gráfica justo después de que los huecos
            // empezaran a cortar la línea. Solo esos llevan punto; con
            // puntos en todos, una serie de 90 días es un sarpullido.
            dot={({ cx, cy, index }) =>
              esAislado(serie, index) && typeof cx === "number" && typeof cy === "number" ? (
                <circle key={index} cx={cx} cy={cy} r={2.5} fill="var(--data)" />
              ) : (
                <g key={index} />
              )
            }
            isAnimationActive
            animationDuration={500}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
