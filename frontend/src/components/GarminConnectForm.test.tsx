import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { GarminConnectForm } from "./GarminConnectForm";
import { api, ApiError, type User } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: { ...actual.api, connectGarmin: vi.fn() },
  };
});

const usuarioCreado: User = {
  id: 1,
  nombre: "Miguel",
  altura_cm: 176,
  fecha_nacimiento: "2002-11-28",
  sexo: "M",
  fase_peso_actual: "maintenance",
};

describe("GarminConnectForm", () => {
  it("pide solo email y contraseña, nunca datos de perfil, en el primer paso", () => {
    render(<GarminConnectForm onConnected={vi.fn()} />);
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/contraseña/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/altura/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/fecha de nacimiento/i)).not.toBeInTheDocument();
  });

  it("al conectar con éxito, llama a onConnected con el usuario creado", async () => {
    vi.mocked(api.connectGarmin).mockResolvedValue(usuarioCreado);
    const onConnected = vi.fn();
    const user = userEvent.setup();
    render(<GarminConnectForm onConnected={onConnected} />);

    await user.type(screen.getByLabelText(/email/i), "miguel@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "hunter2");
    await user.click(screen.getByRole("button", { name: /conectar/i }));

    await waitFor(() => expect(onConnected).toHaveBeenCalledWith(usuarioCreado));
    expect(api.connectGarmin).toHaveBeenCalledWith(
      expect.objectContaining({ email: "miguel@example.com", password: "hunter2" })
    );
  });

  it("si Garmin no dio ciertos campos (422), pide SOLO esos campos y reintenta con ellos", async () => {
    const detalle = { campos_faltantes: ["sexo", "altura_cm"] };
    vi.mocked(api.connectGarmin)
      .mockRejectedValueOnce(new ApiError(422, "faltan campos", detalle))
      .mockResolvedValueOnce(usuarioCreado);
    const onConnected = vi.fn();
    const user = userEvent.setup();
    render(<GarminConnectForm onConnected={onConnected} />);

    await user.type(screen.getByLabelText(/email/i), "miguel@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "hunter2");
    await user.click(screen.getByRole("button", { name: /conectar/i }));

    // Ahora debe pedir SOLO sexo y altura, nunca nombre/fecha (que
    // Garmin sí dio).
    await waitFor(() => expect(screen.getByLabelText(/sexo/i)).toBeInTheDocument());
    expect(screen.getByLabelText(/altura/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/nombre/i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/fecha de nacimiento/i)).not.toBeInTheDocument();

    await user.selectOptions(screen.getByLabelText(/sexo/i), "M");
    await user.type(screen.getByLabelText(/altura/i), "176");
    await user.click(screen.getByRole("button", { name: /completar/i }));

    await waitFor(() => expect(onConnected).toHaveBeenCalledWith(usuarioCreado));
    expect(api.connectGarmin).toHaveBeenLastCalledWith(
      expect.objectContaining({ sexo: "M", altura_cm: 176 })
    );
  });

  it("credenciales invalidas (401) muestran un error honesto, sin pedir datos de perfil", async () => {
    vi.mocked(api.connectGarmin).mockRejectedValue(new ApiError(401, "no autorizado"));
    const user = userEvent.setup();
    render(<GarminConnectForm onConnected={vi.fn()} />);

    await user.type(screen.getByLabelText(/email/i), "miguel@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "mala");
    await user.click(screen.getByRole("button", { name: /conectar/i }));

    await waitFor(() => expect(screen.getByText(/no autorizado/i)).toBeInTheDocument());
    expect(screen.queryByLabelText(/^sexo/i)).not.toBeInTheDocument();
  });

  it("si el segundo paso falla con rate-limit (429), vuelve al paso 1 en vez de quedarse atascado", async () => {
    const detalle = { campos_faltantes: ["sexo"] };
    vi.mocked(api.connectGarmin)
      .mockRejectedValueOnce(new ApiError(422, "faltan campos", detalle))
      .mockRejectedValueOnce(new ApiError(429, "rate limit de Garmin"));
    const user = userEvent.setup();
    render(<GarminConnectForm onConnected={vi.fn()} />);

    await user.type(screen.getByLabelText(/email/i), "miguel@example.com");
    await user.type(screen.getByLabelText(/contraseña/i), "hunter2");
    await user.click(screen.getByRole("button", { name: /conectar/i }));

    await waitFor(() => expect(screen.getByLabelText(/sexo/i)).toBeInTheDocument());
    await user.selectOptions(screen.getByLabelText(/sexo/i), "M");
    await user.click(screen.getByRole("button", { name: /completar/i }));

    // Vuelve al paso 1 (email/contraseña), no se queda en "completar
    // campos" con un error de sesión sin salida.
    await waitFor(() => expect(screen.getByText(/rate limit de garmin/i)).toBeInTheDocument());
    expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
    expect(screen.queryByLabelText(/^sexo/i)).not.toBeInTheDocument();
  });
});
