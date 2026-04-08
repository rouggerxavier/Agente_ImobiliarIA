import { Link } from "react-router-dom";
import { Bath, BedDouble, Building2, Car, Layers3, MapPin } from "lucide-react";

import { Button } from "@/components/ui/button";
import { formatImovelLocation, Imovel } from "@/lib/imoveis-api";

interface ImovelListingCardProps {
  imovel: Imovel;
  detailHref: string;
  priceValue: string | null;
  priceSuffix?: string;
}

const formatCurrency = (value: string | null) => {
  if (!value) return "-";

  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value));
};

const formatArea = (value: string) => `${Number(value).toLocaleString("pt-BR")} m²`;
const formatCountLabel = (value: number | null, singular: string, plural: string) => {
  const count = value ?? 0;
  return `${count} ${count === 1 ? singular : plural}`;
};

const ImovelListingCard = ({ imovel, detailHref, priceValue, priceSuffix }: ImovelListingCardProps) => {
  const location = formatImovelLocation(imovel);

  return (
    <article className="overflow-hidden rounded-2xl border border-black/10 bg-white shadow-[0_16px_35px_-24px_rgba(15,23,42,0.55)] transition-transform duration-300 hover:-translate-y-0.5 hover:shadow-[0_20px_45px_-24px_rgba(15,23,42,0.62)]">
      <div className="relative h-52 overflow-hidden">
        <img
          src={imovel.foto_url}
          alt={imovel.titulo}
          className="h-full w-full object-cover transition-transform duration-500 hover:scale-105"
          loading="lazy"
          onError={(event) => {
            (event.currentTarget as HTMLImageElement).src = "/catalogo-fallback.jpg";
          }}
        />
        <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/60 to-transparent" />
      </div>

      <div className="bg-[linear-gradient(130deg,hsl(225_70%_28%),hsl(220_70%_20%))] px-5 py-4 text-white">
        <p className="text-xs uppercase tracking-[0.2em] text-white/75">Cód. {imovel.codigo}</p>
        <h2 className="font-display mt-2 text-lg font-semibold">{imovel.titulo}</h2>
        <p className="mt-2 text-2xl font-bold">
          {formatCurrency(priceValue)}
          {priceSuffix ? <span className="text-sm font-normal">{priceSuffix}</span> : null}
        </p>
      </div>

      <div className="p-5">
        <p className="flex items-center gap-2 text-sm text-slate-600">
          <MapPin className="h-4 w-4 text-amber-600" />
          <span>{location.headline}</span>
        </p>
        <p className="mt-1 text-xs leading-relaxed text-slate-500">{location.caption}</p>

        <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-700">
          <span className="flex items-center gap-2">
            <Building2 className="h-4 w-4 text-amber-600" />
            {formatArea(imovel.area_m2)}
          </span>
          <span className="flex items-center gap-2">
            <BedDouble className="h-4 w-4 text-amber-600" />
            {formatCountLabel(imovel.numero_quartos, "quarto", "quartos")}
          </span>
          <span className="flex items-center gap-2">
            <Bath className="h-4 w-4 text-amber-600" />
            {formatCountLabel(imovel.numero_banheiros, "banheiro", "banheiros")}
          </span>
          <span className="flex items-center gap-2">
            <Car className="h-4 w-4 text-amber-600" />
            {formatCountLabel(imovel.numero_vagas, "vaga", "vagas")}
          </span>
          <span className="flex items-center gap-2">
            <Layers3 className="h-4 w-4 text-amber-600" />
            {formatCountLabel(imovel.numero_salas, "sala", "salas")}
          </span>
        </div>

        <Button asChild className="mt-5 w-full bg-amber-500 font-semibold text-slate-900 hover:bg-amber-400">
          <Link to={detailHref}>Detalhes</Link>
        </Button>
      </div>
    </article>
  );
};

export default ImovelListingCard;
