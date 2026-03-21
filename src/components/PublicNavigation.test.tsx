import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import Footer from "@/components/Footer";
import Navbar from "@/components/Navbar";

describe("Public navigation labels and routes", () => {
  it("usa rótulos públicos em português e link para /sobre no header", () => {
    render(
      <MemoryRouter initialEntries={["/sobre"]}>
        <Navbar />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Início" })).toHaveAttribute("href", "/#inicio");
    expect(screen.getByRole("link", { name: "Locação" })).toHaveAttribute("href", "/locacao");
    expect(screen.getByRole("link", { name: "Sobre" })).toHaveAttribute("href", "/sobre");
    expect(screen.queryByRole("link", { name: "A Empresa" })).not.toBeInTheDocument();
  });

  it("mantém links públicos consistentes no footer", () => {
    render(
      <MemoryRouter>
        <Footer />
      </MemoryRouter>,
    );

    expect(screen.getByRole("link", { name: "Sobre" })).toHaveAttribute("href", "/sobre");
    expect(screen.getByRole("link", { name: "Locação" })).toHaveAttribute("href", "/locacao");
    expect(screen.queryByRole("link", { name: "A Empresa" })).not.toBeInTheDocument();
  });
});
