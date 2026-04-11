import { CATALOG_FALLBACK } from "@/lib/catalog-fallback";

export type TipoNegocio = "locacao" | "venda";

type ApiErrorCode = "http" | "network" | "timeout" | "parse" | "contract";

export interface Imovel {
  id: number;
  codigo: string;
  tipo_negocio: TipoNegocio;
  titulo: string;
  descricao: string;
  foto_url: string;
  categoria: string | null;
  finalidade: string | null;
  fonte_url: string | null;
  video_url: string | null;
  mapa_url: string | null;
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
  estado?: string | null;
  uf?: string | null;
  municipio?: string | null;
  logradouro?: string | null;
  endereco?: string | null;
  numero?: string | number | null;
  complemento?: string | null;
  cep?: string | null;
  endereco_formatado?: string | null;
  ponto_referencia?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  created_at: string;
  data_source?: "api" | "fallback_local";
}

export type ImovelLocationPrecision = "exact" | "partial" | "missing";

export interface ImovelLocationInfo {
  headline: string;
  caption: string;
  precision: ImovelLocationPrecision;
}

export interface BuscaParams {
  q?: string;
  codigo?: string;
  tipo_negocio?: TipoNegocio;
  categoria?: string;
  finalidade?: string;
  bairro?: string;
  cidade?: string;
  dormitorios?: number;
  limit?: number;
  offset?: number;
}

export interface ImoveisFilterOptions {
  bairros: string[];
  categorias: string[];
  finalidades: string[];
}

export interface ContactPayload {
  nome: string;
  email: string;
  telefone: string;
  mensagem: string;
}

export interface NewsletterPayload {
  nome: string;
  email: string;
}

const LOCAL_CATALOG_IMAGES = {
  locacao: [
    "/imoveis/locacao-01.jpg",
    "/imoveis/locacao-02.jpg",
    "/imoveis/locacao-03.jpg",
    "/imoveis/locacao-04.jpg",
    "/imoveis/locacao-05.jpg",
  ],
  venda: [
    "/imoveis/venda-01.jpg",
    "/imoveis/venda-02.jpg",
    "/imoveis/venda-03.jpg",
    "/imoveis/venda-04.jpg",
    "/imoveis/venda-05.jpg",
  ],
} as const;

const LEGACY_DEAD_IMAGE_HOSTS = new Set(["cdn.vistahost.com.br"]);

export class ApiError extends Error {
  status: number;
  code: ApiErrorCode;

  constructor(status: number, message: string, code: ApiErrorCode = "http") {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const RAW_BACKEND_URL = (import.meta.env.VITE_BACKEND_URL || "").replace(/\/$/, "");
const REQUEST_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 12000);
const ENABLE_CATALOG_FALLBACK = String(import.meta.env.VITE_ENABLE_CATALOG_FALLBACK || "true").toLowerCase() !== "false";
const ENABLE_BACKEND_DISCOVERY = String(import.meta.env.VITE_ENABLE_BACKEND_DISCOVERY || "false").toLowerCase() === "true";

let cachedBackendBase: string | null = null;

function normalizeExplicitBackendUrl(rawUrl: string): string {
  if (!rawUrl) return "";
  if (typeof window === "undefined") return rawUrl;

  try {
    const parsed = new URL(rawUrl);
    const browserHost = window.location.hostname;
    const isBrowserLocal = ["localhost", "127.0.0.1"].includes(browserHost);
    const isExplicitLocal = ["localhost", "127.0.0.1"].includes(parsed.hostname);

    // In local dev we prefer same-origin requests so Vite proxy can handle backend routing
    // and avoid noisy CORS errors when VITE_BACKEND_URL points to a direct host:port.
    if (parsed.origin === window.location.origin || (isBrowserLocal && isExplicitLocal)) {
      return "";
    }
  } catch {
    return rawUrl;
  }

  return rawUrl;
}

const EXPLICIT_BACKEND_URL = normalizeExplicitBackendUrl(RAW_BACKEND_URL);

function buildQuery(params: Record<string, string | number | undefined | null>): string {
  const query = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    query.set(key, String(value));
  });
  const queryText = query.toString();
  return queryText ? `?${queryText}` : "";
}

