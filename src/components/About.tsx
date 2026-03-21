import { Shield, Star, Users } from "lucide-react";

const stats = [
  { icon: Shield, label: "Anos de mercado", value: "20+" },
  { icon: Star, label: "Imóveis vendidos", value: "2.400+" },
  { icon: Users, label: "Clientes satisfeitos", value: "1.800+" },
];

const About = () => {
  return (
    <section id="sobre" className="bg-background py-20">
      <div className="container mx-auto px-4">
        <div className="mx-auto mb-14 max-w-3xl text-center">
          <p className="section-kicker">Sobre nós</p>
          <h2 className="section-title mb-4">Sua parceira em cada conquista</h2>
          <p className="section-copy text-lg text-muted-foreground">
            A GranKasa é referência no mercado imobiliário, unindo tecnologia e atendimento personalizado para
            encontrar o imóvel ideal para você e sua família.
          </p>
        </div>

        <div className="mx-auto grid max-w-2xl gap-8 sm:grid-cols-3">
          {stats.map((s) => (
            <div key={s.label} className="text-center">
              <div className="surface-stat mb-4 h-14 w-14">
                <s.icon className="h-6 w-6 text-accent" />
              </div>
              <p className="font-display text-3xl font-bold text-foreground">{s.value}</p>
              <p className="section-copy-muted mt-1">{s.label}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
};

export default About;
