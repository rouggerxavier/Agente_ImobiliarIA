import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, RefreshCw, ShieldCheck } from "lucide-react";

import AsyncStateCard from "@/components/AsyncStateCard";
import PropertyCard from "@/components/PropertyCard";
import PropertyGridSkeleton from "@/components/PropertyGridSkeleton";
import { Button } from "@/components/ui/button";
import { ApiError, fetchImoveisPorTipo, Imovel } from "@/lib/imoveis-api";

const formatCurrency = (value: string | null) => {
  if (!value) return "-";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value));
};

const PropertyPreview = ({ imovel, tipo }: { imovel: Imovel; tipo: "locacao" | "venda" }) => {
  const valor = tipo === "locacao" ? imovel.valor_aluguel : imovel.valor_compra;
  return (
    <PropertyCard
      image={imovel.foto_url}
      title={imovel.titulo}
      location={`${imovel.bairro}, ${imovel.cidade}`}
      price={`${formatCurrency(valor)}${tipo === "locacao" ? "/mês" : ""}`}
      beds={imovel.numero_quartos ?? 0}
      baths={imovel.numero_banheiros ?? 0}
      area={Number(imovel.area_m2)}
      href={`/imovel/${imovel.codigo}`}
    />
  );
};

const fallbackNotice = (
  <div className="mb-6 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
    <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0" />
    <div>
      <p className="font-semibold">Exibindo dados de contingência.</p>
      <p className="text-amber-800/90">A API principal não respondeu a tempo, então mostramos o catálogo legado local para manter a navegação.</p>
    </div>
  </div>
);

const FeaturedProperties = () => {
  const {
    data: locacao,
    isLoading: loadingLocacao,
    isError: isLocacaoError,
    error: locacaoError,
    refetch: refetchLocacao,
  } = useQuery<Imovel[], ApiError>({
    queryKey: ["imoveis", "locacao", "home"],
    queryFn: () => fetchImoveisPorTipo("locacao", { limit: 6 }),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) {
        return false;
      }
      return failureCount < 1;
    },
    retryDelay: 400,
    staleTime: 30_000,
  });

  const {
    data: venda,
    isLoading: loadingVenda,
    isError: isVendaError,
    error: vendaError,
    refetch: refetchVenda,
  } = useQuery<Imovel[], ApiError>({
    queryKey: ["imoveis", "venda", "home"],
    queryFn: () => fetchImoveisPorTipo("venda", { limit: 6 }),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) {
        return false;
      }
      return failureCount < 1;
    },
    retryDelay: 400,
    staleTime: 30_000,
  });

  const locacaoFallback = Boolean(locacao?.some((item) => item.data_source === "fallback_local"));
  const vendaFallback = Boolean(venda?.some((item) => item.data_source === "fallback_local"));

  const locacaoErrorText =
    locacaoError instanceof ApiError
      ? locacaoError.message
      : "Falha inesperada ao buscar destaques de locação.";

  const vendaErrorText =
    vendaError instanceof ApiError
      ? vendaError.message
      : "Falha inesperada ao buscar destaques de venda.";

  return (
    <>
      <section id="locacao-destaque" className="bg-secondary py-20">
        <div className="container mx-auto px-4">
          <div className="mb-14 text-center">
            <p className="section-kicker">Destaques</p>
            <h2 className="section-title">Imóveis para Locação</h2>
          </div>

          {locacaoFallback ? fallbackNotice : null}

          {loadingLocacao ? (
            <PropertyGridSkeleton count={3} label="Carregando destaques de locação" />
          ) : isLocacaoError ? (
            <AsyncStateCard
              tone="error"
              icon={<AlertTriangle className="h-5 w-5 text-red-700" />}
              title="Não foi possível carregar os imóveis em destaque."
              description={locacaoErrorText}
              action={
                <Button type="button" variant="outline" className="mt-4" onClick={() => refetchLocacao()}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Tentar novamente
                </Button>
              }
            />
          ) : !locacao || locacao.length === 0 ? (
            <AsyncStateCard
              tone="neutral"
              title="Nenhum imóvel em destaque no momento."
              description="Novos imóveis de locação podem entrar em destaque a qualquer momento."
            />
          ) : (
            <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
              {locacao.slice(0, 3).map((imovel) => (
                <PropertyPreview key={imovel.codigo} imovel={imovel} tipo="locacao" />
              ))}
            </div>
          )}

          <div className="mt-10 text-center">
            <Link to="/locacao" className="section-link">
              Ver todos os imóveis para locação
            </Link>
          </div>
        </div>
      </section>

      <section id="venda-destaque" className="bg-background py-20">
        <div className="container mx-auto px-4">
          <div className="mb-14 text-center">
            <p className="section-kicker">Destaques</p>
            <h2 className="section-title">Imóveis para Venda</h2>
          </div>

          {vendaFallback ? fallbackNotice : null}

          {loadingVenda ? (
            <PropertyGridSkeleton count={3} label="Carregando destaques de venda" />
          ) : isVendaError ? (
            <AsyncStateCard
              tone="error"
              icon={<AlertTriangle className="h-5 w-5 text-red-700" />}
              title="Não foi possível carregar os imóveis em destaque."
              description={vendaErrorText}
              action={
                <Button type="button" variant="outline" className="mt-4" onClick={() => refetchVenda()}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Tentar novamente
                </Button>
              }
            />
          ) : !venda || venda.length === 0 ? (
            <AsyncStateCard
              tone="neutral"
              title="Nenhum imóvel em destaque no momento."
              description="Novos imóveis de venda podem entrar em destaque a qualquer momento."
            />
          ) : (
            <div className="grid gap-8 md:grid-cols-2 lg:grid-cols-3">
              {venda.slice(0, 3).map((imovel) => (
                <PropertyPreview key={imovel.codigo} imovel={imovel} tipo="venda" />
              ))}
            </div>
          )}

          <div className="mt-10 text-center">
            <Link to="/vendas" className="section-link">
              Ver todos os imóveis para venda
            </Link>
          </div>
        </div>
      </section>
    </>
  );
};

export default FeaturedProperties;
