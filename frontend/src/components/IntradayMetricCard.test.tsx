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

  it("pide la metrica de ritmo cardiaco de hoy por defecto", async () => {
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([]);
    render(<IntradayMetricCard userId={1} />);
    await waitFor(() =>
      expect(api.getGarminIntradayHistory).toHaveBeenCalledWith(1, "heart_rate", expect.any(String))
    );
  });

  it("muestra un mensaje honesto si no hay puntos ese dia (scheduler aun no sincronizo)", async () => {
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([]);
    render(<IntradayMetricCard userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/todavía no hay datos minuto a minuto/i)).toBeInTheDocument()
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

    await user.click(screen.getByRole("tab", { name: /body battery/i }));

    await waitFor(() =>
      expect(api.getGarminIntradayHistory).toHaveBeenLastCalledWith(
        1,
        "body_battery",
        expect.any(String)
      )
    );
  });

  it("con puntos, muestra el numero de puntos del dia", async () => {
    vi.mocked(api.getGarminIntradayHistory).mockResolvedValue([
      { timestamp_utc: "2026-08-09T06:00:00", valor: 60 },
      { timestamp_utc: "2026-08-09T06:02:00", valor: 62 },
    ]);
    render(<IntradayMetricCard userId={1} />);
    await waitFor(() => expect(screen.getByText(/2 puntos/i)).toBeInTheDocument());
  });
});
