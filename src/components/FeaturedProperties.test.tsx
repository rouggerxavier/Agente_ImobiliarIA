import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import FeaturedProperties from "@/components/FeaturedProperties";
import { ApiError } from "@/lib/imoveis-api";

const mockFetchImoveisPorTipo = vi.fn();

vi.mock("@/lib/imoveis-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/imoveis-api")>("@/lib/imoveis-api");
  return {
    ...actual,
    fetchImoveisPorTipo: (...args: unknown[]) => mockFetchImoveisPorTipo(...args),
  };
});

const baseImovel = {
  id: 1,
  codigo: "A1",
  tipo_negocio: "locacao" as const,
  titulo: "Apartamento em Manaíra",
  descricao: "Descrição de teste com tamanho válido",
  foto_url: "/imoveis-img/fallback.jpg",
  categoria: "Apartamento",
  finalidade: "RESIDENCIAL",
  fonte_url: null,
  video_url: null,
  mapa_url: null,
  valor_aluguel: "3500.00",
  valor_compra: null,
  condominio: "500.00",
  iptu: "120.00",
  area_m2: "70.00",
  numero_salas: 1,
  numero_vagas: 1,
  numero_quartos: 2,
  numero_banheiros: 2,
  numero_suites: 1,
  dependencias: false,
  ano_construcao: 2018,
  numero_andares: 12,
  tem_elevadores: true,
  bairro: "Manaíra",
  cidade: "João Pessoa",
  created_at: "2026-03-20T00:00:00Z",
  data_source: "api" as const,
};

function renderComponent() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <MemoryRouter>
      <QueryClientProvider client={queryClient}>
        <FeaturedProperties />
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("FeaturedProperties", () => {
  beforeEach(() => {
    mockFetchImoveisPorTipo.mockReset();
  });

  it("renderiza destaques de locação e venda", async () => {
    mockFetchImoveisPorTipo.mockImplementation((tipo: string) => {
      if (tipo === "locacao") {
        return Promise.resolve([{ ...baseImovel, codigo: "L1", tipo_negocio: "locacao" }]);
      }
      return Promise.resolve([
        {
          ...baseImovel,
          codigo: "V1",
          tipo_negocio: "venda",
          valor_aluguel: null,
          valor_compra: "790000.00",
        },
      ]);
    });

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText("Imóveis para Locação")).toBeInTheDocument();
      expect(screen.getByText("Imóveis para Venda")).toBeInTheDocument();
      expect(screen.getAllByText("Apartamento em Manaíra").length).toBeGreaterThan(0);
    });
  });

  it("renderiza estado de erro com mensagem útil", async () => {
    mockFetchImoveisPorTipo.mockRejectedValue(new ApiError(503, "Backend indisponível", "network"));

    renderComponent();

    await waitFor(() => {
      expect(screen.getAllByText("Não foi possível carregar os imóveis em destaque.").length).toBeGreaterThan(0);
      expect(screen.getAllByText(/Backend indisponível/i).length).toBeGreaterThan(0);
    });
  });
});
