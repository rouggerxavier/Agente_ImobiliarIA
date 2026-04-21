import { Link } from "react-router-dom";

const CtaSection = () => (
  <section className="py-24 px-8 md:px-16 max-w-screen-2xl mx-auto mb-24">
    <div className="bg-surface-container rounded-2xl overflow-hidden flex flex-col lg:flex-row">
      <div className="lg:w-1/2 p-12 md:p-20">
        <span className="text-tertiary-fixed-dim font-bold uppercase tracking-[0.3em] text-xs mb-6 block">Próximo passo</span>
        <h2 className="text-4xl md:text-5xl font-headline font-bold text-on-surface mb-8 leading-tight">
          Pronto para encontrar o imóvel dos sonhos?{" "}
          <span className="italic">Vamos conversar.</span>
        </h2>
        <p className="text-on-surface-variant text-lg mb-12 max-w-md">
          Agende uma consulta privada com nosso curador para discutir sua visão e explorar nossos imóveis exclusivos no Rio de Janeiro.
        </p>
        <Link
          to="/fale-conosco"
          className="inline-flex items-center justify-center gap-3 w-full md:w-auto bg-primary-dark text-white py-5 px-12 rounded-lg font-bold uppercase tracking-widest text-xs hover:opacity-90 transition-all"
        >
          Agendar Consulta
        </Link>
      </div>
      <div className="lg:w-1/2 min-h-[400px]">
        <img
          src="/cta-main.png"
          alt="Imóvel exclusivo GranKasa com piscina"
          className="w-full h-full object-cover"
          style={{ objectPosition: "center 25%" }}
        />
      </div>
    </div>
  </section>
);

export default CtaSection;
