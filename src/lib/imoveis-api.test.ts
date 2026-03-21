import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";

import { fetchImoveisPorTipo, fetchImoveisFiltros, formatImovelLocation, resetBackendResolutionForTests } from "@/lib/imoveis-api";

const fakeImovel = {
  id: 1,
  codigo: "A1",
  tipo_negocio: "locacao",
  titulo: "Imóvel de teste",
  descricao: "Descrição de teste suficientemente longa",
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
};

const jsonResponse = (payload: unknown, status = 200) =>
  new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });

const htmlResponse = (html: string, status = 200) =>
  new Response(html, {
    status,
    headers: { "Content-Type": "text/html; charset=utf-8" },
  });

describe("imoveis-api", () => {
  beforeEach(() => {
    resetBackendResolutionForTests();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("usa fallback local quando endpoint retorna HTML em vez de JSON", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/health")) return jsonResponse({ status: "ok", service: "agente_imobiliario_api" });
      if (url.includes("/imoveis/locacao")) return htmlResponse("<html>wrong server</html>");
      return jsonResponse([]);
    });

    vi.stubGlobal("fetch", fetchMock);

    const response = await fetchImoveisPorTipo("locacao", { limit: 3 });

    expect(response.length).toBeGreaterThan(0);
    expect(response.every((item) => item.data_source === "fallback_local")).toBe(true);
  });

  it("corrige texto com mojibake retornado pela API", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/health")) return jsonResponse({ status: "ok", service: "agente_imobiliario_api" });
      if (url.includes("/imoveis/locacao")) {
        return jsonResponse([
          {
            ...fakeImovel,
            titulo: "ImÃ³vel de teste",
            bairro: "ManaÃ­ra",
            cidade: "JoÃ£o Pessoa",
          },
        ]);
      }
      return jsonResponse([]);
    });

    vi.stubGlobal("fetch", fetchMock);

    const response = await fetchImoveisPorTipo("locacao", { limit: 1 });

    expect(response[0].titulo).toBe("Imóvel de teste");
    expect(response[0].bairro).toBe("Manaíra");
    expect(response[0].cidade).toBe("João Pessoa");
    expect(response[0].data_source).toBe("api");
  });

  it("retorna filtros de fallback quando a API falha", async () => {
    const fetchMock = vi.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.includes("/health")) {
        return Promise.reject(new TypeError("NetworkError"));
      }
      return Promise.reject(new TypeError("NetworkError"));
    });

    vi.stubGlobal("fetch", fetchMock);

    const filtros = await fetchImoveisFiltros();

    expect(filtros.bairros.length).toBeGreaterThan(0);
    expect(Array.isArray(filtros.categorias)).toBe(true);
    expect(Array.isArray(filtros.finalidades)).toBe(true);
  });

  it("monta uma localização completa quando o backend envia endereço detalhado", () => {
    const location = formatImovelLocation({
      ...fakeImovel,
      logradouro: "Rua das Flores",
      numero: "123",
      complemento: "apto 402",
      bairro: "Manaíra",
      cidade: "João Pessoa",
      uf: "pb",
      cep: "58038-000",
      ponto_referencia: "ao lado do shopping",
    });

    expect(location.precision).toBe("exact");
    expect(location.headline).toBe("Rua das Flores, 123 (apto 402)");
    expect(location.caption).toContain("Manaíra, João Pessoa - PB");
    expect(location.caption).toContain("CEP 58038-000");
  });

  it("deixa claro quando a localização é apenas parcial", () => {
    const location = formatImovelLocation({
      ...fakeImovel,
      bairro: "Manaíra",
      cidade: "João Pessoa",
    });

    expect(location.precision).toBe("partial");
    expect(location.headline).toBe("Localização parcial: Manaíra, João Pessoa");
    expect(location.caption).toContain("Mostramos apenas a região informada");
  });
});
