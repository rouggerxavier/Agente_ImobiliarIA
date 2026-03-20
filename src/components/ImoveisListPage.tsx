import { useQuery } from "@tanstack/react-query";

import AsyncStateCard from "@/components/AsyncStateCard";
import ImovelListingCard from "@/components/ImovelListingCard";
import ImoveisPageHero from "@/components/ImoveisPageHero";
import PropertyGridSkeleton from "@/components/PropertyGridSkeleton";
import SitePageShell from "@/components/SitePageShell";
import { Button } from "@/components/ui/button";
import { ApiError, TipoNegocio, fetchImoveisPorTipo } from "@/lib/imoveis-api";

interface ImoveisListPageProps {
  tipo: TipoNegocio;
  titulo: string;
  descricao: string;
}

const ImoveisListPage = ({ tipo, titulo, descricao }: ImoveisListPageProps) => {
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["imoveis", tipo],
    queryFn: () => fetchImoveisPorTipo(tipo),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) {
        return false;
      }
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(500 * 2 ** attempt, 2000),
  });

  return (
    <SitePageShell hero={<ImoveisPageHero eyebrow="GranKasa" title={titulo} description={descricao} />}>
      <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">
        {isLoading && (
          <PropertyGridSkeleton />
        )}

        {isError && (
          <AsyncStateCard
            tone="error"
            title="Não foi possível carregar os imóveis agora."
            description="Tente novamente em alguns instantes."
            action={
              <Button type="button" variant="outline" className="mt-4" onClick={() => refetch()}>
                Tentar novamente
              </Button>
            }
          />
        )}

        {!isLoading && !isError && data && data.length === 0 && (
          <AsyncStateCard
            tone="neutral"
            title="Nenhum imóvel encontrado no momento."
            description="Tente ajustar os filtros ou volte mais tarde para conferir novas ofertas."
          />
        )}

        {!isLoading && !isError && data && data.length > 0 && (
          <div className="grid grid-cols-1 gap-6 md:grid-cols-2 lg:grid-cols-3">
            {data.map((imovel) => (
              <ImovelListingCard
                key={imovel.codigo}
                imovel={imovel}
                detailHref={`/imovel/${imovel.codigo}`}
                priceValue={tipo === "locacao" ? imovel.valor_aluguel : imovel.valor_compra}
                priceSuffix={tipo === "locacao" ? "/mês" : undefined}
              />
            ))}
          </div>
        )}
      </section>
    </SitePageShell>
  );
};

export default ImoveisListPage;

