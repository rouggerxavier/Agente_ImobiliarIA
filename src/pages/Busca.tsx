import { useState, useEffect } from "react";
import { Link, useSearchParams, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Bath, BedDouble, Building2, Car, Layers3, MapPin, Search } from "lucide-react";

import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { fetchBusca, Imovel } from "@/lib/imoveis-api";

const formatCurrency = (value: string | null) => {
  if (!value) return "-";
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(Number(value));
};

const formatArea = (value: string) => `${Number(value).toLocaleString("pt-BR")} m²`;

const valorPrincipal = (imovel: Imovel) =>
  imovel.tipo_negocio === "locacao" ? imovel.valor_aluguel : imovel.valor_compra;

const Busca = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const initialQ = searchParams.get("q") ?? "";
  const [input, setInput] = useState(initialQ);

  // Sincroniza input quando URL muda (ex: navegar de volta)
  useEffect(() => {
    setInput(searchParams.get("q") ?? "");
  }, [searchParams]);

  const q = searchParams.get("q") ?? "";

  const { data, isLoading, isError } = useQuery({
    queryKey: ["busca", q],
    queryFn: () => fetchBusca(q),
    enabled: q.length > 0,
  });

  const handleSearch = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    navigate(`/busca?q=${encodeURIComponent(trimmed)}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch();
  };

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
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/75 font-semibold">GranKasa</p>
          <h1
            className="mt-2 text-3xl md:text-4xl text-white uppercase"
            style={{ fontFamily: "'Sora', 'Playfair Display', serif", letterSpacing: "0.09em" }}
          >
            Busca de Imóveis
          </h1>

          {/* Barra de busca inline */}
          <div className="mt-6 max-w-xl bg-white/10 backdrop-blur-sm rounded-full flex items-center p-1.5 border border-white/20">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Buscar por bairro, cidade ou tipo..."
              className="flex-1 bg-transparent px-5 py-2.5 text-sm text-white placeholder:text-white/60 focus:outline-none"
            />
            <button
              onClick={handleSearch}
              className="bg-amber-500 text-slate-900 rounded-full p-2.5 hover:bg-amber-400 transition-colors"
              aria-label="Pesquisar"
            >
              <Search className="h-4 w-4" />
            </button>
          </div>
        </div>
      </section>

      <main className="flex-1">
        <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">

          {/* Estado: sem query */}
          {!q && (
            <p className="text-slate-500 text-sm">Digite algo na barra acima para buscar imóveis.</p>
          )}

          {/* Estado: carregando */}
          {isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-72 rounded-2xl bg-white/70 animate-pulse" />
              ))}
            </div>
          )}

          {/* Estado: erro */}
          {isError && (
            <div className="rounded-2xl bg-white p-7 border border-red-200 text-red-700">
              Não foi possível realizar a busca agora.
            </div>
          )}

          {/* Resultados */}
          {!isLoading && !isError && q && (
            <>
              <p className="text-sm text-slate-500 mb-6">
                {data?.length
                  ? `${data.length} imóvel(is) encontrado(s) para "${q}"`
                  : `Nenhum imóvel encontrado para "${q}"`}
              </p>

              {data && data.length > 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {data.map((imovel) => (
                    <article
                      key={imovel.codigo}
                      className="rounded-2xl border border-black/10 bg-white overflow-hidden shadow-[0_16px_35px_-24px_rgba(15,23,42,0.55)]"
                    >
                      <div className="relative h-52 overflow-hidden">
                        <img
                          src={imovel.foto_url}
                          alt={imovel.titulo}
                          className="h-full w-full object-cover transition-transform duration-500 hover:scale-105"
                          loading="lazy"
                          onError={(e) => { (e.currentTarget as HTMLImageElement).src = "/imoveis-img/fallback.jpg"; }}
                        />
                        <div className="absolute inset-x-0 bottom-0 h-16 bg-gradient-to-t from-black/60 to-transparent" />
                      </div>
                      <div className="px-5 py-4 text-white" style={{ background: "linear-gradient(130deg, hsl(225 70% 28%), hsl(220 70% 20%))" }}>
                        <p className="text-xs uppercase tracking-[0.2em] text-white/75">Cod. {imovel.codigo}</p>
                        <h2 className="mt-2 text-lg font-semibold" style={{ fontFamily: "'Sora', 'Playfair Display', serif" }}>
                          {imovel.titulo}
                        </h2>
                        <p className="mt-2 text-2xl font-bold">
                          {formatCurrency(valorPrincipal(imovel))}
                          {imovel.tipo_negocio === "locacao" && <span className="text-sm font-normal">/mês</span>}
                        </p>
                      </div>
                      <div className="p-5">
                        <p className="flex items-center gap-2 text-sm text-slate-600">
                          <MapPin className="h-4 w-4 text-amber-600" />
                          {imovel.bairro}, {imovel.cidade}
                        </p>
                        <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-700">
                          <span className="flex items-center gap-2"><Building2 className="h-4 w-4 text-amber-600" /> {formatArea(imovel.area_m2)}</span>
                          <span className="flex items-center gap-2"><BedDouble className="h-4 w-4 text-amber-600" /> {imovel.numero_quartos ?? 0} quartos</span>
                          <span className="flex items-center gap-2"><Bath className="h-4 w-4 text-amber-600" /> {imovel.numero_banheiros ?? 0} banheiros</span>
                          <span className="flex items-center gap-2"><Car className="h-4 w-4 text-amber-600" /> {imovel.numero_vagas ?? 0} vagas</span>
                          <span className="flex items-center gap-2"><Layers3 className="h-4 w-4 text-amber-600" /> {imovel.numero_salas ?? 0} salas</span>
                        </div>
                        <Button asChild className="mt-5 w-full bg-amber-500 text-slate-900 hover:bg-amber-400 font-semibold">
                          <Link to={`/imovel/${imovel.codigo}`}>Detalhes</Link>
                        </Button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
      </main>
    </div>
  );
};

export default Busca;
