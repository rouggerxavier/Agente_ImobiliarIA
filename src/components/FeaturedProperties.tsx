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

const SectionHeader = ({ kicker, title, linkTo, linkLabel }: {
  kicker: string; title: string; linkTo: string; linkLabel: string;
}) => (
  <div className="flex flex-col md:flex-row justify-between items-end mb-20 gap-8">
    <div className="max-w-2xl">
      <span className="text-tertiary-fixed-dim font-bold uppercase tracking-[0.3em] text-xs mb-4 block">{kicker}</span>
      <h2 className="text-4xl md:text-6xl font-headline font-bold text-on-surface leading-tight">{title}</h2>
    </div>
    <Link to={linkTo}
      className="group flex items-center gap-3 text-xs font-bold uppercase tracking-widest text-on-surface-variant hover:text-primary-dark transition-colors">
      {linkLabel}
      <span className="w-12 h-px bg-outline-variant group-hover:w-16 group-hover:bg-primary-dark transition-all" />
    </Link>
  </div>
);

const FeaturedProperties = () => {
  const {
    data: locacao, isLoading: loadingLocacao, isError: isLocacaoError,
    error: locacaoError, refetch: refetchLocacao,
  } = useQuery<Imovel[], ApiError>({
    queryKey: ["imoveis", "locacao", "home"],
    queryFn: () => fetchImoveisPorTipo("locacao", { limit: 6 }),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
    retryDelay: 400,
    staleTime: 30_000,
  });

  const {
    data: venda, isLoading: loadingVenda, isError: isVendaError,
    error: vendaError, refetch: refetchVenda,
  } = useQuery<Imovel[], ApiError>({
    queryKey: ["imoveis", "venda", "home"],
    queryFn: () => fetchImoveisPorTipo("venda", { limit: 6 }),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) return false;
      return failureCount < 1;
    },
    retryDelay: 400,
    staleTime: 30_000,
  });

  const locacaoFallback = Boolean(locacao?.some((item) => item.data_source === "fallback_local"));
  const vendaFallback = Boolean(venda?.some((item) => item.data_source === "fallback_local"));

  const locacaoErrorText = locacaoError instanceof ApiError
    ? locacaoError.message : "Falha inesperada ao buscar destaques de locação.";
  const vendaErrorText = vendaError instanceof ApiError
    ? vendaError.message : "Falha inesperada ao buscar destaques de venda.";

  return (
    <>
      {/* Locação */}
      <section id="locacao-destaque" className="py-32 px-8 md:px-16 max-w-screen-2xl mx-auto">
        <SectionHeader
          kicker="Curadoria de Locação"
          title="Imóveis para Locar"
          linkTo="/locacao"
          linkLabel="Ver todos os imóveis"
        />
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
      </section>

      {/* Venda */}
      <section id="venda-destaque" className="py-32 px-8 md:px-16 max-w-screen-2xl mx-auto bg-surface-container-low">
        <SectionHeader
          kicker="Curadoria de Vendas"
          title="Imóveis à Venda"
          linkTo="/vendas"
          linkLabel="Ver todos os imóveis"
        />
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
      </section>
    </>
  );
};

export default FeaturedProperties;