function nowMs(): number {
  return Date.now();
}

function logCatalogEvent(event: string, payload: Record<string, unknown>) {
  const record = {
    event,
    ts: new Date().toISOString(),
    ...payload,
  };

  if (typeof window !== "undefined") {
    const traceStore = ((window as unknown as Record<string, unknown>).__catalogTrace ?? []) as Array<Record<string, unknown>>;
    traceStore.push(record);
    (window as unknown as Record<string, unknown>).__catalogTrace = traceStore.slice(-100);
  }

  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.info("[catalog]", record);
  }
}

function requestUrl(base: string, path: string): string {
  if (!base) return path;
  return `${base}${path}`;
}

function localCandidateBases(): string[] {
  if (typeof window === "undefined") return [];

  const host = window.location.hostname;
  if (!["localhost", "127.0.0.1"].includes(host)) return [];

  return [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8001",
    "http://localhost:8001",
    "http://127.0.0.1:8010",
    "http://localhost:8010",
  ];
}

function backendCandidates(): string[] {
  const ordered = [EXPLICIT_BACKEND_URL];

  if (ENABLE_BACKEND_DISCOVERY) {
    ordered.push(...localCandidateBases());
  }

  ordered.push("");
  const deduped: string[] = [];

  ordered.forEach((entry) => {
    if (entry === undefined || entry === null) return;
    const normalized = entry.replace(/\/$/, "");
    if (!deduped.includes(normalized)) deduped.push(normalized);
  });

  if (!deduped.includes("")) deduped.push("");
  return deduped;
}

function withTimeoutSignal(timeoutMs: number): { signal: AbortSignal; cleanup: () => void } {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  return {
    signal: controller.signal,
    cleanup: () => clearTimeout(timeout),
  };
}

async function probeBackend(base: string): Promise<boolean> {
  const startedAt = nowMs();
  const { signal, cleanup } = withTimeoutSignal(Math.min(REQUEST_TIMEOUT_MS, 6000));

  try {
    const response = await fetch(requestUrl(base, "/health"), {
      method: "GET",
      headers: { Accept: "application/json" },
      signal,
    });

    const contentType = response.headers.get("content-type") || "";
    if (!response.ok || !contentType.includes("application/json")) {
      logCatalogEvent("backend_probe_rejected", {
        base,
        status: response.status,
        contentType,
        durationMs: nowMs() - startedAt,
      });
      return false;
    }

    const payload = (await response.json()) as { status?: string; service?: string };
    const healthy = payload?.status === "ok";

    logCatalogEvent("backend_probe", {
      base,
      healthy,
      service: payload?.service || null,
      durationMs: nowMs() - startedAt,
    });

    return healthy;
  } catch (error) {
    logCatalogEvent("backend_probe_failed", {
      base,
      reason: error instanceof Error ? error.message : "unknown",
      durationMs: nowMs() - startedAt,
    });
    return false;
  } finally {
    cleanup();
  }
}

async function resolveBackendBase(): Promise<string> {
  if (cachedBackendBase !== null) return cachedBackendBase;

  if (!ENABLE_BACKEND_DISCOVERY) {
    cachedBackendBase = EXPLICIT_BACKEND_URL || "";
    return cachedBackendBase;
  }

  for (const candidate of backendCandidates()) {
    // Candidate vazio usa proxy/local current origin.
    if (candidate === "") {
      cachedBackendBase = "";
      return cachedBackendBase;
    }

    const healthy = await probeBackend(candidate);
    if (healthy) {
      cachedBackendBase = candidate;
      return cachedBackendBase;
    }
  }

  cachedBackendBase = EXPLICIT_BACKEND_URL || "";
  return cachedBackendBase;
}

