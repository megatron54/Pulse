import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ConnectionsCard } from "./ConnectionsCard";
import { api, ApiError, type Conexiones } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getConnections: vi.fn(),
      connectGarmin: vi.fn(),
      connectFeelfit: vi.fn(),
      syncGarminNow: vi.fn(),
    },
  };
});

const CONECTADO: Conexiones = {
  garmin: {
    conectado: true,
    email: "miguel@example.com",
    historial_desde: "2026-06-01",
    dias_de_historial: 104,
  },
  feelfit: { conectado: true, conectado_desde: "2026-09-10", mediciones_importadas: 34 },
};

describe("ConnectionsCard", () => {
  beforeEach(() => {
    vi.mocked(api.getConnections).mockReset();
  });

  it("muestra con qué cuenta de Garmin está vinculada la app", async () => {
    // El email es lo que evita el problema real que ya ocurrió: perfiles
    // duplicados por no poder ver a qué cuenta estaba conectado Pulse.
    vi.mocked(api.getConnections).mockResolvedValue(CONECTADO);
    render(<ConnectionsCard userId={1} />);
    await waitFor(() => expect(screen.getByText("miguel@example.com")).toBeInTheDocument());
    expect(screen.getByText(/104 días sincronizados/)).toBeInTheDocument();
  });

  it("distingue 'sin conectar' de 'conectado' y ofrece conectar", async () => {
    vi.mocked(api.getConnections).mockResolvedValue({
      garmin: { conectado: false, email: null, historial_desde: null, dias_de_historial: null },
      feelfit: { conectado: false, conectado_desde: null, mediciones_importadas: 0 },
    });
    render(<ConnectionsCard userId={1} />);
    await waitFor(() => expect(screen.getAllByText("Sin conectar")).toHaveLength(2));
    expect(screen.getByRole("button", { name: "Conectar Garmin" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Conectar Feelfit" })).toBeInTheDocument();
    // Sin conexión no hay nada que sincronizar.
    expect(screen.queryByRole("button", { name: /sincronizar ahora/i })).not.toBeInTheDocument();
  });

  it("una cuenta cuyo token caducó aparece como no conectada, no como conectada sin datos", async () => {
    vi.mocked(api.getConnections).mockResolvedValue({
      ...CONECTADO,
      garmin: { ...CONECTADO.garmin, conectado: false },
    });
    render(<ConnectionsCard userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/la sesión guardada dejó de funcionar/i)).toBeInTheDocument()
    );
    expect(screen.getByRole("button", { name: "Conectar Garmin" })).toBeInTheDocument();
  });

  it("concuerda el plural de las mediciones importadas", async () => {
    vi.mocked(api.getConnections).mockResolvedValue({
      ...CONECTADO,
      feelfit: { ...CONECTADO.feelfit, mediciones_importadas: 1 },
    });
    render(<ConnectionsCard userId={1} />);
    await waitFor(() => expect(screen.getByText("1 medición importada")).toBeInTheDocument());
  });

  it("abre el formulario de credenciales solo al pedirlo", async () => {
    vi.mocked(api.getConnections).mockResolvedValue(CONECTADO);
    render(<ConnectionsCard userId={1} />);
    await waitFor(() => expect(screen.getByText("miguel@example.com")).toBeInTheDocument());
    expect(screen.queryByLabelText("Contraseña")).not.toBeInTheDocument();

    screen.getAllByRole("button", { name: "Reconectar" })[0].click();

    await waitFor(() => expect(screen.getByLabelText("Contraseña")).toBeInTheDocument());
    // Precargado con la cuenta ya vinculada: escribir otra crearía un
    // perfil nuevo en vez de reconectar el existente.
    expect(screen.getByLabelText("Email")).toHaveValue("miguel@example.com");
    expect(screen.getByText(/usa esta misma cuenta de garmin/i)).toBeInTheDocument();
  });

  it("muestra un error con reintento si no se puede leer el estado", async () => {
    vi.mocked(api.getConnections).mockRejectedValue(new ApiError(500, "caido"));
    render(<ConnectionsCard userId={1} />);
    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
  });
});
