import { KeyboardEvent, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Search } from "lucide-react";

import AsyncStateCard from "@/components/AsyncStateCard";
import ImovelListingCard from "@/components/ImovelListingCard";
import ImoveisPageHero from "@/components/ImoveisPageHero";
import PropertyGridSkeleton from "@/components/PropertyGridSkeleton";
import SitePageShell from "@/components/SitePageShell";
import { Button } from "@/components/ui/button";
import { ApiError, fetchBusca } from "@/lib/imoveis-api";

const BUSCA_INPUT_ID = "busca-imoveis-input";

const Busca = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQ = searchParams.get("q") ?? "";
  const [input, setInput] = useState(initialQ);

  useEffect(() => {
    setInput(searchParams.get("q") ?? "");
  }, [searchParams]);

  const q = searchParams.get("q") ?? "";

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["busca", q],
    queryFn: () => fetchBusca(q),
    enabled: q.length > 0,
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) {
        return false;
      }
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(500 * 2 ** attempt, 2000),
  });

  const handleSearch = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    navigate(`/busca?q=${encodeURIComponent(trimmed)}`);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter") handleSearch();
  };

  const hasInput = input.trim().length > 0;

  return (
    <SitePageShell
      hero={
        <ImoveisPageHero eyebrow="GranKasa" title="Busca de Imóveis">
          <div className="mt-6 flex max-w-xl items-center rounded-full border border-white/20 bg-white/10 p-1.5 backdrop-blur-sm">
            <label htmlFor={BUSCA_INPUT_ID} className="sr-only">
              Buscar por bairro, cidade ou tipo de imóvel
            </label>
            <input
              id={BUSCA_INPUT_ID}
              type="text"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Buscar por bairro, cidade ou tipo..."
              className="flex-1 bg-transparent px-5 py-2.5 text-sm text-white placeholder:text-white/60 focus:outline-none"
            />
            <button
              type="button"
              onClick={handleSearch}
              disabled={!hasInput}
              className="rounded-full bg-amber-500 p-2.5 text-slate-900 transition-colors hover:bg-amber-400 disabled:opacity-60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white"
              aria-label="Pesquisar"
            >
              <Search className="h-4 w-4" />
            </button>
          </div>
        </ImoveisPageHero>
      }
    >
      <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">
        {!q && <p className="text-sm text-slate-500">Digite algo na barra acima para buscar imóveis.</p>}

        {isLoading && <PropertyGridSkeleton count={3} />}

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

        {!isLoading && !isError && q && (
          <>
            {data?.length ? (
              <p className="mb-6 text-sm text-slate-500">
                {data.length === 1 ? `1 imóvel encontrado para "${q}"` : `${data.length} imóveis encontrados para "${q}"`}
              </p>
            ) : (
              <AsyncStateCard
                tone="neutral"
                title={`Nenhum imóvel encontrado para "${q}"`}
                description="Tente alterar os termos da busca ou pesquise outro bairro, cidade ou tipo."
              />
            )}

            {data && data.length > 0 && (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
                {data.map((imovel) => (
                  <ImovelListingCard
                    key={imovel.codigo}
                    imovel={imovel}
                    detailHref={`/imovel/${imovel.codigo}`}
                    priceValue={imovel.tipo_negocio === "locacao" ? imovel.valor_aluguel : imovel.valor_compra}
                    priceSuffix={imovel.tipo_negocio === "locacao" ? "/mês" : undefined}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </section>
    </SitePageShell>
  );
};

export default Busca;