function parseErrorPayload(raw: string): string {
  if (!raw) return "";
  try {
    const parsed = JSON.parse(raw) as { detail?: string; message?: string };
    return parsed?.detail || parsed?.message || "";
  } catch {
    return "";
  }
}

function repairMojibake(value: string): string {
  if (!value || !/[ÃÂ]/.test(value)) return value;

  try {
    const bytes = Uint8Array.from(Array.from(value).map((char) => char.charCodeAt(0)));
    const repaired = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    return repaired;
  } catch {
    return value;
  }
}

function normalizeLegacyDisplayText(value: string): string {
  if (!value) return value;

  const replacements: Array<[RegExp, string]> = [
    [/\bAndarai\b/g, "Andaraí"],
    [/\bBarra Da Tijuca\b/g, "Barra da Tijuca"],
    [/\bBarra Olimpica\b/g, "Barra Olímpica"],
    [/\bCentro Da Cidade\b/g, "Centro da Cidade"],
    [/\bEngenho De Dentro\b/g, "Engenho de Dentro"],
    [/Freguesia \(Jacarepagua\)/gi, "Freguesia (Jacarepaguá)"],
    [/\bGavea\b/g, "Gávea"],
    [/\bImovel\b/gi, "Imóvel"],
    [/\bItacuruca\b/g, "Itacuruçá"],
    [/\bJardim Botanico\b/g, "Jardim Botânico"],
    [/\bLins De Vasconcelos\b/g, "Lins de Vasconcelos"],
    [/\bMaracana\b/g, "Maracanã"],
    [/\bMeier\b/g, "Méier"],
    [/\bPonta Dos Ubas\b/g, "Ponta dos Ubas"],
    [/\bRecreio Dos Bandeirantes\b/g, "Recreio dos Bandeirantes"],
    [/\bRio De Janeiro\b/g, "Rio de Janeiro"],
    [/\bRepublica\b/g, "República"],
    [/\bSao\b/g, "São"],
    [/\bCristovao\b/g, "Cristóvão"],
    [/\bJoao\b/g, "João"],
    [/\bTodos Os Santos\b/g, "Todos os Santos"],
    [/\bVila Sao Luis\b/g, "Vila São Luís"],
    [/\bVila São Luis\b/g, "Vila São Luís"],
  ];

  let normalized = value;
  replacements.forEach(([pattern, next]) => {
    normalized = normalized.replace(pattern, next);
  });
  return normalized;
}

function normalizeDisplayValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") return Number.isFinite(value) ? String(value) : "";
  return normalizeLegacyDisplayText(repairMojibake(String(value))).trim();
}

function normalizeUf(value: unknown): string {
  const normalized = normalizeDisplayValue(value);
  if (!normalized) return "";
  return normalized.toUpperCase();
}

function hashCatalogSeed(value: string): number {
  let hash = 0;
  for (const char of value) {
    hash = (hash * 31 + char.charCodeAt(0)) >>> 0;
  }
  return hash;
}

function localCatalogImageFor(imovel: Imovel): string {
  const imagePool = imovel.tipo_negocio === "venda" ? LOCAL_CATALOG_IMAGES.venda : LOCAL_CATALOG_IMAGES.locacao;
  const seed = `${imovel.codigo}:${imovel.tipo_negocio}:${imovel.bairro}:${imovel.cidade}`;
  return imagePool[hashCatalogSeed(seed) % imagePool.length] || "/catalogo-fallback.jpg";
}

function normalizeFotoUrl(imovel: Imovel): string {
  const rawValue = typeof imovel.foto_url === "string" ? imovel.foto_url.trim() : "";
  if (!rawValue) return localCatalogImageFor(imovel);
  if (/logo\.png/i.test(rawValue)) return localCatalogImageFor(imovel);

  try {
    const parsed = new URL(rawValue, "http://localhost");
    const isLegacyDeadCatalogImage =
      LEGACY_DEAD_IMAGE_HOSTS.has(parsed.hostname) && parsed.pathname.includes("/grankasa/vista.imobi/fotos/");

    if (isLegacyDeadCatalogImage) {
      return `/imoveis/imovel-${imovel.id}.jpg`;
    }
  } catch {
    return rawValue;
  }

  return rawValue;
}

