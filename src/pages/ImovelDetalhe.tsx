import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Building2, MapPin, MessageCircle, Phone } from "lucide-react";

import AsyncStateCard from "@/components/AsyncStateCard";
import ImoveisPageHero from "@/components/ImoveisPageHero";
import PropertyDetailSkeleton from "@/components/PropertyDetailSkeleton";
import SitePageShell from "@/components/SitePageShell";
import { Button } from "@/components/ui/button";
import { ApiError, fetchImovelPorCodigo, formatImovelLocation } from "@/lib/imoveis-api";
import { buildMapsEmbedUrl, buildMapsSearchUrl } from "@/lib/maps";

const CONTACT_PHONE = "+552125499000";
const CONTACT_EMAIL = "grankasa@grankasa.com.br";

const formatCurrency = (value: string | null) => {
  if (!value) return "-";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 2,
  }).format(Number(value));
};

const yesNo = (value: boolean) => (value ? "Sim" : "Não");

const ImovelDetalhe = () => {
  const { codigo = "" } = useParams();
  const navigate = useNavigate();

  const { data, isLoading, isError, error, refetch } = useQuery({
    queryKey: ["imovel", codigo],
    queryFn: () => fetchImovelPorCodigo(codigo),
    enabled: Boolean(codigo),
    retry: (failureCount, requestError) => {
      if (requestError instanceof ApiError && requestError.status === 404) return false;
      return failureCount < 1;
    },
    retryDelay: (attempt) => Math.min(500 * 2 ** attempt, 2000),
  });

  const notFoundError = error instanceof ApiError && error.status === 404;
  const location = data ? formatImovelLocation(data) : null;
  const mapFallbackQuery = data
    ? [data.endereco_formatado, data.logradouro, data.numero, data.bairro, data.cidade, data.uf ?? data.estado]
        .filter((value): value is string | number => value !== null && value !== undefined && String(value).trim().length > 0)
        .join(", ")
    : null;
  const mapEmbedUrl = data ? buildMapsEmbedUrl(data.mapa_url, mapFallbackQuery) : null;
  const mapSearchUrl = data ? buildMapsSearchUrl(data.mapa_url, mapFallbackQuery) : null;
  const mapLinkLabel = mapSearchUrl?.includes("google.") ? "Abrir no Google Maps" : "Abrir mapa de referência";

  const mailToHref = data
    ? `mailto:${CONTACT_EMAIL}?subject=${encodeURIComponent(`Interesse no imóvel ${data.codigo}`)}`
    : `mailto:${CONTACT_EMAIL}`;
  const whatsappHref = data
    ? `https://api.whatsapp.com/send?phone=${CONTACT_PHONE.replace("+", "")}&text=${encodeURIComponent(
        `Tenho interesse em visitar o imóvel de código ${data.codigo}`,
      )}`
    : `https://api.whatsapp.com/send?phone=${CONTACT_PHONE.replace("+", "")}`;

  return (
    <SitePageShell hero={<ImoveisPageHero eyebrow="Imóvel" title="Detalhes do Imóvel" />}>
      <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">
        <Button
          variant="ghost"
          className="mb-6 text-slate-700"
          onClick={() => {
            if (window.history.length > 1) navigate(-1);
            else navigate(data ? `/${data.tipo_negocio === "venda" ? "vendas" : "locacao"}` : "/");
          }}
        >
          <ArrowLeft className="h-4 w-4" />
          Voltar
        </Button>

        {isLoading && <PropertyDetailSkeleton />}

        {isError &&
          (notFoundError ? (
            <AsyncStateCard
              tone="neutral"
              title="Imóvel não encontrado para este código."
              description="Verifique o código informado ou volte para a página inicial para continuar navegando."
              action={
                <Button asChild type="button" variant="outline" className="mt-4">
                  <Link to="/">Voltar para a página inicial</Link>
                </Button>
              }
            />
          ) : (
            <AsyncStateCard
              tone="error"
              title="Não foi possível carregar este imóvel."
              description="Tente novamente em alguns instantes."
              action={
                <Button type="button" variant="outline" className="mt-4" onClick={() => refetch()}>
                  Tentar novamente
                </Button>
              }
            />
          ))}

        {!isLoading && !isError && data && (
          <div className="grid grid-cols-1 gap-7 lg:grid-cols-[1.4fr_1fr]">
            <article className="overflow-hidden rounded-2xl border border-black/10 bg-white shadow-[0_16px_35px_-24px_rgba(15,23,42,0.55)]">
              <div className="bg-[linear-gradient(130deg,hsl(225_70%_28%),hsl(220_70%_20%))] px-6 py-5 text-white">
                <p className="text-xs uppercase tracking-[0.2em] text-white/75">Cód. {data.codigo}</p>
                <h2 className="font-display mt-2 text-2xl font-semibold">{data.titulo}</h2>
                <p className="mt-3 text-sm text-white/80">
                  {data.tipo_negocio === "locacao" ? "Locação" : "Venda"}
                  {data.categoria ? ` - ${data.categoria}` : ""}
                  {data.finalidade ? ` - ${data.finalidade}` : ""}
                </p>
              </div>

              <div className="space-y-5 p-6">
                <div className="overflow-hidden rounded-xl border border-black/10">
                  <img
                    src={data.foto_url}
                    alt={data.titulo}
                    className="h-[280px] w-full object-cover"
                    loading="lazy"
                    onError={(event) => {
                      (event.currentTarget as HTMLImageElement).src = "/catalogo-fallback.jpg";
                    }}
                  />
                </div>

                {location && (
                  <div className="rounded-xl border border-amber-200 bg-amber-50/80 px-4 py-3">
                    <p className="flex items-start gap-2 text-slate-800">
                      <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
                      <span className="font-medium">{location.headline}</span>
                    </p>
                    <p className="mt-1 text-sm text-slate-600">{location.caption}</p>
                    {mapSearchUrl && (
                      <a
                        href={mapSearchUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="mt-2 inline-flex text-sm font-medium text-amber-700 hover:underline"
                      >
                        {mapLinkLabel}
                      </a>
                    )}
                  </div>
                )}

                {mapEmbedUrl && (
                  <div className="space-y-3">
                    <div className="overflow-hidden rounded-xl border border-black/10">
                      <iframe
                        title={`Mapa do imóvel ${data.codigo}`}
                        src={mapEmbedUrl}
                        className="block h-[320px] w-full border-0"
                        loading="lazy"
                        referrerPolicy="no-referrer-when-downgrade"
                        allowFullScreen
                      />
                    </div>
                    {mapSearchUrl && (
                      <a
                        href={mapSearchUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-2 text-sm font-semibold text-amber-700 hover:underline"
                      >
                        <MapPin className="h-4 w-4" />
                        {mapLinkLabel}
                      </a>
                    )}
                  </div>
                )}

                <p className="leading-relaxed text-slate-700">{data.descricao}</p>

                <div className="grid grid-cols-2 gap-4 text-sm md:grid-cols-3">
                  <div>
                    <strong>Área:</strong> {Number(data.area_m2).toLocaleString("pt-BR")} m²
                  </div>
                  <div>
                    <strong>Salas:</strong> {data.numero_salas ?? 0}
                  </div>
                  <div>
                    <strong>Vagas:</strong> {data.numero_vagas ?? 0}
                  </div>
                  <div>
                    <strong>Quartos:</strong> {data.numero_quartos ?? 0}
                  </div>
                  <div>
                    <strong>Banheiros:</strong> {data.numero_banheiros ?? 0}
                  </div>
                  <div>
                    <strong>Suítes:</strong> {data.numero_suites ?? 0}
                  </div>
                  <div>
                    <strong>Dependências:</strong> {yesNo(data.dependencias)}
                  </div>
                  <div>
                    <strong>Ano de construção:</strong> {data.ano_construcao ?? "-"}
                  </div>
                  <div>
                    <strong>Andares:</strong> {data.numero_andares ?? "-"}
                  </div>
                  <div>
                    <strong>Elevadores:</strong> {yesNo(data.tem_elevadores)}
                  </div>
                  <div>
                    <strong>Condomínio:</strong> {formatCurrency(data.condominio)}
                  </div>
                  <div>
                    <strong>IPTU:</strong> {formatCurrency(data.iptu)}
                  </div>
                </div>

                {(data.video_url || mapSearchUrl || data.fonte_url) && (
                  <div className="rounded-xl border border-black/10 bg-slate-50 p-4 text-sm text-slate-700 space-y-2">
                    <h3 className="font-semibold text-slate-900">Mídias e referências</h3>
                    {data.video_url && (
                      <a href={data.video_url} target="_blank" rel="noreferrer" className="text-amber-700 hover:underline block">
                        Vídeo do imóvel
                      </a>
                    )}
                    {mapSearchUrl && (
                      <a href={mapSearchUrl} target="_blank" rel="noreferrer" className="text-amber-700 hover:underline block">
                        Localização
                      </a>
                    )}
                    {data.fonte_url && (
                      <a href={data.fonte_url} target="_blank" rel="noreferrer" className="text-amber-700 hover:underline block">
                        Fonte original
                      </a>
                    )}
                  </div>
                )}
              </div>
            </article>

            <aside className="h-fit rounded-2xl border border-black/10 bg-white p-6 shadow-[0_16px_35px_-24px_rgba(15,23,42,0.55)]">
              <h3 className="font-display text-lg font-semibold text-slate-900">Valores</h3>

              <div className="mt-5 space-y-4 text-sm text-slate-700">
                <div className="flex items-center justify-between">
                  <span>Valor do aluguel</span>
                  <strong>{formatCurrency(data.valor_aluguel)}</strong>
                </div>
                <div className="flex items-center justify-between">
                  <span>Valor de compra</span>
                  <strong>{formatCurrency(data.valor_compra)}</strong>
                </div>
                <div className="flex items-center justify-between">
                  <span>Condomínio</span>
                  <strong>{formatCurrency(data.condominio)}</strong>
                </div>
                <div className="flex items-center justify-between">
                  <span>IPTU</span>
                  <strong>{formatCurrency(data.iptu)}</strong>
                </div>
              </div>

              <div className="mt-6 rounded-xl bg-amber-100/70 px-4 py-3 text-xs text-slate-700 space-y-3">
                <p className="flex items-start gap-2">
                  <Building2 className="mt-[1px] h-4 w-4 shrink-0 text-amber-700" />
                  Agende sua visita com a equipe GranKasa.
                </p>
                <a href={`tel:${CONTACT_PHONE}`} className="flex items-center gap-2 text-slate-800 hover:underline">
                  <Phone className="h-4 w-4" /> (21) 2549-9000
                </a>
                <a href={whatsappHref} target="_blank" rel="noreferrer" className="flex items-center gap-2 text-slate-800 hover:underline">
                  <MessageCircle className="h-4 w-4" /> WhatsApp
                </a>
                <a href={mailToHref} className="text-slate-800 hover:underline block">
                  {CONTACT_EMAIL}
                </a>
              </div>
            </aside>
          </div>
        )}
      </section>
    </SitePageShell>
  );
};

export default ImovelDetalhe;
