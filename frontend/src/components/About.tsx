const stats = [
  { value: "20+", label: "Anos de Mercado" },
  { value: "2.400+", label: "Imóveis Negociados" },
  { value: "1.800+", label: "Clientes Satisfeitos" },
];

const About = () => {
  return (
    <section id="sobre" className="py-32 bg-primary-dark overflow-hidden relative">
      <div className="absolute top-0 right-0 w-1/3 h-full bg-tertiary-fixed-dim/5 -skew-x-12 transform translate-x-20" />
      <div className="max-w-screen-2xl mx-auto px-8 md:px-16 flex flex-col lg:flex-row items-center gap-20">
        {/* Left: image + quote */}
        <div className="lg:w-1/2 relative">
          <div className="absolute -top-10 -left-10 w-40 h-40 border-t-2 border-l-2 border-tertiary-fixed-dim/30" />
          <img
            src="/about-main.png"
            alt="Imóvel de alto padrão GranKasa"
            className="rounded-lg shadow-2xl relative z-10 w-full object-cover"
          />
          <div className="absolute -bottom-10 -right-10 p-8 bg-surface-container-lowest shadow-xl z-20 max-w-xs hidden md:block">
            <p className="font-headline italic text-primary-dark text-xl mb-4">
              "A arquitetura é uma arte visual, e os imóveis falam por si mesmos."
            </p>
            <div className="flex items-center gap-3">
              <div className="h-px w-8 bg-tertiary-fixed-dim" />
              <span className="text-[10px] uppercase tracking-widest font-bold text-on-surface-variant">Vanda — Fundadora da GranKasa</span>
            </div>
          </div>
        </div>

        {/* Right: text + stats */}
        <div className="lg:w-1/2 text-white">
          <span className="text-tertiary-fixed-dim font-bold uppercase tracking-[0.3em] text-xs mb-4 block">Sobre Nós</span>
          <h2 className="text-4xl md:text-6xl font-headline font-bold mb-10 leading-tight">
            Definindo a Arte<br />do Bem Viver.
          </h2>
          <div className="space-y-6 text-on-primary-container text-lg leading-relaxed max-w-xl">
            <p>
              Na GranKasa, acreditamos que um imóvel é mais do que uma estrutura; é a tela para os momentos mais significativos de sua vida. Por mais de duas décadas, curadamos as propriedades mais exclusivas do Rio de Janeiro para clientes que exigem nada menos que a perfeição.
            </p>
            <p>
              Nosso compromisso com a excelência vai além da transação. Trabalhamos com arquitetos visionários e especialistas do mercado para garantir que cada imóvel em nosso portfólio represente o ápice do design moderno.
            </p>
          </div>
          <div className="mt-12 flex flex-wrap gap-12">
            {stats.map((s) => (
              <div key={s.label}>
                <p className="text-4xl font-headline font-bold text-tertiary-fixed-dim mb-1">{s.value}</p>
                <p className="text-[10px] uppercase tracking-widest font-bold opacity-60">{s.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};

export default About;