function joinLocationPieces(...pieces: Array<string | null | undefined>): string {
  return pieces.filter(Boolean).join(", ");
}

function joinCityState(city: string, state: string): string {
  if (city && state) return `${city} - ${state}`;
  return city || state;
}

function locationValue(imovel: Imovel, keys: string[]): string {
  for (const key of keys) {
    const value = normalizeDisplayValue((imovel as Record<string, unknown>)[key]);
    if (value) return value;
  }
  return "";
}

export function formatImovelLocation(imovel: Imovel): ImovelLocationInfo {
  const enderecoFormatado = locationValue(imovel, ["endereco_formatado", "enderecoFormatado", "full_address", "fullAddress"]);
  const logradouro = locationValue(imovel, ["logradouro", "endereco", "address", "rua", "street"]);
  const numero = locationValue(imovel, ["numero", "numero_endereco", "number", "street_number"]);
  const complemento = locationValue(imovel, ["complemento", "address2", "complement", "apt", "apto"]);
  const bairro = locationValue(imovel, ["bairro", "bairro_nome", "neighborhood"]);
  const cidade = locationValue(imovel, ["cidade", "municipio", "city"]);
  const estado = normalizeUf((imovel as Record<string, unknown>).estado ?? (imovel as Record<string, unknown>).uf ?? (imovel as Record<string, unknown>).state);
  const cep = locationValue(imovel, ["cep", "postal_code", "postalCode"]);
  const referencia = locationValue(imovel, ["ponto_referencia", "referencia", "reference_point", "landmark"]);
  const hasPreciseStreetAddress = Boolean(logradouro && numero);

  const cityState = joinCityState(cidade, estado);
  const region = joinLocationPieces(bairro, cityState);
  const regionFallback = region || cityState || bairro || estado;

  const preciseAddress = joinLocationPieces(logradouro, numero);
  const preciseHeadline = [preciseAddress, complemento ? `(${complemento})` : ""].filter(Boolean).join(" ");

  if (enderecoFormatado) {
    const caption = joinLocationPieces(region || undefined, cep ? `CEP ${cep}` : "", referencia ? `Referência: ${referencia}` : "");
    return {
      headline: enderecoFormatado,
      caption: caption || "Endereço informado pelo anunciante.",
      precision: hasPreciseStreetAddress ? "exact" : "partial",
    };
  }

  if (preciseHeadline) {
    const caption = joinLocationPieces(region || undefined, cep ? `CEP ${cep}` : "", referencia ? `Referência: ${referencia}` : "");
    return {
      headline: hasPreciseStreetAddress ? preciseHeadline : `Localização parcial: ${preciseHeadline}`,
      caption: caption || "Endereço informado pelo anunciante.",
      precision: hasPreciseStreetAddress ? "exact" : "partial",
    };
  }

  if (regionFallback) {
    const caption = joinLocationPieces(cep ? `CEP ${cep}` : "", referencia ? `Referência: ${referencia}` : "");
    return {
      headline: `Localização parcial: ${regionFallback}`,
      caption: caption || "Mostramos apenas a região informada no anúncio.",
      precision: "partial",
    };
  }

  const fallbackRegion = joinLocationPieces(bairro, cidade);

  if (fallbackRegion) {
    const caption = joinLocationPieces(cep ? `CEP ${cep}` : "", referencia ? `Referência: ${referencia}` : "");
    return {
      headline: `Localização parcial: ${fallbackRegion}`,
      caption: caption || "Mostramos apenas a região informada no anúncio.",
      precision: "partial",
    };
  }

  return {
    headline: "Localização não informada",
    caption: "O anúncio ainda não trouxe dados de endereço, bairro ou cidade.",
    precision: "missing",
  };
}

