import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CoachNarrativeBlock } from "./CoachNarrativeBlock";
import { api, ApiError } from "@/lib/api";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    api: {
      ...actual.api,
      getGarminHealthNarrative: vi.fn(),
    },
  };
});

describe("CoachNarrativeBlock", () => {
  beforeEach(() => {
    vi.mocked(api.getGarminHealthNarrative).mockReset();
  });

  it("no renderiza nada si todavía no hay una decisión de la que hablar (text/source null)", async () => {
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({ text: null, source: null });
    const { container } = render(<CoachNarrativeBlock userId={1} />);
    await waitFor(() => expect(api.getGarminHealthNarrative).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });

  it("muestra el texto del coach cuando existe", async () => {
    vi.mocked(api.getGarminHealthNarrative).mockResolvedValue({
      text: "Tu HRV de hoy (60 ms) está por encima de tu baseline.",
      source: "template",
    });
    render(<CoachNarrativeBlock userId={1} />);
    await waitFor(() =>
      expect(screen.getByText(/está por encima de tu baseline/i)).toBeInTheDocument()
    );
  });

  it("no muestra ningún error visible si la petición falla (bloque no crítico)", async () => {
    vi.mocked(api.getGarminHealthNarrative).mockRejectedValue(new ApiError(500, "caído"));
    const { container } = render(<CoachNarrativeBlock userId={1} />);
    await waitFor(() => expect(api.getGarminHealthNarrative).toHaveBeenCalled());
    expect(container.textContent).toBe("");
  });
});
