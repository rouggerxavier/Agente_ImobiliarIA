import { KeyboardEvent, useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import AsyncStateCard from "@/components/AsyncStateCard";
import ImovelListingCard from "@/components/ImovelListingCard";
import ImoveisPageHero from "@/components/ImoveisPageHero";
import PropertyGridSkeleton from "@/components/PropertyGridSkeleton";
import SitePageShell from "@/components/SitePageShell";
import { Button } from "@/components/ui/button";
import { ApiError, fetchBusca, fetchImoveisFiltros, TipoNegocio } from "@/lib/imoveis-api";

const BUSCA_INPUT_ID = "busca-imoveis-input";
const PAGE_SIZE = 12;

const toPositivePage = (value: string | null) => {
  const parsed = Number(value || "1");
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  return Math.floor(parsed);
};

const Busca = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const qParam = searchParams.get("q") ?? "";
  const codigoParam = searchParams.get("codigo") ?? "";
  const tipoParam = (searchParams.get("tipo_negocio") as TipoNegocio | null) ?? null;
  const categoriaParam = searchParams.get("categoria") ?? "";
  const bairroParam = searchParams.get("bairro") ?? "";
  const dormitoriosParam = searchParams.get("dormitorios") ?? "";
  const page = toPositivePage(searchParams.get("page"));

  const [inputQ, setInputQ] = useState(qParam);
  const [inputCodigo, setInputCodigo] = useState(codigoParam);
  const [inputTipo, setInputTipo] = useState<TipoNegocio | "">(tipoParam ?? "");
  const [inputCategoria, setInputCategoria] = useState(categoriaParam);
  const [inputBairro, setInputBairro] = useState(bairroParam);
  const [inputDormitorios, setInputDormitorios] = useState(dormitoriosParam);

  useEffect(() => {
    setInputQ(qParam);
    setInputCodigo(codigoParam);
    setInputTipo(tipoParam ?? "");
    setInputCategoria(categoriaParam);
    setInputBairro(bairroParam);
    setInputDormitorios(dormitoriosParam);
  }, [qParam, codigoParam, tipoParam, categoriaParam, bairroParam, dormitoriosParam]);

  const { data: filtros } = useQuery({
    queryKey: ["imoveis", "filtros"],
    queryFn: () => fetchImoveisFiltros(),
  });

  const hasAnyFilter = Boolean(qParam || codigoParam || tipoParam || categoriaParam || bairroParam || dormitoriosParam);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["busca", qParam, codigoParam, tipoParam, categoriaParam, bairroParam, dormitoriosParam],
    queryFn: () =>
      fetchBusca({
        q: qParam || undefined,
        codigo: codigoParam || undefined,
        tipo_negocio: tipoParam || undefined,
        categoria: categoriaParam || undefined,
        bairro: bairroParam || undefined,
        dormitorios: dormitoriosParam ? Number(dormitoriosParam) : undefined,
        limit: 500,
      }),
    enabled: hasAnyFilter,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(500 * 2 ** attempt, 2000),
  });

  const totalResults = data?.length ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalResults / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);

  const pageItems = useMemo(() => {
    if (!data?.length) return [];
    const start = (safePage - 1) * PAGE_SIZE;
    return data.slice(start, start + PAGE_SIZE);
  }, [data, safePage]);

  const applyFilters = () => {
    const params = new URLSearchParams();
    const trimmedQ = inputQ.trim();
    const trimmedCodigo = inputCodigo.trim();

    if (trimmedQ) params.set("q", trimmedQ);
    if (trimmedCodigo) params.set("codigo", trimmedCodigo);
    if (inputTipo) params.set("tipo_negocio", inputTipo);
    if (inputCategoria) params.set("categoria", inputCategoria);
    if (inputBairro) params.set("bairro", inputBairro);
    if (inputDormitorios) params.set("dormitorios", inputDormitorios);
    params.set("page", "1");

    navigate(`/busca?${params.toString()}`);
  };

  const changePage = (nextPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(Math.max(1, Math.min(nextPage, totalPages))));
    navigate(`/busca?${params.toString()}`);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") applyFilters();
  };

  return (
    <SitePageShell
      hero={
        <ImoveisPageHero eyebrow="GranKasa" title="Busca de Imóveis" description="Busca por código e filtros avançados.">
          <div className="mt-6 grid max-w-5xl grid-cols-1 gap-3 rounded-2xl border border-white/20 bg-white/10 p-3 backdrop-blur-sm md:grid-cols-6">
            <input
              id={BUSCA_INPUT_ID}
              type="text"
              value={inputQ}
              onChange={(event) => setInputQ(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Buscar por título, bairro ou cidade"
              className="md:col-span-2 rounded-xl border border-white/20 bg-transparent px-4 py-2 text-sm text-white placeholder:text-white/60"
            />
            <input
              type="text"
              value={inputCodigo}
              onChange={(event) => setInputCodigo(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Código"
              className="rounded-xl border border-white/20 bg-transparent px-4 py-2 text-sm text-white placeholder:text-white/60"
            />
            <select
              value={inputTipo}
              onChange={(event) => setInputTipo(event.target.value as TipoNegocio | "")}
              className="rounded-xl border border-white/20 bg-slate-900/30 px-3 py-2 text-sm text-white"
            >
              <option value="">Imóvel para</option>
              <option value="venda">Venda</option>
              <option value="locacao">Aluguel</option>
            </select>
            <select
              value={inputCategoria}
              onChange={(event) => setInputCategoria(event.target.value)}
              className="rounded-xl border border-white/20 bg-slate-900/30 px-3 py-2 text-sm text-white"
            >
              <option value="">Categoria</option>
              {filtros?.categorias?.map((categoria) => (
                <option key={categoria} value={categoria}>
                  {categoria}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={applyFilters}
              className="rounded-xl bg-amber-500 px-4 py-2 text-sm font-semibold text-slate-900 hover:bg-amber-400"
            >
              <span className="inline-flex items-center gap-2">
                <Search className="h-4 w-4" />
                Buscar
              </span>
            </button>

            <select
              value={inputBairro}
              onChange={(event) => setInputBairro(event.target.value)}
              className="md:col-span-2 rounded-xl border border-white/20 bg-slate-900/30 px-3 py-2 text-sm text-white"
            >
              <option value="">Bairro</option>
              {filtros?.bairros?.map((bairro) => (
                <option key={bairro} value={bairro}>
                  {bairro}
                </option>
              ))}
            </select>
            <select
              value={inputDormitorios}
              onChange={(event) => setInputDormitorios(event.target.value)}
              className="rounded-xl border border-white/20 bg-slate-900/30 px-3 py-2 text-sm text-white"
            >
              <option value="">Dormitórios</option>
              {[1, 2, 3, 4, 5, 6].map((n) => (
                <option key={n} value={n}>
                  {n}+
                </option>
              ))}
            </select>
          </div>
        </ImoveisPageHero>
      }
    >
      <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">
        {!hasAnyFilter && <p className="text-sm text-slate-500">Use os campos acima para pesquisar o catálogo.</p>}

        {isLoading && <PropertyGridSkeleton count={6} />}

        {isError && (
          <AsyncStateCard
            tone="error"
            title="Não foi possível realizar a busca agora."
            description="Tente novamente em alguns instantes."
            action={
              <Button type="button" variant="outline" className="mt-4" onClick={() => refetch()}>
                Tentar novamente
              </Button>
            }
          />
        )}

        {!isLoading && !isError && hasAnyFilter && (
          <>
            {totalResults > 0 ? (
              <p className="mb-6 text-sm text-slate-500">
                {totalResults === 1 ? "1 imóvel encontrado" : `${totalResults} imóveis encontrados`} - página {safePage} de {totalPages}
              </p>
            ) : (
              <AsyncStateCard
                tone="neutral"
                title="Nenhum imóvel encontrado"
                description="Tente ajustar os filtros ou remover parte dos critérios."
              />
            )}

            {pageItems.length > 0 && (
              <>
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                  {pageItems.map((imovel) => (
                    <ImovelListingCard
                      key={imovel.codigo}
                      imovel={imovel}
                      detailHref={`/imovel/${imovel.codigo}`}
                      priceValue={imovel.tipo_negocio === "locacao" ? imovel.valor_aluguel : imovel.valor_compra}
                      priceSuffix={imovel.tipo_negocio === "locacao" ? "/mês" : undefined}
                    />
                  ))}
                </div>

                {totalPages > 1 && (
                  <div className="mt-8 flex items-center justify-center gap-3">
                    <Button type="button" variant="outline" disabled={safePage <= 1} onClick={() => changePage(safePage - 1)}>
                      Anterior
                    </Button>
                    <span className="text-sm text-slate-600">
                      Página {safePage} de {totalPages}
                    </span>
                    <Button
                      type="button"
                      variant="outline"
                      disabled={safePage >= totalPages}
                      onClick={() => changePage(safePage + 1)}
                    >
                      Próxima
                    </Button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </section>
    </SitePageShell>
  );
};

export default Busca;