function sanitizeImovel(imovel: Imovel): Imovel {
  const titulo = normalizeLegacyDisplayText(repairMojibake(imovel.titulo));
  const descricao = normalizeLegacyDisplayText(repairMojibake(imovel.descricao));
  const categoria = imovel.categoria ? normalizeLegacyDisplayText(repairMojibake(imovel.categoria)) : imovel.categoria;
  const finalidade = imovel.finalidade ? normalizeLegacyDisplayText(repairMojibake(imovel.finalidade)) : imovel.finalidade;
  const bairro = normalizeLegacyDisplayText(repairMojibake(imovel.bairro));
  const cidade = normalizeLegacyDisplayText(repairMojibake(imovel.cidade));
  const estado = imovel.estado ? normalizeLegacyDisplayText(repairMojibake(imovel.estado)) : imovel.estado;
  const uf = imovel.uf ? normalizeLegacyDisplayText(repairMojibake(imovel.uf)) : imovel.uf;
  const municipio = imovel.municipio ? normalizeLegacyDisplayText(repairMojibake(imovel.municipio)) : imovel.municipio;
  const logradouro = imovel.logradouro ? normalizeLegacyDisplayText(repairMojibake(imovel.logradouro)) : imovel.logradouro;
  const endereco = imovel.endereco ? normalizeLegacyDisplayText(repairMojibake(imovel.endereco)) : imovel.endereco;
  const complemento = imovel.complemento ? normalizeLegacyDisplayText(repairMojibake(imovel.complemento)) : imovel.complemento;
  const cep = imovel.cep ? normalizeLegacyDisplayText(repairMojibake(imovel.cep)) : imovel.cep;
  const endereco_formatado = imovel.endereco_formatado
    ? normalizeLegacyDisplayText(repairMojibake(imovel.endereco_formatado))
    : imovel.endereco_formatado;
  const ponto_referencia = imovel.ponto_referencia
    ? normalizeLegacyDisplayText(repairMojibake(imovel.ponto_referencia))
    : imovel.ponto_referencia;
  const foto_url = normalizeFotoUrl(imovel);

  return {
    ...imovel,
    titulo,
    descricao,
    foto_url,
    categoria,
    finalidade,
    bairro,
    cidade,
    estado,
    uf,
    municipio,
    logradouro,
    endereco,
    complemento,
    cep,
    endereco_formatado,
    ponto_referencia,
  };
}

function markApiSource(imoveis: Imovel[]): Imovel[] {
  return imoveis.map((item) => sanitizeImovel({ ...item, data_source: "api" }));
}

