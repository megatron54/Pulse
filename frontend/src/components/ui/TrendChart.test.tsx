import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TrendChart, conHuecos, ejeY, esAislado } from "./TrendChart";

const SERIE = [
  { fecha: "2026-08-01", valor: 80 },
  { fecha: "2026-08-02", valor: 79.5 },
];

describe("TrendChart", () => {
  it("toma su nombre accesible de la serie que representa", () => {
    render(<TrendChart data={SERIE} etiqueta="Peso corporal" unidad=" kg" />);
    // v2 anunciaba "Gráfica de tendencia" en todas por igual: con tres
    // gráficas en la misma página eso no distingue ninguna.
    expect(screen.getByRole("img", { name: "Peso corporal" })).toBeInTheDocument();
  });

  it("no renderiza nada sin datos, en vez de un hueco vacío del alto del gráfico", () => {
    const { container } = render(<TrendChart data={[]} etiqueta="Peso corporal" />);
    expect(container).toBeEmptyDOMElement();
  });

  it("no revienta con un solo punto de dato", () => {
    render(<TrendChart data={[SERIE[0]]} etiqueta="Peso corporal" />);
    expect(screen.getByRole("img", { name: "Peso corporal" })).toBeInTheDocument();
  });

  it("rotula el eje Y con la unidad, no solo con el número", () => {
    // Doctrina 5: toda gráfica lleva eje y unidad.
    const { container } = render(
      <TrendChart data={SERIE} etiqueta="Peso corporal" unidad=" kg" decimales={1} />
    );
    expect(container.textContent).toContain("kg");
  });

  it("no parte la etiqueta del eje entre el número y la unidad", () => {
    // "70 ppm" salía en dos líneas ("70" y "ppm" debajo) porque
    // recharts rompe la etiqueta por el espacio: espacio duro.
    const { container } = render(
      <TrendChart
        data={[
          { fecha: "2026-08-01", valor: 52 },
          { fecha: "2026-08-02", valor: 70 },
        ]}
        etiqueta="Pulso en reposo"
        unidad=" ppm"
        decimales={0}
      />
    );
    expect(container.textContent).toContain("70 ppm");
    expect(container.textContent).not.toContain("70 ppm");
  });

  it("saca la unidad larga a una etiqueta única en vez de repetirla en cada marca", () => {
    // "53.0 ml/kg/min" cinco veces medía 102px de eje: un tercio del
    // ancho de la gráfica en móvil para decir cinco veces lo mismo.
    const { container } = render(
      <TrendChart
        data={[
          { fecha: "2026-08-01", valor: 51 },
          { fecha: "2026-08-28", valor: 52.4 },
        ]}
        etiqueta="VO₂ máx"
        unidad=" ml/kg/min"
        decimales={1}
      />
    );
    const veces = container.textContent!.match(/ml\/kg\/min/g) ?? [];
    expect(veces).toHaveLength(1);
    // Pero la unidad sigue estando: doctrina 5, eje y unidad siempre.
    expect(container.textContent).toContain("ml/kg/min");
  });

  it("rotula el eje X con fechas humanas aunque por dentro sean marcas de tiempo", () => {
    // El eje X pasó a `type="number"` con escala de tiempo para que un
    // hueco de tres meses entre pesadas ocupe tres meses de ancho. El
    // riesgo de ese cambio es que el formateador reciba el epoch y
    // rotule "1767222000000": esto lo detecta.
    const { container } = render(
      <TrendChart
        data={[
          { fecha: "2026-01-14", valor: 75.4 },
          { fecha: "2026-07-01", valor: 76.7 },
        ]}
        etiqueta="Peso"
        unidad=" kg"
      />
    );
    // Con espacio duro: igual que en el eje Y, para que "18 sep 2025"
    // no se parta en varias líneas.
    expect(container.textContent).toContain("1 jul");
    expect(container.textContent).not.toMatch(/\d{10,}/);
  });

  it("no rellena el área bajo la curva con un degradado", () => {
    // El relleno se lee como "cantidad desde cero" y aquí el eje del
    // peso empieza en 75 kg, así que no representaba nada; y con la
    // línea partida por los huecos, cada tramo cerraba el relleno con
    // un tajo vertical hasta la base (tres losas grises en la captura
    // de la auditoría donde solo hay tres rachas de pesadas).
    const { container } = render(
      <TrendChart data={SERIE} etiqueta="Peso corporal" unidad=" kg" />
    );
    expect(container.querySelector("linearGradient")).toBeNull();
  });

  it("acepta series intradía con eje de horas", () => {
    render(
      <TrendChart
        data={[
          { fecha: "2026-08-01T08:00:00", valor: 62 },
          { fecha: "2026-08-01T09:00:00", valor: 71 },
        ]}
        etiqueta="Frecuencia cardíaca"
        unidad=" ppm"
        formatoEjeX="hora"
      />
    );
    expect(screen.getByRole("img", { name: "Frecuencia cardíaca" })).toBeInTheDocument();
  });
});

