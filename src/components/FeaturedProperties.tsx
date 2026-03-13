import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bath, BedDouble, MapPin, Maximize } from "lucide-react";

import { fetchImoveisPorTipo, Imovel } from "@/lib/imoveis-api";

const formatCurrency = (value: string | null) => {
  if (!value) return "-";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value));
};

const ImovelCard = ({ imovel, tipo }: { imovel: Imovel; tipo: "locacao" | "venda" }) => {
  const valor = tipo === "locacao" ? imovel.valor_aluguel : imovel.valor_compra;
  return (
    <Link to={`/imovel/${imovel.codigo}`} className="group block">
      <div className="bg-card rounded-lg overflow-hidden shadow-card hover:shadow-card-hover transition-shadow duration-300">
        <div className="relative overflow-hidden aspect-[4/3]">
          <img
            src={imovel.foto_url}
            alt={imovel.titulo}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            loading="lazy"
            onError={(e) => { (e.currentTarget as HTMLImageElement).src = "/imoveis-img/fallback.jpg"; }}
          />
          <span className="absolute top-3 left-3 bg-accent text-accent-foreground font-body text-xs font-semibold px-3 py-1 rounded-full">
            {formatCurrency(valor)}{tipo === "locacao" && "/mês"}
          </span>
        </div>
        <div className="p-5">
          <h3 className="font-display text-lg font-semibold text-card-foreground mb-1">{imovel.titulo}</h3>
          <p className="flex items-center gap-1 text-muted-foreground text-sm font-body mb-4">
            <MapPin className="h-3.5 w-3.5" /> {imovel.bairro}, {imovel.cidade}
          </p>
          <div className="flex items-center gap-4 text-muted-foreground text-sm font-body border-t border-border pt-4">
            <span className="flex items-center gap-1"><BedDouble className="h-4 w-4" /> {imovel.numero_quartos ?? 0}</span>
            <span className="flex items-center gap-1"><Bath className="h-4 w-4" /> {imovel.numero_banheiros ?? 0}</span>
            <span className="flex items-center gap-1"><Maximize className="h-4 w-4" /> {Number(imovel.area_m2).toLocaleString("pt-BR")}m²</span>
          </div>
        </div>
      </div>
    </Link>
  );
};

const SkeletonGrid = () => (
  <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
    {[...Array(3)].map((_, i) => (
      <div key={i} className="h-64 rounded-lg bg-card/50 animate-pulse" />
    ))}
  </div>
);

const FeaturedProperties = () => {
  const { data: locacao, isLoading: loadingLocacao } = useQuery({
    queryKey: ["imoveis", "locacao"],
    queryFn: () => fetchImoveisPorTipo("locacao"),
  });
  const { data: venda, isLoading: loadingVenda } = useQuery({
    queryKey: ["imoveis", "venda"],
    queryFn: () => fetchImoveisPorTipo("venda"),
  });

  return (
    <>
      {/* Seção Locação */}
      <section id="locacao-destaque" className="py-20 bg-secondary">
        <div className="container mx-auto px-4">
          <div className="text-center mb-14">
            <p className="font-body text-accent text-sm font-semibold uppercase tracking-wider mb-2">Destaques</p>
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
              Imóveis para Locação
            </h2>
          </div>
          {loadingLocacao ? (
            <SkeletonGrid />
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {locacao?.slice(0, 3).map((imovel) => (
                <ImovelCard key={imovel.codigo} imovel={imovel} tipo="locacao" />
              ))}
            </div>
          )}
          <div className="text-center mt-10">
            <Link
              to="/locacao"
              className="inline-block font-body text-sm font-semibold text-accent hover:underline"
            >
              Ver todos os imóveis para locação →
            </Link>
          </div>
        </div>
      </section>

      {/* Seção Venda */}
      <section id="venda-destaque" className="py-20 bg-background">
        <div className="container mx-auto px-4">
          <div className="text-center mb-14">
            <p className="font-body text-accent text-sm font-semibold uppercase tracking-wider mb-2">Destaques</p>
            <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground">
              Imóveis para Venda
            </h2>
          </div>
          {loadingVenda ? (
            <SkeletonGrid />
          ) : (
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
              {venda?.slice(0, 3).map((imovel) => (
                <ImovelCard key={imovel.codigo} imovel={imovel} tipo="venda" />
              ))}
            </div>
          )}
          <div className="text-center mt-10">
            <Link
              to="/venda"
              className="inline-block font-body text-sm font-semibold text-accent hover:underline"
            >
              Ver todos os imóveis para venda →
            </Link>
          </div>
        </div>
      </section>
    </>
  );
};

export default FeaturedProperties;
