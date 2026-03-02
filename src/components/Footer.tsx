import { Building2, Mail, Phone, MapPin } from "lucide-react";

const Footer = () => {
  return (
    <footer id="contato" className="bg-primary text-primary-foreground py-16">
      <div className="container mx-auto px-4">
        <div className="grid md:grid-cols-3 gap-10">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Building2 className="h-6 w-6 text-accent" />
              <span className="font-display text-xl font-semibold">
                Nova<span className="text-accent">Lar</span>
              </span>
            </div>
            <p className="font-body text-primary-foreground/70 text-sm leading-relaxed">
              Transformando sonhos em endereços desde 2010. Atendimento personalizado e os melhores imóveis do mercado.
            </p>
          </div>
          <div>
            <h4 className="font-display text-lg font-semibold mb-4">Contato</h4>
            <div className="space-y-3 font-body text-sm text-primary-foreground/70">
              <p className="flex items-center gap-2"><Phone className="h-4 w-4 text-accent" /> (11) 99999-0000</p>
              <p className="flex items-center gap-2"><Mail className="h-4 w-4 text-accent" /> contato@novalar.com.br</p>
              <p className="flex items-center gap-2"><MapPin className="h-4 w-4 text-accent" /> Av. Paulista, 1000 — São Paulo</p>
            </div>
          </div>
          <div>
            <h4 className="font-display text-lg font-semibold mb-4">Links</h4>
            <div className="space-y-2 font-body text-sm text-primary-foreground/70">
              <a href="#inicio" className="block hover:text-accent transition-colors">Início</a>
              <a href="#imoveis" className="block hover:text-accent transition-colors">Imóveis</a>
              <a href="#sobre" className="block hover:text-accent transition-colors">Sobre</a>
            </div>
          </div>
        </div>
        <div className="border-t border-primary-foreground/10 mt-10 pt-6 text-center font-body text-xs text-primary-foreground/50">
          © 2025 NovaLar Imóveis. Todos os direitos reservados.
        </div>
      </div>
    </footer>
  );
};

export default Footer;
