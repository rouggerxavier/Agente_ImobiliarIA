import { useState, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Search, ChevronLeft, ChevronRight } from "lucide-react";

const slides = [
  {
    url: "https://images.unsplash.com/photo-1486325212027-8081e485255e?w=1920&q=85",
    alt: "Prédio moderno de luxo ao entardecer",
  },
  {
    url: "https://images.unsplash.com/photo-1545324418-cc1a3fa10c00?w=1920&q=85",
    alt: "Edifício residencial contemporâneo",
  },
  {
    url: "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=1920&q=85",
    alt: "Casa moderna com piscina",
  },
  {
    url: "https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?w=1920&q=85",
    alt: "Condomínio de alto padrão",
  },
  {
    url: "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=1920&q=85",
    alt: "Fachada de apartamento luxuoso",
  },
];

const INTERVAL_MS = 10000;

const Hero = () => {
  const [current, setCurrent] = useState(0);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  const next = useCallback(() => {
    setCurrent((c) => (c + 1) % slides.length);
  }, []);

  const prev = useCallback(() => {
    setCurrent((c) => (c - 1 + slides.length) % slides.length);
  }, []);

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
    <section id="inicio" className="relative min-h-[85vh] flex items-center justify-center overflow-hidden">
      {/* Slides */}
      {slides.map((slide, i) => (
        <img
          key={slide.url}
          src={slide.url}
          alt={slide.alt}
          className="absolute inset-0 w-full h-full object-cover transition-opacity duration-1000"
          style={{ opacity: i === current ? 1 : 0 }}
          loading={i === 0 ? "eager" : "lazy"}
        />
      ))}

      {/* Overlay escuro */}
      <div className="absolute inset-0" style={{ background: "var(--gradient-hero)" }} />

      {/* Botão anterior */}
      <button
        onClick={prev}
        aria-label="Foto anterior"
        className="absolute left-4 top-1/2 -translate-y-1/2 z-20 flex items-center justify-center w-11 h-11 rounded-full bg-black/40 text-white hover:bg-black/65 transition-colors backdrop-blur-sm border border-white/20"
      >
        <ChevronLeft className="h-6 w-6" />
      </button>

      {/* Botão próximo */}
      <button
        onClick={next}
        aria-label="Próxima foto"
        className="absolute right-4 top-1/2 -translate-y-1/2 z-20 flex items-center justify-center w-11 h-11 rounded-full bg-black/40 text-white hover:bg-black/65 transition-colors backdrop-blur-sm border border-white/20"
      >
        <ChevronRight className="h-6 w-6" />
      </button>

      {/* Indicadores */}
      <div className="absolute bottom-6 left-1/2 -translate-x-1/2 z-20 flex gap-2">
        {slides.map((_, i) => (
          <button
            key={i}
            onClick={() => setCurrent(i)}
            aria-label={`Ir para foto ${i + 1}`}
            className={`h-1.5 rounded-full transition-all duration-300 ${
              i === current ? "w-6 bg-white" : "w-1.5 bg-white/50"
            }`}
          />
        ))}
      </div>

      {/* Conteúdo */}
      <div className="relative z-10 container mx-auto px-4 text-center">
        <h1 className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-primary-foreground mb-6 opacity-0 animate-fade-in-up">
          Encontre o imóvel <br />
          <span className="text-gradient">dos seus sonhos</span>
        </h1>
        <p
          className="font-body text-primary-foreground/80 text-lg md:text-xl max-w-2xl mx-auto mb-10 opacity-0 animate-fade-in-up"
          style={{ animationDelay: "0.15s" }}
        >
          Apartamentos, casas e coberturas nas melhores localizações. Experiência premium em cada detalhe.
        </p>

        <div
          className="max-w-xl mx-auto bg-card/95 backdrop-blur-sm rounded-full flex items-center shadow-card p-1.5 opacity-0 animate-fade-in-up"
          style={{ animationDelay: "0.3s" }}
        >
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Buscar por bairro, cidade ou tipo..."
            className="flex-1 bg-transparent px-5 py-3 font-body text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          <button
            onClick={handleSearch}
            className="bg-accent text-accent-foreground rounded-full p-3 hover:opacity-90 transition-opacity"
            aria-label="Pesquisar imóveis"
          >
            <Search className="h-5 w-5" />
          </button>
        </div>
      </div>
    </section>
  );
};

export default Hero;
