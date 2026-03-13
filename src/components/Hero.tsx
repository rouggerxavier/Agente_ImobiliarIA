import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import heroImg from "@/assets/hero-building.jpg";

const Hero = () => {
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

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
      <img
        src={heroImg}
        alt="Edifício moderno de luxo ao pôr do sol"
        className="absolute inset-0 w-full h-full object-cover"
        loading="eager"
      />
      <div className="absolute inset-0" style={{ background: "var(--gradient-hero)" }} />

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