describe("conHuecos", () => {
  const DIA = 86_400_000;
  const serie = (...dias: number[]) => dias.map((d) => ({ t: d * DIA, valor: 76 }));

  it("parte la línea donde faltan datos, en vez de cruzar el hueco con una recta", () => {
    // Caso real: pesadas diarias, cinco meses sin pesarse, y vuelta.
    const resultado = conHuecos(serie(0, 1, 2, 3, 150, 151, 152));
    const nulos = resultado.filter((p) => p.valor === null);
    expect(nulos).toHaveLength(1);
    // El nulo va DENTRO del hueco, no sobre una fecha con dato.
    expect(nulos[0].t).toBeGreaterThan(3 * DIA);
    expect(nulos[0].t).toBeLessThan(150 * DIA);
  });

  it("no parte una serie regular, ni con algún día sin sincronizar", () => {
    expect(conHuecos(serie(0, 1, 2, 3, 4)).every((p) => p.valor !== null)).toBe(true);
    // Un par de días sueltos sin dato no son un agujero: la curva
    // seguiría siendo legible y partirla la convertiría en confeti.
    expect(conHuecos(serie(0, 1, 2, 5, 6, 7)).every((p) => p.valor !== null)).toBe(true);
  });

  it("no toca series de dos puntos ni de fechas repetidas", () => {
    // Con un solo salto, ese salto ES la mediana: nada que comparar.
    expect(conHuecos(serie(0, 300))).toHaveLength(2);
    // Y sin saltos positivos el umbral no significaría nada.
    expect(conHuecos(serie(5, 5, 5))).toHaveLength(3);
  });

  it("usa el ritmo de la propia serie: en intradía el hueco son minutos", () => {
    const MINUTO = 60_000;
    const intradia = [0, 1, 2, 3, 120, 121].map((m) => ({ t: m * MINUTO, valor: 60 }));
    expect(conHuecos(intradia).filter((p) => p.valor === null)).toHaveLength(1);
  });
});

describe("esAislado", () => {
  // Serie ya partida por `conHuecos`: dato, hueco, dato solo, hueco,
  // dos datos seguidos.
  const serie = [
    { valor: 76 },
    { valor: null },
    { valor: 75 },
    { valor: null },
    { valor: 74 },
    { valor: 74.5 },
  ];

  it("marca el dato que no tiene vecinos: sin punto no se dibujaría nada", () => {
    expect(esAislado(serie, 2)).toBe(true);
  });

  it("no marca los datos que forman segmento, ni los propios huecos", () => {
    expect(esAislado(serie, 4)).toBe(false);
    expect(esAislado(serie, 5)).toBe(false);
    expect(esAislado(serie, 1)).toBe(false);
  });

  it("el primer dato cuenta como aislado si lo que sigue es un hueco", () => {
    expect(esAislado(serie, 0)).toBe(true);
    expect(esAislado([{ valor: 76 }, { valor: 75 }], 0)).toBe(false);
  });
});

describe("ejeY", () => {
  it("rotula cifras redondas y no los extremos de la serie", () => {
    // La captura de la auditoría mostraba "80 / 63 / 48 / 33 ms".
    const { dominio, marcas } = ejeY(33, 80);
    expect(marcas).toEqual([30, 40, 50, 60, 70, 80]);
    expect(dominio).toEqual([30, 80]);
  });

  it("nunca sale de los límites físicos de la métrica", () => {
    // Body Battery real de un día flojo: el eje llegaba a "-8" y "102".
    const { dominio, marcas } = ejeY(2, 95, [0, 100]);
    expect(dominio).toEqual([0, 100]);
    expect(marcas[0]).toBe(0);
    expect(marcas[marcas.length - 1]).toBe(100);
    expect(marcas.every((m) => m >= 0 && m <= 100)).toBe(true);
  });

  it("sin límites declarados sí puede bajar de cero (una temperatura, un delta)", () => {
    const { dominio } = ejeY(-3, 12);
    expect(dominio[0]).toBeLessThan(0);
  });

  it("da un dominio con altura aunque la serie sea plana", () => {
    const { dominio, marcas } = ejeY(70, 70);
    expect(dominio[1]).toBeGreaterThan(dominio[0]);
    expect(marcas.length).toBeGreaterThanOrEqual(2);
  });

  it("no deja dos marcas pegadas al recortar contra un techo no redondo", () => {
    // Si el techo cae a menos de medio paso de la última marca,
    // sustituye a esa marca en vez de sumarse: dos etiquetas a tres
    // píxeles se solapan y recharts esconde una, que es justo el eje
    // irregular que se quería quitar.
    const { marcas } = ejeY(0, 6.4, [0, 6.5]);
    expect(marcas).toEqual([0, 2, 4, 6.5]);
  });

  it("deja pocas marcas: un eje de seis etiquetas como máximo", () => {
    // Con más, recharts empieza a esconderlas y la escala se vuelve
    // irregular ("80 / 60 / 50 / 40 / 30 ms" en la auditoría).
    for (const [min, max] of [
      [33, 80],
      [2, 95],
      [48.2, 76.9],
      [0, 12480],
    ] as const) {
      expect(ejeY(min, max).marcas.length).toBeLessThanOrEqual(6);
    }
  });

  it("no arrastra ruido de coma flotante a las etiquetas", () => {
    const { marcas } = ejeY(74.2, 80.2);
    // "76.00000000000001 kg" era un riesgo real al ir sumando el paso.
    expect(marcas).toEqual([74, 76, 78, 80, 82]);
  });
});
