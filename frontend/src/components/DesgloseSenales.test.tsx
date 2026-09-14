import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DesgloseSenales } from "./DesgloseSenales";
import { unasSenales } from "@/test/readiness";

describe("DesgloseSenales", () => {
  it("pone las siete señales en una tabla de verdad, con su valor y su referencia", () => {
    render(<DesgloseSenales senales={unasSenales()} fecha="2026-09-14" resultado="green" />);

    expect(screen.getByRole("table")).toBeInTheDocument();
    // 7 señales + la fila de cabeceras.
    expect(screen.getAllByRole("row")).toHaveLength(8);
    // Por fila y no por texto suelto: lo que hace legible la tabla es
    // que el valor y su referencia estén en la MISMA línea (y "≥ 50" es
    // además la referencia de dos señales distintas).
    const fila = screen.getByRole("row", { name: /Body Battery al despertar/ });
    expect(fila).toHaveTextContent("72");
    expect(fila).toHaveTextContent("≥ 50");
  });

  it("titula la columna del valor con la fecha del cálculo, no con un 'hoy' a ciegas", () => {
    // Si el último veredicto es de ayer (el cálculo necesita el sueño y
    // la VFC de la noche), escribir "Hoy" sería mentir sobre de cuándo
    // son las cifras de la columna.
    const ayer = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
    render(<DesgloseSenales senales={unasSenales()} fecha={ayer} resultado="green" />);

    expect(screen.getByRole("columnheader", { name: "Ayer" })).toBeInTheDocument();
  });

  it("no da el rojo por bueno cuando la señal se cruza por ARRIBA", () => {
    // La carga de entrenamiento es la única señal en la que más es
    // peor: llamarla "muy baja" con un ACWR de 1.7 sería decir lo
    // contrario de lo que pasa.
    render(
      <DesgloseSenales
        senales={unasSenales({ acwr: { estado: "red", valor: 1.72 } })}
        fecha="2026-09-14"
        resultado="red"
      />
    );

    expect(screen.getByText("1.72")).toBeInTheDocument();
    expect(screen.getByText("≤ 1.30")).toBeInTheDocument();
    expect(screen.getByText(/has subido la carga más rápido/i)).toBeInTheDocument();
  });

  it("dibuja como ausencia la señal que el reloj no mide, sin darla por buena", () => {
    render(
      <DesgloseSenales
        senales={unasSenales({ training_readiness: { estado: "unknown" } })}
        fecha="2026-09-14"
        resultado="green"
      />
    );

    // Ni un 0, ni un "Bien": un guion con su lectura para lectores de
    // pantalla (doctrina 6, "lo desconocido no es cero").
    expect(screen.getByLabelText("sin dato")).toBeInTheDocument();
    expect(screen.getByText("Preparación del reloj")).toBeInTheDocument();
    // Y se dice qué significa ese guion, con el plural resuelto: si no,
    // se lee como una mala noticia escondida.
    expect(screen.getByText(/1 señal sin medir: el guion ni suma ni resta/i)).toBeInTheDocument();
  });

  it("nombra primero las señales en rojo y luego las ámbar, y solo aconseja sobre esas", () => {
    render(
      <DesgloseSenales
        senales={unasSenales({
          body_battery: { estado: "red", valor: 24 },
          sleep: { estado: "yellow", valor: 41 },
        })}
        fecha="2026-09-14"
        resultado="red"
      />
    );

    expect(
      screen.getByText(
        "Lo que baja el veredicto hoy: el Body Battery al despertar y la calidad del sueño."
      )
    ).toBeInTheDocument();
    const consejos = screen.getAllByRole("listitem");
    expect(consejos).toHaveLength(2);
    expect(consejos[0]).toHaveTextContent(/body battery al despertar depende/i);
    expect(consejos[1]).toHaveTextContent(/dormir más horas/i);
  });

  it("en una semana mala no escupe seis consejos: tres, y sin repetir el de la VFC", () => {
    // Con seis señales cruzadas (pasa), una lista de seis acciones no se
    // lee. Y las dos de VFC dirían lo mismo dos veces: el motor las
    // cuenta como un único flag, así que aquí también van juntas.
    render(
      <DesgloseSenales
        senales={unasSenales({
          hrv_delta: { estado: "red", valor: -0.18 },
          hrv_trend: { estado: "red", valor: -0.12 },
          body_battery: { estado: "red", valor: 24 },
          acwr: { estado: "red", valor: 1.62 },
          sleep: { estado: "yellow", valor: 44 },
          training_readiness: { estado: "yellow" },
        })}
        fecha="2026-09-14"
        resultado="red"
      />
    );

    const consejos = screen.getAllByRole("listitem");
    expect(consejos).toHaveLength(3);
    expect(consejos[0]).toHaveTextContent(/lleva varios días cayendo/i);
    expect(screen.queryByText(/la variabilidad cardíaca sube con noches largas/i)).toBeNull();
    // Pero la tabla sigue mostrando las siete señales: recortar los
    // consejos no es esconder datos.
    expect(screen.getAllByRole("row")).toHaveLength(8);
    expect(screen.getByText("−18 %")).toBeInTheDocument();
  });

  it("cuando todo está bien lo dice, y no deja la explicación en blanco", () => {
    render(<DesgloseSenales senales={unasSenales()} fecha="2026-09-14" resultado="green" />);

    expect(screen.getByText(/ninguna de tus señales está por debajo de su referencia/i))
      .toBeInTheDocument();
    expect(screen.queryByRole("listitem")).not.toBeInTheDocument();
  });

  it("con el semáforo en rojo y ninguna señal cruzada, no afirma que el veredicto sea verde", () => {
    // El caso real de una captura de verificación: "Recuperación baja"
    // en rojo y, justo debajo, "por eso el veredicto es verde". El
    // cálculo había decidido con la tendencia de VFC, que la fila
    // guardada no conservaba (llegaba a `null` y se dibuja como "sin
    // medir"). La pantalla no puede deducir el color del veredicto de
    // una cuenta a la que le falta la señal que lo decidió.
    render(
      <DesgloseSenales
        senales={unasSenales({ hrv_trend: { estado: "unknown" } })}
        fecha="2026-09-14"
        resultado="red"
      />
    );

    expect(screen.queryByText(/el veredicto es verde/i)).not.toBeInTheDocument();
    expect(screen.getByText(/lo decidió una que no se guardó con el cálculo/i)).toBeInTheDocument();
  });

  it("el dolor articular se lee como sí/no, no como una cifra", () => {
    render(
      <DesgloseSenales
        senales={unasSenales({ joint_pain: { estado: "red" } })}
        fecha="2026-09-14"
        resultado="red"
      />
    );

    expect(screen.getByText("Sí")).toBeInTheDocument();
    expect(screen.getByText(/con dolor articular no se entrena/i)).toBeInTheDocument();
  });
});