async function requestJson<T>(path: string, method: "GET" | "POST", body?: unknown): Promise<T> {
  const startedAt = nowMs();
  const triedBases: string[] = [];

  const initialBase = await resolveBackendBase();
  const candidates = [initialBase, ...backendCandidates().filter((base) => base !== initialBase)];

  let lastError: ApiError | null = null;

  for (const base of candidates) {
    if (triedBases.includes(base)) continue;
    triedBases.push(base);

    const url = requestUrl(base, path);
    const { signal, cleanup } = withTimeoutSignal(REQUEST_TIMEOUT_MS);

    try {
      const response = await fetch(url, {
        method,
        headers: {
          Accept: "application/json",
          ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
        },
        body: body !== undefined ? JSON.stringify(body) : undefined,
        signal,
      });

      const contentType = response.headers.get("content-type") || "";
      const responseText = await response.text();

      logCatalogEvent("catalog_http", {
        path,
        method,
        base,
        status: response.status,
        contentType,
        durationMs: nowMs() - startedAt,
      });

      if (!response.ok) {
        const detail = parseErrorPayload(responseText);
        const message = detail || `Erro ao carregar dados (status ${response.status})`;
        throw new ApiError(response.status, message, "http");
      }

      if (!contentType.includes("application/json")) {
        throw new ApiError(
          502,
          "Resposta inválida do backend (esperado JSON). Verifique a URL da API configurada.",
          "contract",
        );
      }

      try {
        const payload = JSON.parse(responseText) as T;
        if (cachedBackendBase !== base) cachedBackendBase = base;
        return payload;
      } catch {
        throw new ApiError(502, "Falha ao interpretar resposta JSON da API.", "parse");
      }
    } catch (rawError) {
      const error =
        rawError instanceof ApiError
          ? rawError
          : rawError instanceof DOMException && rawError.name === "AbortError"
            ? new ApiError(408, "Tempo limite excedido ao consultar a API.", "timeout")
            : new ApiError(0, "Falha de rede ao consultar a API.", "network");

      lastError = error;

      logCatalogEvent("catalog_http_failed", {
        path,
        method,
        base,
        code: error.code,
        status: error.status,
        message: error.message,
        durationMs: nowMs() - startedAt,
      });

      if (cachedBackendBase === base) {
        cachedBackendBase = base === "" ? null : "";
      }
    } finally {
      cleanup();
    }
  }

  throw lastError || new ApiError(503, "Não foi possível conectar ao backend de catálogo.", "network");
}

function shouldUseCatalogFallback(error: unknown): boolean {
  if (!ENABLE_CATALOG_FALLBACK) return false;
  if (!(error instanceof ApiError)) return false;
  return error.code === "network" || error.code === "timeout" || error.code === "contract" || error.status >= 500;
}

function fallbackItems(): Imovel[] {
  return CATALOG_FALLBACK.map((item) => sanitizeImovel({ ...(item as unknown as Imovel), data_source: "fallback_local" }));
}

function applyFallbackFilters(items: Imovel[], params: BuscaParams): Imovel[] {
  const query = (params.q || "").trim().toLowerCase();
  const code = (params.codigo || "").trim().toLowerCase();
  const bairro = (params.bairro || "").trim().toLowerCase();
  const cidade = (params.cidade || "").trim().toLowerCase();
  const categoria = (params.categoria || "").trim().toLowerCase();

  let filtered = [...items];

  if (params.tipo_negocio) filtered = filtered.filter((item) => item.tipo_negocio === params.tipo_negocio);
  if (code) filtered = filtered.filter((item) => item.codigo.toLowerCase().includes(code));
  if (bairro) filtered = filtered.filter((item) => item.bairro.toLowerCase().includes(bairro));
  if (cidade) filtered = filtered.filter((item) => item.cidade.toLowerCase().includes(cidade));
  if (categoria) filtered = filtered.filter((item) => (item.categoria || "").toLowerCase().includes(categoria));
  if (typeof params.dormitorios === "number") {
    filtered = filtered.filter((item) => (item.numero_quartos || 0) >= params.dormitorios!);
  }

  if (query) {
    filtered = filtered.filter((item) => {
      const haystack = `${item.titulo} ${item.descricao} ${item.bairro} ${item.cidade} ${item.codigo}`.toLowerCase();
      return haystack.includes(query);
    });
  }

  const offset = params.offset || 0;
  const limit = params.limit || filtered.length;
  return filtered.slice(offset, offset + limit);
}

function fallbackFilters(items: Imovel[]): ImoveisFilterOptions {
  const bairros = [...new Set(items.map((item) => item.bairro).filter(Boolean))].sort((a, b) => a.localeCompare(b));
  const categorias = [...new Set(items.map((item) => item.categoria).filter(Boolean) as string[])].sort((a, b) => a.localeCompare(b));
  const finalidades = [...new Set(items.map((item) => item.finalidade).filter(Boolean) as string[])].sort((a, b) => a.localeCompare(b));

  return { bairros, categorias, finalidades };
}

