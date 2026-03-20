import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

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

const FeaturedProperties = () => {
  const {
    data: locacao,
    isLoading: loadingLocacao,
    isError: errorLocacao,
    refetch: refetchLocacao,
  } = useQuery({
    queryKey: ["imoveis", "locacao"],
    queryFn: () => fetchImoveisPorTipo("locacao"),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) {
        return false;
      }
      return failureCount < 1;
    },
  });

  const {
    data: venda,
    isLoading: loadingVenda,
    isError: errorVenda,
    refetch: refetchVenda,
  } = useQuery({
    queryKey: ["imoveis", "venda"],
    queryFn: () => fetchImoveisPorTipo("venda"),
    retry: (failureCount, error) => {
      if (error instanceof ApiError && error.status === 404) {
        return false;
      }
      return failureCount < 1;
    },
  });

  return (
    <>
      <section id="locacao-destaque" className="bg-secondary py-20">
        <div className="container mx-auto px-4">
          <div className="mb-14 text-center">
            <p className="section-kicker">Destaques</p>
            <h2 className="section-title">Imóveis para Locação</h2>
          </div>

          {loadingLocacao ? (
            <PropertyGridSkeleton count={3} />
          ) : errorLocacao ? (
            <AsyncStateCard
              tone="error"
              title="Não foi possível carregar os imóveis em destaque."
              description="Tente novamente para ver os imóveis de locação."
              action={
                <Button type="button" variant="outline" className="mt-4" onClick={() => refetchLocacao()}>
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

          {loadingVenda ? (
            <PropertyGridSkeleton count={3} />
          ) : errorVenda ? (
            <AsyncStateCard
              tone="error"
              title="Não foi possível carregar os imóveis em destaque."
              description="Tente novamente para ver os imóveis de venda."
              action={
                <Button type="button" variant="outline" className="mt-4" onClick={() => refetchVenda()}>
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
            <Link to="/venda" className="section-link">
              Ver todos os imóveis para venda
            </Link>
          </div>
        </div>
      </section>
    </>
  );
};

export default FeaturedProperties;

