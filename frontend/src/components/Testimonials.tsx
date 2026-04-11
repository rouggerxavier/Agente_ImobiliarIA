const testimonials = [
  {
    quote: "Sou proprietária, e sem dúvidas a Grankasa foi a melhor prestação de serviços que eu tive em termos de locação do meu imóvel! Meu contato é a Taísa, sempre muito atenciosa comigo e com o meu imóvel. Não moro no RJ, e eles prestam toda a assistência necessária. Estão sempre buscando melhorar a experiência do cliente. Recomendo muito!",
    name: "Yanna Brasil",
    role: "Local Guide · 141 avaliações",
  },
  {
    quote: "Excelente localização! Excelente atendimento! Profissionais comprometidos e atenciosos! A empresa mostra um excelente nível de qualidade dos serviços! Super organizada! Gestão de resultados! Gestão de eficiência! Recomendo os serviços!",
    name: "Helio Amancio",
    role: "Local Guide · 112 avaliações",
  },
  {
    quote: "Alugamos nosso apartamento com a Grankasa e deu tudo certo, desde o atendimento na visita até a entrega das chaves, obrigado ao Vitor e a Patrícia que foram nossos contatos principais e nos deram uma ótima experiência de contratação.",
    name: "Lucas Alcântara",
    role: "Local Guide · 21 avaliações",
  },
];

const Testimonials = () => (
  <section className="py-32 px-8 md:px-16 max-w-screen-2xl mx-auto">
    <div className="text-center mb-24">
      <span className="text-tertiary-fixed-dim font-bold uppercase tracking-[0.3em] text-xs mb-4 block">Depoimentos</span>
      <h2 className="text-4xl md:text-6xl font-headline font-bold text-on-surface">Vozes de Distinção</h2>
    </div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
      {testimonials.map((t) => (
        <div key={t.name} className="bg-surface-container-low p-12 rounded-lg relative">
          <span className="text-6xl text-tertiary-fixed-dim/20 absolute top-8 left-8 font-headline font-bold leading-none select-none">"</span>
          <p className="relative z-10 text-xl font-body text-on-surface italic leading-relaxed mb-8">{t.quote}</p>
          <div className="flex items-center gap-4">
            <div className="w-12 h-12 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant font-bold text-lg">
              {t.name[0]}
            </div>
            <div>
              <p className="font-bold text-on-surface text-sm">{t.name}</p>
              <p className="text-[10px] uppercase tracking-widest text-on-surface-variant font-medium">{t.role}</p>
            </div>
          </div>
        </div>
      ))}
    </div>
  </section>
);

export default Testimonials;

