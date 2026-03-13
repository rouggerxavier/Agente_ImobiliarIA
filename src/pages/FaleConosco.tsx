import { FormEvent } from "react";
import { Mail, Send } from "lucide-react";
import { toast } from "sonner";

import Navbar from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

const FaleConosco = () => {
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
    toast.success("Cadastro concluido", {
      description: "Voce entrou para a newsletter da GranKasa.",
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
          <p className="text-[11px] uppercase tracking-[0.28em] text-white/75 font-semibold">Atendimento</p>
          <h1
            className="mt-2 text-3xl md:text-4xl text-white"
            style={{ fontFamily: "'Sora', 'Playfair Display', serif", letterSpacing: "0.09em" }}
          >
            FALE CONOSCO
          </h1>
        </div>
      </section>

      <main className="flex-1 border-y border-black/10" style={{ background: "hsl(38 35% 92%)" }}>
        <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">
          <div className="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-10">
            <form
              onSubmit={handleContactSubmit}
              className="rounded-2xl bg-white/85 backdrop-blur-sm p-6 md:p-8 border border-white/70 shadow-[0_15px_35px_-25px_rgba(15,23,42,0.65)]"
            >
              <div className="mb-6">
                <h3 className="text-3xl text-slate-900" style={{ fontFamily: "'Sora', 'Playfair Display', serif" }}>
                  Fale Conosco
                </h3>
                <p className="mt-2 text-sm text-slate-600" style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
                  Entre em contato pelo formulario abaixo.
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

            <form
              onSubmit={handleNewsletterSubmit}
              className="rounded-2xl bg-slate-950/90 text-white p-6 md:p-7 border border-slate-800 shadow-[0_18px_40px_-28px_rgba(15,23,42,0.85)] h-fit"
            >
              <div className="mb-6">
                <h3 className="text-2xl" style={{ fontFamily: "'Sora', 'Playfair Display', serif" }}>
                  Newsletter
                </h3>
                <p className="mt-2 text-sm text-slate-300" style={{ fontFamily: "'Manrope', 'DM Sans', sans-serif" }}>
                  Receba oportunidades de compra, venda e locacao no seu e-mail.
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

export default FaleConosco;
