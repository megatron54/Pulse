import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { HeartPulse } from "lucide-react";
import { StatTile } from "./StatTile";

describe("StatTile", () => {
  it("muestra la etiqueta, el valor y la unidad", () => {
    render(<StatTile icon={HeartPulse} label="HRV" value={54} unit=" ms" />);
    expect(screen.getByText("HRV")).toBeInTheDocument();
    expect(screen.getByText((_, el) => el?.textContent === "54ms" || el?.textContent === "54 ms")).toBeInTheDocument();
  });
});
