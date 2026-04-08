const testimonials = [
  {
    quote: "A GranKasa transformou nossa busca por um imÃ³vel em uma jornada arquitetÃ´nica refinada. A atenÃ§Ã£o aos detalhes Ã© simplesmente incomparÃ¡vel no mercado de alto padrÃ£o.",
    name: "Carlos MendonÃ§a",
    role: "Profissional Autônomo",
  },
  {
    quote: "Da consulta inicial ao fechamento final, a equipe GranKasa tratou cada detalhe com precisÃ£o absoluta. Uma experiÃªncia imobiliÃ¡ria verdadeiramente personalizada.",
    name: "Ana Beatriz Lima",
    role: "Professora",
  },
  {
    quote: "NÃ£o estÃ¡vamos apenas procurando uma casa; estÃ¡vamos buscando uma obra de arte. A GranKasa entendeu isso melhor do que qualquer outra no mercado.",
    name: "Rafael Chen",
    role: "Servidor Público",
  },
];

const Testimonials = () => (
  <section className="py-32 px-8 md:px-16 max-w-screen-2xl mx-auto">
    <div className="text-center mb-24">
      <span className="text-tertiary-fixed-dim font-bold uppercase tracking-[0.3em] text-xs mb-4 block">Depoimentos</span>
      <h2 className="text-4xl md:text-6xl font-headline font-bold text-on-surface">Vozes de DistinÃ§Ã£o</h2>
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

