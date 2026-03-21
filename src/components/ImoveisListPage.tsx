import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Filter, RefreshCw, RotateCcw, ShieldCheck } from "lucide-react";

import AsyncStateCard from "@/components/AsyncStateCard";
import ImovelListingCard from "@/components/ImovelListingCard";
import ImoveisPageHero from "@/components/ImoveisPageHero";
import PropertyGridSkeleton from "@/components/PropertyGridSkeleton";
import SitePageShell from "@/components/SitePageShell";
import { Button } from "@/components/ui/button";
import { ApiError, Imovel, TipoNegocio, fetchImoveisFiltros, fetchImoveisPorTipo } from "@/lib/imoveis-api";

interface ImoveisListPageProps {
  tipo: TipoNegocio;
  titulo: string;
  descricao: string;
}

const PAGE_SIZE = 12;

const asPage = (value: string | null) => {
  const parsed = Number(value || "1");
  if (!Number.isFinite(parsed) || parsed < 1) return 1;
  return Math.floor(parsed);
};

const ImoveisListPage = ({ tipo, titulo, descricao }: ImoveisListPageProps) => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const categoriaParam = searchParams.get("categoria") ?? "";
  const bairroParam = searchParams.get("bairro") ?? "";
  const dormitoriosParam = searchParams.get("dormitorios") ?? "";
  const page = asPage(searchParams.get("page"));

  const [inputCategoria, setInputCategoria] = useState(categoriaParam);
  const [inputBairro, setInputBairro] = useState(bairroParam);
  const [inputDormitorios, setInputDormitorios] = useState(dormitoriosParam);

  useEffect(() => {
    setInputCategoria(categoriaParam);
    setInputBairro(bairroParam);
    setInputDormitorios(dormitoriosParam);
  }, [categoriaParam, bairroParam, dormitoriosParam]);

  const { data: filtros } = useQuery({
    queryKey: ["imoveis", "filtros"],
    queryFn: () => fetchImoveisFiltros(),
    staleTime: 30_000,
  });

  const {
    data,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
  } = useQuery<Imovel[], ApiError>({
    queryKey: ["imoveis", tipo, categoriaParam, bairroParam, dormitoriosParam],
    queryFn: () =>
      fetchImoveisPorTipo(tipo, {
        categoria: categoriaParam || undefined,
        bairro: bairroParam || undefined,
        dormitorios: dormitoriosParam ? Number(dormitoriosParam) : undefined,
        limit: 500,
      }),
    retry: (failureCount, requestError) => {
      if (requestError instanceof ApiError && requestError.status === 404) return false;
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(500 * 2 ** attempt, 2000),
    staleTime: 20_000,
  });

  const totalItems = data?.length ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  const safePage = Math.min(page, totalPages);

  const pageItems = useMemo(() => {
    if (!data?.length) return [];
    const start = (safePage - 1) * PAGE_SIZE;
    return data.slice(start, start + PAGE_SIZE);
  }, [data, safePage]);

  const activeFilters = [
    categoriaParam ? `Categoria: ${categoriaParam}` : "",
    bairroParam ? `Bairro: ${bairroParam}` : "",
    dormitoriosParam ? `Dormitórios: ${dormitoriosParam}+` : "",
  ].filter(Boolean);

  const usingFallbackData = Boolean(data?.some((item) => item.data_source === "fallback_local"));

  const applyFilters = () => {
    const params = new URLSearchParams();
    if (inputCategoria) params.set("categoria", inputCategoria);
    if (inputBairro) params.set("bairro", inputBairro);
    if (inputDormitorios) params.set("dormitorios", inputDormitorios);
    params.set("page", "1");
    navigate(`?${params.toString()}`);
  };

  const resetFilters = () => {
    setInputCategoria("");
    setInputBairro("");
    setInputDormitorios("");
    navigate("?page=1");
  };

  const changePage = (nextPage: number) => {
    const params = new URLSearchParams(searchParams);
    params.set("page", String(Math.max(1, Math.min(nextPage, totalPages))));
    navigate(`?${params.toString()}`);
  };

  const errorDescription =
    error instanceof ApiError
      ? `${error.message} Se estiver no ambiente local, confirme se o backend correto está ativo.`
      : "Tente novamente em alguns instantes.";

  return (
    <SitePageShell
      hero={
        <ImoveisPageHero eyebrow="GranKasa" title={titulo} description={descricao}>
          <div className="mt-6 rounded-2xl border border-white/20 bg-white/10 p-4 backdrop-blur-sm">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
              <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.08em] text-white/80">
                Categoria
                <select
                  value={inputCategoria}
                  onChange={(event) => setInputCategoria(event.target.value)}
                  className="w-full rounded-xl border border-white/20 bg-slate-900/35 px-3 py-2 text-sm normal-case tracking-normal text-white"
                >
                  <option value="">Todas</option>
                  {filtros?.categorias?.map((categoria) => (
                    <option key={categoria} value={categoria}>
                      {categoria}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.08em] text-white/80">
                Bairro
                <select
                  value={inputBairro}
                  onChange={(event) => setInputBairro(event.target.value)}
                  className="w-full rounded-xl border border-white/20 bg-slate-900/35 px-3 py-2 text-sm normal-case tracking-normal text-white"
                >
                  <option value="">Todos</option>
                  {filtros?.bairros?.map((bairro) => (
                    <option key={bairro} value={bairro}>
                      {bairro}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1 text-xs font-semibold uppercase tracking-[0.08em] text-white/80">
                Dormitórios
                <select
                  value={inputDormitorios}
                  onChange={(event) => setInputDormitorios(event.target.value)}
                  className="w-full rounded-xl border border-white/20 bg-slate-900/35 px-3 py-2 text-sm normal-case tracking-normal text-white"
                >
                  <option value="">Qualquer</option>
                  {[1, 2, 3, 4, 5, 6].map((n) => (
                    <option key={n} value={n}>
                      {n}+
                    </option>
                  ))}
                </select>
              </label>

              <div className="flex flex-col gap-2 pt-[18px] md:pt-[22px]">
                <Button type="button" onClick={applyFilters} className="bg-amber-500 text-slate-900 hover:bg-amber-400">
                  <Filter className="mr-2 h-4 w-4" />
                  Aplicar filtros
                </Button>
                <Button type="button" variant="outline" onClick={resetFilters} className="border-white/30 bg-white/5 text-white hover:bg-white/15">
                  <RotateCcw className="mr-2 h-4 w-4" />
                  Limpar
                </Button>
              </div>
            </div>
          </div>
        </ImoveisPageHero>
      }
    >
      <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">
        {usingFallbackData && (
          <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
            <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">Modo de contingência ativo.</p>
              <p className="text-amber-800/90">Mostrando catálogo legado local enquanto a API principal está indisponível.</p>
            </div>
          </div>
        )}

        {activeFilters.length > 0 && (
          <div className="mb-5 flex flex-wrap items-center gap-2 text-xs">
            <span className="font-semibold uppercase tracking-[0.08em] text-slate-500">Filtros ativos:</span>
            {activeFilters.map((filter) => (
              <span key={filter} className="rounded-full border border-slate-200 bg-slate-50 px-3 py-1 text-slate-700">
                {filter}
              </span>
            ))}
          </div>
        )}

        {isFetching && !isLoading && (
          <p className="mb-4 text-sm text-slate-500">Atualizando resultados com os filtros selecionados...</p>
        )}

        {isLoading && <PropertyGridSkeleton label="Buscando imóveis no catálogo" />}

        {isError && (
          <AsyncStateCard
            tone="error"
            title="Não foi possível carregar os imóveis agora."
            description={errorDescription}
            action={
              <div className="flex flex-wrap gap-2 pt-1">
                <Button type="button" variant="outline" onClick={() => refetch()}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Tentar novamente
                </Button>
                <Button type="button" variant="ghost" onClick={resetFilters}>
                  Limpar filtros
                </Button>
              </div>
            }
          />
        )}

        {!isLoading && !isError && data && data.length === 0 && (
          <AsyncStateCard
            tone="neutral"
            title="Nenhum imóvel encontrado para os filtros atuais."
            description="Ajuste bairro, categoria ou dormitórios para ampliar os resultados."
            action={
              <Button type="button" variant="outline" className="mt-4" onClick={resetFilters}>
                Limpar filtros e tentar novamente
              </Button>
            }
          />
        )}

        {!isLoading && !isError && data && data.length > 0 && (
          <>
            <p className="mb-6 text-sm text-slate-600">
              {totalItems} imóveis encontrados • página {safePage} de {totalPages}
            </p>
            <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
              {pageItems.map((imovel) => (
                <ImovelListingCard
                  key={imovel.codigo}
                  imovel={imovel}
                  detailHref={`/imovel/${imovel.codigo}`}
                  priceValue={tipo === "locacao" ? imovel.valor_aluguel : imovel.valor_compra}
                  priceSuffix={tipo === "locacao" ? "/mês" : undefined}
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
      </section>
    </SitePageShell>
  );
};

export default ImoveisListPage;
