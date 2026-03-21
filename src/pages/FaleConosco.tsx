import { FormEvent, useState } from "react";
import { Mail, Send } from "lucide-react";
import { toast } from "sonner";

import MarketingPageShell from "@/components/MarketingPageShell";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { cadastrarNewsletter, enviarContato } from "@/lib/imoveis-api";

const contactCardClass = "surface-card-soft p-6 md:p-8";
const newsletterCardClass = "surface-card-dark h-fit p-6 md:p-7";
const fieldShellClass = "space-y-1.5";
const inputClass = "h-11 border-white bg-white focus-visible:ring-amber-500";
const darkInputClass =
  "h-11 border-slate-700 bg-slate-900 text-slate-100 placeholder:text-slate-400 focus-visible:ring-amber-400";
const buttonClass = "mt-4 h-11 w-full bg-amber-500 font-semibold text-slate-900 hover:bg-amber-400";

const FaleConosco = () => {
  const [sendingContact, setSendingContact] = useState(false);
  const [sendingNewsletter, setSendingNewsletter] = useState(false);

  const handleContactSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    try {
      setSendingContact(true);
      await enviarContato({
        nome: String(formData.get("name") || "").trim(),
        email: String(formData.get("email") || "").trim(),
        telefone: String(formData.get("phone") || "").trim(),
        mensagem: String(formData.get("message") || "").trim(),
      });
      form.reset();
      toast.success("Mensagem enviada", {
        description: "Nossa equipe vai retornar seu contato em breve.",
      });
    } catch {
      toast.error("Falha ao enviar", {
        description: "Não foi possível registrar seu contato agora. Tente novamente.",
      });
    } finally {
      setSendingContact(false);
    }
  };

  const handleNewsletterSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const form = event.currentTarget;
    const formData = new FormData(form);

    try {
      setSendingNewsletter(true);
      await cadastrarNewsletter({
        nome: String(formData.get("newsletterName") || "").trim(),
        email: String(formData.get("newsletterEmail") || "").trim(),
      });
      form.reset();
      toast.success("Cadastro concluído", {
        description: "Você entrou para a newsletter da GranKasa.",
      });
    } catch {
      toast.error("Falha no cadastro", {
        description: "Não foi possível salvar seu e-mail agora. Tente novamente.",
      });
    } finally {
      setSendingNewsletter(false);
    }
  };

  return (
    <MarketingPageShell eyebrow="Atendimento" title="Fale Conosco" mainClassName="flex-1 border-y border-black/10">
      <section className="mx-auto max-w-6xl px-4 py-12 md:py-14">
        <div className="grid grid-cols-1 gap-10 lg:grid-cols-[2fr_1fr]">
          <form onSubmit={handleContactSubmit} className={contactCardClass}>
            <div className="mb-6">
              <h3 className="font-display text-3xl text-slate-900">Fale Conosco</h3>
              <p className="section-copy-muted mt-2">Entre em contato pelo formulário abaixo.</p>
            </div>

            <div className="space-y-4">
              <div className={fieldShellClass}>
                <Label htmlFor="contact-name" className="text-slate-700">
                  Nome
                </Label>
                <Input id="contact-name" name="name" required placeholder="Nome" autoComplete="name" className={inputClass} />
              </div>
              <div className={fieldShellClass}>
                <Label htmlFor="contact-email" className="text-slate-700">
                  E-mail
                </Label>
                <Input
                  id="contact-email"
                  type="email"
                  name="email"
                  required
                  placeholder="E-mail"
                  autoComplete="email"
                  className={inputClass}
                />
              </div>
              <div className={fieldShellClass}>
                <Label htmlFor="contact-phone" className="text-slate-700">
                  Telefone
                </Label>
                <Input
                  id="contact-phone"
                  type="tel"
                  name="phone"
                  required
                  placeholder="Telefone"
                  autoComplete="tel"
                  className={inputClass}
                />
              </div>
              <div className={fieldShellClass}>
                <Label htmlFor="contact-message" className="text-slate-700">
                  Mensagem
                </Label>
                <Textarea
                  id="contact-message"
                  name="message"
                  required
                  placeholder="Mensagem"
                  className="min-h-[116px] resize-y border-white bg-white focus-visible:ring-amber-500"
                />
              </div>
            </div>

            <Button type="submit" disabled={sendingContact} className={buttonClass}>
              <Send className="h-4 w-4" />
              {sendingContact ? "Enviando..." : "Enviar"}
            </Button>
          </form>

          <form onSubmit={handleNewsletterSubmit} className={newsletterCardClass}>
            <div className="mb-6">
              <h3 className="font-display text-2xl">Newsletter</h3>
              <p className="section-copy-dark mt-2">Receba oportunidades de compra, venda e locação no seu e-mail.</p>
            </div>

            <div className="space-y-4">
              <div className={fieldShellClass}>
                <Label htmlFor="newsletter-name" className="text-slate-200">
                  Nome
                </Label>
                <Input
                  id="newsletter-name"
                  name="newsletterName"
                  required
                  placeholder="Nome"
                  autoComplete="name"
                  className={darkInputClass}
                />
              </div>
              <div className={fieldShellClass}>
                <Label htmlFor="newsletter-email" className="text-slate-200">
                  E-mail
                </Label>
                <Input
                  id="newsletter-email"
                  type="email"
                  name="newsletterEmail"
                  required
                  placeholder="E-mail"
                  autoComplete="email"
                  className={darkInputClass}
                />
              </div>
            </div>

            <Button type="submit" disabled={sendingNewsletter} className={buttonClass}>
              <Mail className="h-4 w-4" />
              {sendingNewsletter ? "Cadastrando..." : "Cadastrar"}
            </Button>
          </form>
        </div>
      </section>
    </MarketingPageShell>
  );
};

export default FaleConosco;
