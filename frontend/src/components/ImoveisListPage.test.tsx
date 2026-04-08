import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it, vi, beforeEach } from "vitest";

import ImoveisListPage from "@/components/ImoveisListPage";

const mockFetchImoveisPorTipo = vi.fn();
const mockFetchImoveisFiltros = vi.fn();

vi.mock("@/lib/imoveis-api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/imoveis-api")>("@/lib/imoveis-api");
  return {
    ...actual,
    fetchImoveisPorTipo: (...args: unknown[]) => mockFetchImoveisPorTipo(...args),
    fetchImoveisFiltros: (...args: unknown[]) => mockFetchImoveisFiltros(...args),
  };
});

const fallbackItem = {
  id: 10,
  codigo: "F1",
  tipo_negocio: "venda" as const,
  titulo: "Apartamento fallback",
  descricao: "Descrição de teste válida",
  foto_url: "/imoveis-img/fallback.jpg",
  categoria: "Apartamento",
  finalidade: "RESIDENCIAL",
  fonte_url: null,
  video_url: null,
  mapa_url: null,
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
  bairro: "Manaíra",
  cidade: "João Pessoa",
  created_at: "2026-03-20T00:00:00Z",
  data_source: "fallback_local" as const,
};

const detailedItem = {
  ...fallbackItem,
  codigo: "F2",
  data_source: "api" as const,
  logradouro: "Rua das Flores",
  numero: "123",
  complemento: "apto 402",
  cep: "58038-000",
  uf: "pb",
  mapa_url: "https://maps.example.com",
};

function renderPage(initialEntry = "/vendas") {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <QueryClientProvider client={queryClient}>
        <Routes>
          <Route
            path="/vendas"
            element={<ImoveisListPage tipo="venda" titulo="Vendas" descricao="Catálogo para venda" />}
          />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  );
}

describe("ImoveisListPage", () => {
  beforeEach(() => {
    mockFetchImoveisPorTipo.mockReset();
    mockFetchImoveisFiltros.mockReset();
    mockFetchImoveisFiltros.mockResolvedValue({
      bairros: ["Manaíra", "Tambaú"],
      categorias: ["Apartamento"],
      finalidades: ["RESIDENCIAL"],
    });
  });

  it("mostra aviso de contingência quando lista vem de fallback", async () => {
    mockFetchImoveisPorTipo.mockResolvedValue([fallbackItem]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Modo de contingência ativo.")).toBeInTheDocument();
      expect(screen.getByText("Apartamento fallback")).toBeInTheDocument();
      expect(screen.getByText(/Localização parcial: Manaíra, João Pessoa/)).toBeInTheDocument();
    });
  });

  it("mostra endereço detalhado quando o backend envia campos de localização completos", async () => {
    mockFetchImoveisPorTipo.mockResolvedValue([detailedItem]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("Rua das Flores, 123 (apto 402)")).toBeInTheDocument();
      expect(screen.getByText(/Manaíra, João Pessoa - PB/)).toBeInTheDocument();
    });
  });

  it("aplica filtros sem travar carregamento", async () => {
    mockFetchImoveisPorTipo.mockResolvedValue([fallbackItem]);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText("1 imóveis encontrados • página 1 de 1")).toBeInTheDocument();
    });

    fireEvent.change(screen.getByLabelText("Bairro"), { target: { value: "Manaíra" } });
    fireEvent.click(screen.getByRole("button", { name: /aplicar filtros/i }));

    await waitFor(() => {
      expect(mockFetchImoveisPorTipo).toHaveBeenCalled();
    });
  });

  it("ignora parametro de dormitorios invalido na URL", async () => {
    mockFetchImoveisPorTipo.mockResolvedValue([fallbackItem]);

    renderPage("/vendas?dormitorios=abc");

    await waitFor(() => {
      expect(mockFetchImoveisPorTipo).toHaveBeenCalled();
    });

    const firstCall = mockFetchImoveisPorTipo.mock.calls[0];
    expect(firstCall[1]).toMatchObject({ dormitorios: undefined });
    expect(screen.queryByText(/Dormitórios:/)).not.toBeInTheDocument();
  });
});
