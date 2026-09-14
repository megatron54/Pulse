import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { IntradayMetricCard } from "./IntradayMetricCard";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: { ...actual.api, getGarminIntradayHistory: vi.fn() },
  };
});

describe("IntradayMetricCard", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminIntradayHistory).mockReset();
  });

  it("abre por el Body Battery de hoy: es la serie que se lee sola", async () => {
    // La primera pestaña es también la que se pide sin tocar nada. El
    // pulso de todo el día es la serie más ruidosa y ya no abre la
    // tarjeta.
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([]);
    render(<IntradayMetricCard userId={1} />);
    await waitFor(() =>
      expect(api.getGarminIntradayHistory).toHaveBeenCalledWith(
        1,
        "body_battery",
        expect.any(String)
      )
    );
  });

  it("muestra un mensaje honesto si no hay puntos ese dia (scheduler aun no sincronizo)", async () => {
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([]);
    render(<IntradayMetricCard userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/garmin todavía no ha sincronizado la serie de hoy/i)).toBeInTheDocument()
    );
  });

  it("muestra un error si la peticion falla", async () => {
    vi.mocked(api.getGarminIntradayHistory).mockRejectedValue(new ApiError(500, "caído"));
    render(<IntradayMetricCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
  });

  it("cambiar de pestaña pide la metrica correspondiente", async () => {
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([]);
    const user = userEvent.setup();
    render(<IntradayMetricCard userId={1} />);
    await waitFor(() => expect(api.getGarminIntradayHistory).toHaveBeenCalledTimes(1));

    await user.click(screen.getByRole("tab", { name: /^pulso$/i }));

    await waitFor(() =>
      expect(api.getGarminIntradayHistory).toHaveBeenLastCalledWith(
        1,
        "heart_rate",
        expect.any(String)
      )
    );
  });

  it("con puntos, dice qué dibuja la línea, cuántas medidas hay y cómo ver los días anteriores", async () => {
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([
      { timestamp_utc: "2026-08-09T06:00:00", valor: 60 },
      { timestamp_utc: "2026-08-09T06:02:00", valor: 62 },
    ]);
    render(<IntradayMetricCard userId={1} />);

    await waitFor(() =>
      expect(screen.getByText(/2 mediciones registradas hoy/i)).toBeInTheDocument()
    );
    // La leyenda sale del catálogo, la misma que titula la gráfica de un
    // día en la página de detalle.
    expect(screen.getByText(/body battery minuto a minuto/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /ver los días anteriores/i })).toHaveAttribute(
      "href",
      "/salud/body-battery"
    );
  });
});
