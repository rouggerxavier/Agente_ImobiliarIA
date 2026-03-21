import { Link } from "react-router-dom";
import { MapPin, MessageCircle, Phone } from "lucide-react";

import MarketingPageShell from "@/components/MarketingPageShell";
import { Button } from "@/components/ui/button";
import { buildMapsEmbedUrl, buildMapsSearchUrl } from "@/lib/maps";

const MAPS_QUERY =
  "Av. Nossa Sra. de Copacabana, 749 - Sl 501 - Copacabana, Rio de Janeiro - RJ, 22050-002, Brasil";
const MAPS_EMBED_URL = buildMapsEmbedUrl(null, MAPS_QUERY);
const MAPS_SEARCH_URL = buildMapsSearchUrl(null, MAPS_QUERY);

const contacts = [
  { label: "Fixo", number: "(21) 2549-9000", href: "tel:+552125499000", icon: Phone },
  { label: "WhatsApp Locação", number: "(21) 99216-4686", href: "https://wa.me/5521992164686", icon: MessageCircle },
  { label: "WhatsApp Venda", number: "(21) 99398-2345", href: "https://wa.me/5521993982345", icon: MessageCircle },
];

const pageSectionClass = "mx-auto max-w-6xl px-4 py-14 md:py-16";

const Sobre = () => {
  return (
    <MarketingPageShell eyebrow="CJ 5234" title="Sobre a GranKasa" titleAlign="center">
      <section className={pageSectionClass}>
        <div className="mx-auto max-w-4xl space-y-6 text-center">
          <p className="section-copy">
            Há mais de duas décadas presente no mercado imobiliário carioca, a <strong>GranKasa</strong> se consolidou como referência em
            intermediação de compra, venda e locação de imóveis residenciais e comerciais no Rio de Janeiro, com destaque para os bairros da
            Zona Sul.
          </p>
          <p className="section-copy">
            Nosso diferencial está no <strong>atendimento personalizado</strong>: cada cliente recebe dedicação integral, com orientação
            transparente em todas as etapas, da prospecção à assinatura do contrato. Acreditamos que confiança é a base de qualquer negociação
            bem-sucedida.
          </p>
          <p className="section-copy">
            Fundada por <strong>Vanda Farias</strong>, a empresa carrega em sua cultura o compromisso de unir excelência técnica e
            relacionamento humano para transformar cada atendimento em uma experiência segura e eficiente.
          </p>
          <p className="section-copy">
            Nossa missão é oferecer soluções imobiliárias com agilidade, ética e alto padrão de serviço. Nossa visão é seguir como referência
            em confiança e recomendação no Rio de Janeiro.
          </p>
          <p className="flex items-center justify-center gap-2 text-sm font-medium text-slate-600">
            <MapPin className="h-4 w-4 shrink-0 text-accent" />
            Av. Nossa Sra. de Copacabana, 749 - Sl 501 - Copacabana, Rio de Janeiro - RJ, 22050-002
          </p>
        </div>

        <div className="mt-12 grid grid-cols-1 items-start gap-7 md:grid-cols-3">
          <div className="space-y-3 md:col-span-2">
            <div className="surface-panel">
              {MAPS_EMBED_URL && (
                <iframe
                  title="Mapa da GranKasa em Copacabana"
                  src={MAPS_EMBED_URL}
                  className="block h-[400px] w-full border-0"
                  height="400"
                  loading="lazy"
                  referrerPolicy="no-referrer-when-downgrade"
                  allowFullScreen
                />
              )}
            </div>
            {MAPS_SEARCH_URL && (
              <a href={MAPS_SEARCH_URL} target="_blank" rel="noreferrer" className="section-link">
                <MapPin className="h-4 w-4" />
                Abrir no Google Maps
              </a>
            )}
          </div>

          <aside className="surface-sidebar">
            <h2 className="font-display text-xl font-semibold text-slate-900">Fale com a Equipe</h2>
            <p className="section-copy-muted mt-2">Atendimento rápido para locação, compra e venda com especialistas da Zona Sul.</p>

            <div className="mt-6 space-y-4">
              {contacts.map(({ label, number, href, icon: Icon }) => (
                <a
                  key={label}
                  href={href}
                  target={href.startsWith("http") ? "_blank" : undefined}
                  rel={href.startsWith("http") ? "noreferrer" : undefined}
                  className="group flex items-center gap-3"
                >
                  <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-amber-100 text-amber-600 transition-colors group-hover:bg-amber-500 group-hover:text-white">
                    <Icon className="h-4 w-4" />
                  </span>
                  <span className="font-body">
                    <span className="block text-xs font-medium text-slate-500">{label}</span>
                    <span className="block text-[15px] font-semibold text-slate-800">{number}</span>
                  </span>
                </a>
              ))}
            </div>

            <Button asChild className="mt-6 w-full bg-amber-500 font-semibold text-slate-900 hover:bg-amber-400">
              <Link to="/fale-conosco">Ir para Fale Conosco</Link>
            </Button>
          </aside>
        </div>
      </section>
    </MarketingPageShell>
  );
};

export default Sobre;
