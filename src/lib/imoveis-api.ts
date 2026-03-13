export type TipoNegocio = "locacao" | "venda";

export interface Imovel {
  id: number;
  codigo: string;
  tipo_negocio: TipoNegocio;
  titulo: string;
  descricao: string;
  foto_url: string;
  valor_aluguel: string | null;
  valor_compra: string | null;
  condominio: string | null;
  iptu: string | null;
  area_m2: string;
  numero_salas: number | null;
  numero_vagas: number | null;
  numero_quartos: number | null;
  numero_banheiros: number | null;
  numero_suites: number | null;
  dependencias: boolean;
  ano_construcao: number | null;
  numero_andares: number | null;
  tem_elevadores: boolean;
  bairro: string;
  cidade: string;
  created_at: string;
}

const BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/$/, "");

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${BACKEND_URL}${path}`);
  if (!response.ok) {
    throw new Error(`Erro ao carregar dados (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function fetchImoveisPorTipo(tipo: TipoNegocio): Promise<Imovel[]> {
  return apiGet<Imovel[]>(`/imoveis/${tipo}`);
}

export function fetchImovelPorCodigo(codigo: string): Promise<Imovel> {
  return apiGet<Imovel>(`/imoveis/codigo/${encodeURIComponent(codigo)}`);
}

export function fetchBusca(q: string): Promise<Imovel[]> {
  return apiGet<Imovel[]>(`/imoveis/busca?q=${encodeURIComponent(q)}`);
}
