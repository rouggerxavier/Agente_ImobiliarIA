import { FormEvent } from "react";
import { Mail, MapPin, MessageCircle, Phone, Send } from "lucide-react";
import { toast } from "sonner";

import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const MAPS_QUERY =
  "Av. Nossa Sra. de Copacabana, 749 - Sl 501 - Copacabana, Rio de Janeiro - RJ, 22050-002, Brasil";
const MAPS_EMBED_URL = `https://www.google.com/maps?q=${encodeURIComponent(MAPS_QUERY)}&output=embed`;
const MAPS_SEARCH_URL = `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(MAPS_QUERY)}`;

const contacts = [
  { label: "Fixo", number: "(21) 2549-9000", href: "tel:+552125499000", icon: Phone },
  { label: "WhatsApp Locação", number: "(21) 99216-4686", href: "https://wa.me/5521992164686", icon: MessageCircle },
  { label: "WhatsApp Venda", number: "(21) 99398-2345", href: "https://wa.me/5521993982345", icon: MessageCircle },
];

const AEmpresa = () => {
  const handleContactSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    event.currentTarget.reset();
    toast.success("Mensagem enviada", {
      description: "Nossa equipe vai retornar seu contato em breve.",
    });
  };

  const handleNewsletterSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    event.currentTarget.reset();
    toast.success("Cadastro concluído", {
      description: "Você entrou para a newsletter da GranKasa.",
    });
  };

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
        <div className="relative mx-auto max-w-6xl px-4 py-11">
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/75 font-semibold">
            CJ 5234
          </p>
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
              Há mais de duas décadas presente no mercado imobiliário carioca, a <strong>GranKasa</strong> se consolidou
              como referência em intermediação de compra, venda e locação de imóveis residenciais e comerciais no Rio
              de Janeiro, com destaque para os bairros da Zona Sul.
            </p>
            <p style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
              Nosso diferencial está no <strong>atendimento personalizado</strong>: cada cliente recebe dedicação
              integral, com orientação transparente em todas as etapas, da prospecção à assinatura do contrato.
              Acreditamos que confiança é a base de qualquer negociação bem-sucedida.
            </p>
            <p style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
              Fundada por <strong>Vanda Farias</strong>, a empresa carrega em sua cultura o compromisso de unir
              excelência técnica e relacionamento humano para transformar cada atendimento em uma experiência segura e
              eficiente.
            </p>
            <p style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
              Nossa missão é oferecer soluções imobiliárias com agilidade, ética e alto padrão de serviço. Nossa visão
              é seguir como referência em confiança e recomendação no Rio de Janeiro.
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
                Atendimento rápido para locação, compra e venda com especialistas da Zona Sul.
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
            </aside>
          </div>
        </section>

        <section
          className="border-y border-black/10"
          style={{ background: "linear-gradient(170deg, hsl(55 58% 72%), hsl(50 52% 67%))" }}
        >
          <div className="mx-auto max-w-6xl px-4 py-12 md:py-14">
            <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-10">
              <form onSubmit={handleContactSubmit} className="rounded-2xl bg-white/85 backdrop-blur-sm p-6 md:p-8 border border-white/70 shadow-[0_15px_35px_-25px_rgba(15,23,42,0.65)]">
                <div className="mb-6">
                  <h3
                    className="text-3xl text-slate-900"
                    style={{ fontFamily: "'Sora', 'Playfair Display', serif" }}
                  >
                    Fale Conosco
                  </h3>
                  <p
                    className="mt-2 text-sm text-slate-600"
                    style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}
                  >
                    Envie sua mensagem e nossa equipe responde o quanto antes.
                  </p>
                </div>

                <div className="space-y-3">
                  <Input
                    name="name"
                    required
                    placeholder="Nome"
                    autoComplete="name"
                    className="h-11 bg-white border-white focus-visible:ring-amber-500"
                  />
                  <Input
                    type="email"
                    name="email"
                    required
                    placeholder="E-mail"
                    autoComplete="email"
                    className="h-11 bg-white border-white focus-visible:ring-amber-500"
                  />
                  <Input
                    type="tel"
                    name="phone"
                    required
                    placeholder="Telefone"
                    autoComplete="tel"
                    className="h-11 bg-white border-white focus-visible:ring-amber-500"
                  />
                  <Textarea
                    name="message"
                    required
                    placeholder="Mensagem"
                    className="min-h-[116px] resize-y bg-white border-white focus-visible:ring-amber-500"
                  />
                </div>

                <Button
                  type="submit"
                  className="mt-4 h-11 w-full bg-amber-500 text-slate-900 hover:bg-amber-400 font-semibold"
                  style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}
                >
                  <Send className="h-4 w-4" />
                  Enviar
                </Button>
              </form>

              <form onSubmit={handleNewsletterSubmit} className="rounded-2xl bg-slate-950/90 text-white p-6 md:p-7 border border-slate-800 shadow-[0_18px_40px_-28px_rgba(15,23,42,0.85)] h-fit">
                <div className="mb-6">
                  <h3
                    className="text-2xl"
                    style={{ fontFamily: "'Sora', 'Playfair Display', serif" }}
                  >
                    Newsletter
                  </h3>
                  <p
                    className="mt-2 text-sm text-slate-300"
                    style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}
                  >
                    Receba oportunidades de compra, venda e locação no seu e-mail.
                  </p>
                </div>

                <div className="space-y-3">
                  <Input
                    name="newsletterName"
                    required
                    placeholder="Nome"
                    autoComplete="name"
                    className="h-11 bg-slate-900 border-slate-700 text-slate-100 placeholder:text-slate-400 focus-visible:ring-amber-400"
                  />
                  <Input
                    type="email"
                    name="newsletterEmail"
                    required
                    placeholder="E-mail"
                    autoComplete="email"
                    className="h-11 bg-slate-900 border-slate-700 text-slate-100 placeholder:text-slate-400 focus-visible:ring-amber-400"
                  />
                </div>

                <Button
                  type="submit"
                  className="mt-4 h-11 w-full bg-amber-500 text-slate-900 hover:bg-amber-400 font-semibold"
                  style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}
                >
                  <Mail className="h-4 w-4" />
                  Cadastrar
                </Button>
              </form>
            </div>
          </div>
        </section>
      </main>

      <footer
        className="py-6 text-center text-xs text-slate-300"
        style={{ background: "hsl(220 60% 18%)", fontFamily: "'Manrope', 'DM Sans', sans-serif" }}
      >
        © {new Date().getFullYear()} GranKasa Imóveis · CRECI RJ · Todos os direitos reservados
      </footer>
    </div>
  );
};

export default AEmpresa;
