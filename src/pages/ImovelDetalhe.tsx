import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Building2, MapPin } from "lucide-react";

import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { fetchImovelPorCodigo } from "@/lib/imoveis-api";

const formatCurrency = (value: string | null) => {
  if (!value) return "-";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 2,
  }).format(Number(value));
};

const yesNo = (value: boolean) => (value ? "Sim" : "Nao");

const ImovelDetalhe = () => {
  const { codigo = "" } = useParams();

  const { data, isLoading, isError } = useQuery({
    queryKey: ["imovel", codigo],
    queryFn: () => fetchImovelPorCodigo(codigo),
    enabled: Boolean(codigo),
  });

  return (
    <div className="min-h-screen flex flex-col" style={{ background: "hsl(38 35% 92%)" }}>
      <Navbar />

      <section
        className="w-full pt-16 relative overflow-hidden"
        style={{ background: "linear-gradient(130deg, hsl(229 73% 28%), hsl(222 68% 17%))" }}
      >
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              "radial-gradient(circle at 15% 25%, hsl(220 80% 58% / 0.35) 0, transparent 42%), radial-gradient(circle at 86% 32%, hsl(240 80% 72% / 0.2) 0, transparent 40%)",
          }}
        />
        <div className="relative mx-auto max-w-6xl px-4 py-11">
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/75 font-semibold">
            Imovel
          </p>
          <h1
            className="mt-2 text-3xl md:text-4xl text-white uppercase"
            style={{ fontFamily: "'Sora', 'Playfair Display', serif", letterSpacing: "0.09em" }}
          >
            Detalhes do Imovel
          </h1>
        </div>
      </section>

      <main className="flex-1">
        <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">
          <Button asChild variant="ghost" className="mb-6 text-slate-700">
            <Link to="/">
              <ArrowLeft className="h-4 w-4" />
              Voltar
            </Link>
          </Button>

          {isLoading && <div className="h-56 rounded-2xl bg-white/70 animate-pulse" />}

          {isError && (
            <div className="rounded-2xl bg-white p-7 border border-red-200 text-red-700">
              Nao foi possivel carregar este imovel.
            </div>
          )}

          {!isLoading && !isError && data && (
            <div className="grid grid-cols-1 lg:grid-cols-[1.4fr_1fr] gap-7">
              <article className="rounded-2xl bg-white border border-black/10 overflow-hidden shadow-[0_16px_35px_-24px_rgba(15,23,42,0.55)]">
                <div
                  className="px-6 py-5 text-white"
                  style={{ background: "linear-gradient(130deg, hsl(225 70% 28%), hsl(220 70% 20%))" }}
                >
                  <p className="text-xs uppercase tracking-[0.2em] text-white/75">Cod. {data.codigo}</p>
                  <h2 className="mt-2 text-2xl font-semibold" style={{ fontFamily: "'Sora', 'Playfair Display', serif" }}>
                    {data.titulo}
                  </h2>
                  <p className="mt-3 text-sm text-white/80">{data.tipo_negocio === "locacao" ? "Locacao" : "Venda"}</p>
                </div>

                <div className="p-6 space-y-5">
                  <div className="overflow-hidden rounded-xl border border-black/10">
                    <img
                      src={data.foto_url}
                      alt={data.titulo}
                      className="w-full h-[280px] object-cover"
                      loading="lazy"
                      onError={(e) => { (e.currentTarget as HTMLImageElement).src = "/imoveis-img/fallback.jpg"; }}
                    />
                  </div>

                  <p className="flex items-center gap-2 text-slate-700">
                    <MapPin className="h-4 w-4 text-amber-600" />
                    {data.bairro}, {data.cidade}
                  </p>

                  <p className="text-slate-700 leading-relaxed">{data.descricao}</p>

                  <div className="grid grid-cols-2 md:grid-cols-3 gap-4 text-sm">
                    <div><strong>Area:</strong> {Number(data.area_m2).toLocaleString("pt-BR")} m²</div>
                    <div><strong>Salas:</strong> {data.numero_salas ?? 0}</div>
                    <div><strong>Vagas:</strong> {data.numero_vagas ?? 0}</div>
                    <div><strong>Quartos:</strong> {data.numero_quartos ?? 0}</div>
                    <div><strong>Banheiros:</strong> {data.numero_banheiros ?? 0}</div>
                    <div><strong>Suites:</strong> {data.numero_suites ?? 0}</div>
                    <div><strong>Dependencias:</strong> {yesNo(data.dependencias)}</div>
                    <div><strong>Ano construcao:</strong> {data.ano_construcao ?? "-"}</div>
                    <div><strong>Andares:</strong> {data.numero_andares ?? "-"}</div>
                    <div><strong>Elevadores:</strong> {yesNo(data.tem_elevadores)}</div>
                    <div><strong>Condominio:</strong> {formatCurrency(data.condominio)}</div>
                    <div><strong>IPTU:</strong> {formatCurrency(data.iptu)}</div>
                  </div>
                </div>
              </article>

              <aside className="rounded-2xl bg-white border border-black/10 p-6 h-fit shadow-[0_16px_35px_-24px_rgba(15,23,42,0.55)]">
                <h3 className="text-lg font-semibold text-slate-900" style={{ fontFamily: "'Sora', 'Playfair Display', serif" }}>
                  Valores
                </h3>

                <div className="mt-5 space-y-4 text-sm text-slate-700">
                  <div className="flex items-center justify-between">
                    <span>Valor aluguel</span>
                    <strong>{formatCurrency(data.valor_aluguel)}</strong>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Valor compra</span>
                    <strong>{formatCurrency(data.valor_compra)}</strong>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>Condominio</span>
                    <strong>{formatCurrency(data.condominio)}</strong>
                  </div>
                  <div className="flex items-center justify-between">
                    <span>IPTU</span>
                    <strong>{formatCurrency(data.iptu)}</strong>
                  </div>
                </div>

                <div className="mt-6 rounded-xl px-4 py-3 text-xs bg-amber-100/70 text-slate-700 flex items-start gap-2">
                  <Building2 className="h-4 w-4 text-amber-700 shrink-0 mt-[1px]" />
                  Dados apresentados para demonstracao da reforma visual e navegacao por codigo.
                </div>
              </aside>
            </div>
          )}
        </section>
      </main>
    </div>
  );
};

export default ImovelDetalhe;
