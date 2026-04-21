import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ChevronLeft, ChevronRight, MapPin } from "lucide-react";

const slides = [
  { url: "/hero-1.png", alt: "Imóvel de alto padrão em Copacabana" },
  { url: "/hero-2.png", alt: "Residência de luxo com vista privilegiada" },
  { url: "/hero-3.png", alt: "Apartamento contemporâneo de alto padrão" },
  { url: "/hero-4.png", alt: "Condomínio exclusivo com área de lazer" },
  { url: "/hero-5.png", alt: "Fachada moderna em localização prime" },
];

const INTERVAL_MS = 10000;
const HERO_SEARCH_INPUT_ID = "hero-property-search";

const Hero = () => {
  const [current, setCurrent] = useState(0);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const next = useCallback(() => { setCurrent((c) => (c + 1) % slides.length); }, []);
  const prev = useCallback(() => { setCurrent((c) => (c - 1 + slides.length) % slides.length); }, []);

  useEffect(() => {
    const timer = setInterval(next, INTERVAL_MS);
    return () => clearInterval(timer);
  }, [next]);

  const handleSearch = () => {
    const q = query.trim();
    if (!q) return;
    navigate(`/busca?q=${encodeURIComponent(q)}`);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") handleSearch();
  };

  return (
    <header className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Slideshow */}
      {slides.map((slide, i) => (
        <img key={slide.url} src={slide.url} alt={slide.alt}
          className="absolute inset-0 w-full h-full object-cover transition-opacity duration-1000"
          style={{ opacity: i === current ? 1 : 0 }}
          loading={i === 0 ? "eager" : "lazy"} />
      ))}
      {/* Overlays */}
      <div className="absolute inset-0 bg-primary-dark/40 mix-blend-multiply" />
      <div className="absolute inset-0 bg-gradient-to-b from-transparent via-primary-dark/20 to-primary-dark/80" />

      {/* Prev/Next */}
      <button type="button" onClick={prev} aria-label="Foto anterior"
        className="absolute left-4 top-1/2 -translate-y-1/2 z-20 flex items-center justify-center w-11 h-11 rounded-full bg-black/40 text-white hover:bg-black/65 transition-colors backdrop-blur-sm border border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
        <ChevronLeft className="h-6 w-6" />
      </button>
      <button type="button" onClick={next} aria-label="Próxima foto"
        className="absolute right-4 top-1/2 -translate-y-1/2 z-20 flex items-center justify-center w-11 h-11 rounded-full bg-black/40 text-white hover:bg-black/65 transition-colors backdrop-blur-sm border border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
        <ChevronRight className="h-6 w-6" />
      </button>

      {/* Dots */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex gap-1">
        {slides.map((_, i) => {
          const active = i === current;
          return (
            <button key={i} type="button" onClick={() => setCurrent(i)}
              aria-label={`Ir para foto ${i + 1}`} aria-current={active ? "true" : "false"}
              className="flex h-11 w-11 items-center justify-center rounded-full focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white">
              <span className={`h-1.5 rounded-full transition-all duration-300 ${active ? "w-6 bg-white" : "w-1.5 bg-white/50"}`} />
            </button>
          );
        })}
      </div>

      {/* Content */}
      <div className="relative z-10 w-full max-w-7xl mx-auto px-8 md:px-16 pt-24 text-center md:text-left">
        <div className="inline-block bg-tertiary-fixed-dim/20 backdrop-blur-md px-4 py-1 rounded-full mb-6 border border-tertiary-fixed-dim/30">
          <span className="text-tertiary-fixed text-xs uppercase tracking-[0.2em] font-bold">Excelência em Curadoria</span>
        </div>
        <h1 className="text-5xl md:text-8xl font-headline font-bold text-white mb-6 leading-[1.1] tracking-tight max-w-4xl">
          Elevando sua <br /><span className="text-tertiary-fixed">Experiência</span> Imobiliária.
        </h1>
        <p className="text-lg md:text-2xl text-slate-200 mb-12 max-w-2xl font-light leading-relaxed">
          Descubra imóveis extraordinários que redefinem o bem viver. Curadoria das melhores arquiteturas em Copacabana e no Rio.
        </p>

        {/* Search Bar */}
        <div className="w-full max-w-4xl bg-white/90 backdrop-blur-2xl p-4 md:p-2 rounded-xl shadow-2xl flex flex-col md:flex-row items-stretch md:items-center gap-2">
          <div className="flex-1 flex items-center gap-3 p-4">
            <MapPin className="h-5 w-5 text-tertiary-fixed-dim shrink-0" />
            <div className="flex flex-col flex-1">
              <label htmlFor={HERO_SEARCH_INPUT_ID} className="text-[10px] uppercase tracking-widest text-on-surface-variant font-bold mb-1">
                Buscar imóvel
              </label>
              <input
                id={HERO_SEARCH_INPUT_ID}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Bairro, cidade ou tipo..."
                className="bg-transparent border-none focus:ring-0 w-full text-on-surface p-0 font-medium text-sm focus:outline-none"
              />
            </div>
          </div>
          <button type="button" onClick={handleSearch}
            className="bg-primary-dark text-white h-full px-10 py-5 rounded-lg font-bold uppercase tracking-widest text-xs flex items-center justify-center gap-2 hover:bg-primary-dark/90 transition-all">
            <Search className="h-4 w-4" />
            Buscar
          </button>
        </div>
      </div>
    </header>
  );
};

export default Hero;
