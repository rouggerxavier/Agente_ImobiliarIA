import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ImovelDetalhe from "@/pages/ImovelDetalhe";

const mockFetchImovelPorCodigo = vi.fn();

vi.mock("@/lib/imoveis-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/imoveis-api")>("@/lib/imoveis-api");
  return {
    ...actual,
    fetchImovelPorCodigo: (...args: unknown[]) => mockFetchImovelPorCodigo(...args),
  };
});

const imovelDetalhado = {
  id: 1,
  codigo: "F2",
  tipo_negocio: "venda" as const,
  titulo: "Apartamento com endereco detalhado",
  descricao: "Descricao de teste com endereco completo",
  foto_url: "/imoveis-img/fallback.jpg",
  categoria: "Apartamento",
  finalidade: "RESIDENCIAL",
  fonte_url: null,
  video_url: null,
  mapa_url:
    "https://www.google.com/maps/embed?origin=Professor+Silvio+Elias+55+Vargem+Grande+Rio+De+Janeiro&pb=!1m2!1m1!1sProfessor+Silvio+Elias+55+Vargem+Grande+Rio+De+Janeiro",
  valor_aluguel: null,
  valor_compra: "890000.00",
  condominio: "900.00",
  iptu: "180.00",
  area_m2: "90.00",
  numero_salas: 1,
  numero_vagas: 1,
  numero_quartos: 3,
  numero_banheiros: 2,
  numero_suites: 1,
  dependencias: false,
  ano_construcao: 2019,
  numero_andares: 14,
  tem_elevadores: true,
  bairro: "Manaira",
  cidade: "Joao Pessoa",
  logradouro: "Rua das Flores",
  numero: "123",
  complemento: "apto 402",
  cep: "58038-000",
  uf: "PB",
  created_at: "2026-03-20T00:00:00Z",
  data_source: "api" as const,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <MemoryRouter initialEntries={["/imovel/F2"]}>
      <QueryClientProvider client={queryClient}>
        <Routes>
          <Route path="/imovel/:codigo" element={<ImovelDetalhe />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("ImovelDetalhe", () => {
  beforeEach(() => {
    mockFetchImovelPorCodigo.mockReset();
  });

  it("converte link de embed para URL navegavel do Google Maps", async () => {
    mockFetchImovelPorCodigo.mockResolvedValue(imovelDetalhado);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Rua das Flores, 123 (apto 402)")).toBeInTheDocument();
      expect(screen.getByTitle(/Mapa do im/)).toBeInTheDocument();
    });

    const mapLinks = screen.getAllByRole("link", { name: /Abrir no Google Maps/i });
    expect(mapLinks.length).toBeGreaterThan(0);
    mapLinks.forEach((link) => {
      expect(link).toHaveAttribute(
        "href",
        "https://www.google.com/maps/search/?api=1&query=Professor%20Silvio%20Elias%2055%20Vargem%20Grande%20Rio%20De%20Janeiro",
      );
    });
  });
});
