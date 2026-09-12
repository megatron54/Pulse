import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Bike } from "lucide-react";
import { ActivityListItem } from "./ActivityListItem";

describe("ActivityListItem", () => {
  it("muestra título, subtítulo y todas las métricas", () => {
    render(
      <ActivityListItem
        icon={Bike}
        title="ciclismo"
        subtitle="2026-08-01"
        metrics={[
          { label: "Duración", value: "45min" },
          { label: "Distancia", value: "20km" },
        ]}
      />
    );
    expect(screen.getByText("ciclismo")).toBeInTheDocument();
    expect(screen.getByText("2026-08-01")).toBeInTheDocument();
    expect(screen.getByText("45min")).toBeInTheDocument();
    expect(screen.getByText("20km")).toBeInTheDocument();
  });
});
