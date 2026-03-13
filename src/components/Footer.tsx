import { Building2, Mail, MapPin, Phone } from "lucide-react";
import { Link } from "react-router-dom";

const Footer = () => {
  return (
    <footer id="contato" className="bg-primary text-primary-foreground py-16">
      <div className="container mx-auto px-4">
        <div className="grid md:grid-cols-3 gap-10">
          <div>
            <div className="flex items-center gap-2 mb-4">
              <Building2 className="h-6 w-6 text-accent" />
              <span className="font-display text-xl font-semibold">
                Gran<span className="text-accent">Kasa</span>
              </span>
            </div>
            <p className="font-body text-primary-foreground/70 text-sm leading-relaxed">
              Transformando sonhos em enderecos desde 2010. Atendimento personalizado e os melhores
              imoveis do mercado.
            </p>
          </div>

          <div>
            <h4 className="font-display text-lg font-semibold mb-4">Contato</h4>
            <div className="space-y-3 font-body text-sm text-primary-foreground/70">
              <p className="flex items-center gap-2"><Phone className="h-4 w-4 text-accent" /> (21) 2549-9000</p>
              <p className="flex items-center gap-2"><Mail className="h-4 w-4 text-accent" /> grankasa@grankasa.com.br</p>
              <p className="flex items-center gap-2"><MapPin className="h-4 w-4 text-accent" /> Copacabana - Rio de Janeiro</p>
            </div>
          </div>

          <div>
            <h4 className="font-display text-lg font-semibold mb-4">Links</h4>
            <div className="space-y-2 font-body text-sm text-primary-foreground/70">
              <a href="/#inicio" className="block hover:text-accent transition-colors">Inicio</a>
              <Link to="/sobre" className="block hover:text-accent transition-colors">Sobre</Link>
              <Link to="/locacao" className="block hover:text-accent transition-colors">Locacao</Link>
              <Link to="/venda" className="block hover:text-accent transition-colors">Venda</Link>
              <Link to="/fale-conosco" className="block hover:text-accent transition-colors">Fale Conosco</Link>
            </div>
          </div>
        </div>

        <div className="border-t border-primary-foreground/10 mt-10 pt-6 text-center font-body text-xs text-primary-foreground/50">
          (c) 2026 GranKasa Imoveis. Todos os direitos reservados.
        </div>
      </div>
    </footer>
  );
};

export default Footer;