export async function fetchImoveisPorTipo(
  tipo: TipoNegocio,
  options?: { limit?: number; offset?: number; categoria?: string; bairro?: string; dormitorios?: number },
): Promise<Imovel[]> {
  const query = buildQuery(options || {});

  try {
    const payload = await requestJson<Imovel[]>(`/imoveis/${tipo}${query}`, "GET");
    return markApiSource(payload);
  } catch (error) {
    if (!shouldUseCatalogFallback(error)) throw error;

    const fallback = applyFallbackFilters(fallbackItems(), {
      tipo_negocio: tipo,
      categoria: options?.categoria,
      bairro: options?.bairro,
      dormitorios: options?.dormitorios,
      limit: options?.limit,
      offset: options?.offset,
    });

    logCatalogEvent("catalog_fallback_used", {
      endpoint: `/imoveis/${tipo}`,
      count: fallback.length,
      reason: error instanceof ApiError ? error.code : "unknown",
    });

    return fallback;
  }
}

export async function fetchImovelPorCodigo(codigo: string): Promise<Imovel> {
  try {
    const payload = await requestJson<Imovel>(`/imoveis/codigo/${encodeURIComponent(codigo)}`, "GET");
    return sanitizeImovel({ ...payload, data_source: "api" });
  } catch (error) {
    if (!shouldUseCatalogFallback(error)) throw error;

    const found = fallbackItems().find((item) => item.codigo === codigo);
    if (!found) {
      if (error instanceof ApiError) throw error;
      throw new ApiError(503, "Não foi possível consultar o detalhe do imóvel no momento.", "network");
    }

    logCatalogEvent("catalog_fallback_used", {
      endpoint: `/imoveis/codigo/${codigo}`,
      count: 1,
      reason: error instanceof ApiError ? error.code : "unknown",
    });

    return found;
  }
}

export async function fetchBusca(params: BuscaParams): Promise<Imovel[]> {
  const query = buildQuery(params as Record<string, string | number | undefined | null>);

  try {
    const payload = await requestJson<Imovel[]>(`/imoveis/busca${query}`, "GET");
    return markApiSource(payload);
  } catch (error) {
    if (!shouldUseCatalogFallback(error)) throw error;

    const fallback = applyFallbackFilters(fallbackItems(), params);
    logCatalogEvent("catalog_fallback_used", {
      endpoint: "/imoveis/busca",
      count: fallback.length,
      reason: error instanceof ApiError ? error.code : "unknown",
    });
    return fallback;
  }
}

export async function fetchImoveisFiltros(): Promise<ImoveisFilterOptions> {
  try {
    const payload = await requestJson<ImoveisFilterOptions>("/imoveis/filtros", "GET");
    const normalizeList = (items: string[]) =>
      items
        .map((value) => normalizeLegacyDisplayText(repairMojibake(value)))
        .filter(Boolean)
        .sort((a, b) => a.localeCompare(b));

    return {
      bairros: normalizeList(payload.bairros || []),
      categorias: normalizeList(payload.categorias || []),
      finalidades: normalizeList(payload.finalidades || []),
    };
  } catch (error) {
    if (!shouldUseCatalogFallback(error)) throw error;

    const fallback = fallbackFilters(fallbackItems());
    logCatalogEvent("catalog_fallback_used", {
      endpoint: "/imoveis/filtros",
      count: fallback.bairros.length + fallback.categorias.length + fallback.finalidades.length,
      reason: error instanceof ApiError ? error.code : "unknown",
    });
    return fallback;
  }
}

export async function enviarContato(payload: ContactPayload): Promise<{ ok: boolean; id: string }> {
  return requestJson<{ ok: boolean; id: string }>("/contato", "POST", payload);
}

export async function cadastrarNewsletter(payload: NewsletterPayload): Promise<{ ok: boolean; id: string }> {
  return requestJson<{ ok: boolean; id: string }>("/newsletter", "POST", payload);
}

export function resetBackendResolutionForTests() {
  cachedBackendBase = null;
}
