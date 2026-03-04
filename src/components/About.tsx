import { Shield, Star, Users } from "lucide-react";

const stats = [
  { icon: Shield, label: "Anos de mercado", value: "15+" },
  { icon: Star, label: "Imóveis vendidos", value: "2.400+" },
  { icon: Users, label: "Clientes satisfeitos", value: "1.800+" },
];

const About = () => {
  return (
    <section id="sobre" className="py-20 bg-background">
      <div className="container mx-auto px-4">
        <div className="max-w-3xl mx-auto text-center mb-14">
          <p className="font-body text-accent text-sm font-semibold uppercase tracking-wider mb-2">Sobre nós</p>
          <h2 className="font-display text-3xl md:text-4xl font-bold text-foreground mb-4">
            Sua parceira em cada conquista
          </h2>
          <p className="font-body text-muted-foreground text-lg leading-relaxed">
            A GranKasa é referência no mercado imobiliário, unindo tecnologia e atendimento personalizado para encontrar o imóvel ideal para você e sua família.
          </p>
        </div>
        <div className="grid sm:grid-cols-3 gap-8 max-w-2xl mx-auto">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-accent/10 mb-4">
                <s.icon className="h-6 w-6 text-accent" />
              </div>
              <p className="font-display text-3xl font-bold text-foreground">{s.value}</p>
              <p className="font-body text-muted-foreground text-sm mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default About;
