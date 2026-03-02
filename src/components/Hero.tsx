import heroImg from "@/assets/hero-building.jpg";
import { Search } from "lucide-react";

const Hero = () => {
  return (
    <section id="inicio" className="relative min-h-[85vh] flex items-center justify-center overflow-hidden">
      {/* Background image */}
      <img
        src={heroImg}
        alt="Edifício moderno de luxo ao pôr do sol"
        className="absolute inset-0 w-full h-full object-cover"
        loading="eager"
      />
      {/* Overlay */}
      <div className="absolute inset-0" style={{ background: "var(--gradient-hero)" }} />

      <div className="relative z-10 container mx-auto px-4 text-center">
        <h1
          className="font-display text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-primary-foreground mb-6 opacity-0 animate-fade-in-up"
        >
          Encontre o imóvel <br />
          <span className="text-gradient">dos seus sonhos</span>
        </h1>
        <p
          className="font-body text-primary-foreground/80 text-lg md:text-xl max-w-2xl mx-auto mb-10 opacity-0 animate-fade-in-up"
          style={{ animationDelay: "0.15s" }}
        >
          Apartamentos, casas e coberturas nas melhores localizações. Experiência premium em cada detalhe.
        </p>

        {/* Search bar */}
        <div
          className="max-w-xl mx-auto bg-card/95 backdrop-blur-sm rounded-full flex items-center shadow-card p-1.5 opacity-0 animate-fade-in-up"
          style={{ animationDelay: "0.3s" }}
        >
          <input
            type="text"
            placeholder="Buscar por bairro, cidade ou tipo..."
            className="flex-1 bg-transparent px-5 py-3 font-body text-sm text-foreground placeholder:text-muted-foreground focus:outline-none"
          />
          <button className="bg-accent text-accent-foreground rounded-full p-3 hover:opacity-90 transition-opacity">
            <Search className="h-5 w-5" />
          </button>
        </div>
      </div>
    </section>
  );
};

export default Hero;
