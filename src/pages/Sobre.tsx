import { Link } from "react-router-dom";
import { MapPin, MessageCircle, Phone } from "lucide-react";

import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";

const MAPS_QUERY =
  "Av. Nossa Sra. de Copacabana, 749 - Sl 501 - Copacabana, Rio de Janeiro - RJ, 22050-002, Brasil";
const MAPS_EMBED_URL = `https://www.google.com/maps?q=${encodeURIComponent(MAPS_QUERY)}&output=embed`;
const MAPS_SEARCH_URL = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(MAPS_QUERY)}`;

const contacts = [
  { label: "Fixo", number: "(21) 2549-9000", href: "tel:+552125499000", icon: Phone },
  { label: "WhatsApp Locacao", number: "(21) 99216-4686", href: "https://wa.me/5521992164686", icon: MessageCircle },
  { label: "WhatsApp Venda", number: "(21) 99398-2345", href: "https://wa.me/5521993982345", icon: MessageCircle },
];

const Sobre = () => {
  return (
    <div className="min-h-screen flex flex-col" style={{ background: "hsl(38 35% 92%)" }}>
      <Navbar />

      <section
        className="w-full pt-16 relative overflow-hidden"
        style={{ background: "linear-gradient(130deg, hsl(229 73% 28%), hsl(222 68% 17%))" }}
      >
        <div
          className="absolute inset-0 opacity-30"
          style={{
            backgroundImage:
              "radial-gradient(circle at 15% 25%, hsl(220 80% 58% / 0.35) 0, transparent 42%), radial-gradient(circle at 86% 32%, hsl(240 80% 72% / 0.2) 0, transparent 40%)",
          }}
        />
        <div className="relative mx-auto max-w-6xl px-4 py-11 text-center">
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/75 font-semibold">CJ 5234</p>
          <h1
            className="mt-2 text-3xl md:text-4xl text-white"
            style={{ fontFamily: "'Sora', 'Playfair Display', serif", letterSpacing: "0.09em" }}
          >
            SOBRE A GRANKASA
          </h1>
        </div>
      </section>

      <main className="flex-1">
        <section className="mx-auto max-w-6xl px-4 py-14 md:py-16">
          <div className="mx-auto max-w-4xl text-center space-y-6 text-base leading-relaxed text-slate-800">
            <p style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
              Ha mais de duas decadas presente no mercado imobiliario carioca, a <strong>GranKasa</strong> se
              consolidou como referencia em intermediacao de compra, venda e locacao de imoveis residenciais e
              comerciais no Rio de Janeiro, com destaque para os bairros da Zona Sul.
            </p>
            <p style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
              Nosso diferencial esta no <strong>atendimento personalizado</strong>: cada cliente recebe dedicacao
              integral, com orientacao transparente em todas as etapas, da prospeccao a assinatura do contrato.
              Acreditamos que confianca e a base de qualquer negociacao bem-sucedida.
            </p>
            <p style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
              Fundada por <strong>Vanda Farias</strong>, a empresa carrega em sua cultura o compromisso de unir
              excelencia tecnica e relacionamento humano para transformar cada atendimento em uma experiencia segura e
              eficiente.
            </p>
            <p style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
              Nossa missao e oferecer solucoes imobiliarias com agilidade, etica e alto padrao de servico. Nossa
              visao e seguir como referencia em confianca e recomendacao no Rio de Janeiro.
            </p>
            <p className="text-sm font-medium text-slate-600 flex items-center justify-center gap-2">
              <MapPin className="h-4 w-4 text-accent shrink-0" />
              Av. Nossa Sra. de Copacabana, 749 - Sl 501 - Copacabana, Rio de Janeiro - RJ, 22050-002
            </p>
          </div>

          <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-7 items-start">
            <div className="md:col-span-2">
              <div className="overflow-hidden rounded-2xl border border-black/10 shadow-[0_15px_40px_-18px_rgba(15,23,42,0.45)]">
                <iframe
                  title="Mapa da GranKasa em Copacabana"
                  src={MAPS_EMBED_URL}
                  width="100%"
                  height="400"
                  style={{ border: 0, display: "block" }}
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                  allowFullScreen
                />
              </div>
              <a
                href={MAPS_SEARCH_URL}
                target="_blank"
                rel="noreferrer"
                className="mt-3 inline-flex items-center gap-2 text-sm font-semibold text-amber-700 hover:text-amber-800 transition-colors"
                style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}
              >
                <MapPin className="h-4 w-4" />
                Abrir no Google Maps
              </a>
            </div>

            <aside className="rounded-2xl bg-white p-6 border border-black/5 shadow-[0_14px_32px_-20px_rgba(15,23,42,0.4)]">
              <h2
                className="text-xl font-semibold text-slate-900"
                style={{ fontFamily: "'Sora', 'Playfair Display', serif" }}
              >
                Fale com a Equipe
              </h2>
              <p
                className="mt-2 text-sm text-slate-600 leading-relaxed"
                style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}
              >
                Atendimento rapido para locacao, compra e venda com especialistas da Zona Sul.
              </p>

              <div className="mt-6 space-y-4">
                {contacts.map(({ label, number, href, icon: Icon }) => (
                  <a
                    key={label}
                    href={href}
                    target={href.startsWith("http") ? "_blank" : undefined}
                    rel={href.startsWith("http") ? "noreferrer" : undefined}
                    className="group flex items-center gap-3"
                  >
                    <span className="h-10 w-10 rounded-xl bg-amber-100 text-amber-600 flex items-center justify-center group-hover:bg-amber-500 group-hover:text-white transition-colors">
                      <Icon className="h-4 w-4" />
                    </span>
                    <span style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
                      <span className="block text-xs text-slate-500 font-medium">{label}</span>
                      <span className="block text-[15px] text-slate-800 font-semibold">{number}</span>
                    </span>
                  </a>
                ))}
              </div>

              <Button asChild className="mt-6 w-full bg-amber-500 text-slate-900 hover:bg-amber-400 font-semibold">
                <Link to="/fale-conosco">Ir para Fale Conosco</Link>
              </Button>
            </aside>
          </div>
        </section>
      </main>

      <footer
        className="py-6 text-center text-xs text-slate-300"
        style={{ background: "hsl(220 60% 18%)", fontFamily: "'Manrope', 'DM Sans', sans-serif" }}
      >
        © {new Date().getFullYear()} GranKasa Imoveis · CRECI RJ · Todos os direitos reservados
      </footer>
    </div>
  );
};

export default Sobre;
