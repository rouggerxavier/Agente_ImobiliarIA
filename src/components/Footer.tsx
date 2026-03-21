import { Building2, Mail, MapPin, Phone } from "lucide-react";
import { Link } from "react-router-dom";

const footerLinks = [
  { label: "Início", to: "/#inicio" },
  { label: "Sobre", to: "/sobre" },
  { label: "Locação", to: "/locacao" },
  { label: "Vendas", to: "/vendas" },
  { label: "Fale Conosco", to: "/fale-conosco" },
];

const footerContacts = [
  { icon: Phone, label: "(21) 2549-9000", href: "tel:+552125499000" },
  { icon: Mail, label: "grankasa@grankasa.com.br", href: "mailto:grankasa@grankasa.com.br" },
  {
    icon: MapPin,
    label: "Copacabana - Rio de Janeiro",
    href: "https://www.google.com/maps/search/?api=1&query=Av.%20Nossa%20Sra.%20de%20Copacabana,%20749%20-%20Sl%20501%20-%20Copacabana,%20Rio%20de%20Janeiro%20-%20RJ,%2022050-002,%20Brasil",
    external: true,
  },
];

const socialLinks = [
  { label: "Facebook", href: "https://www.facebook.com/grankasa" },
  { label: "YouTube", href: "https://www.youtube.com/user/grankasa" },
  { label: "Painel do Cliente", href: "https://docsuite.com.br/login/granka" },
];

const Footer = () => {
  return (
    <footer id="contato" className="bg-primary py-16 text-primary-foreground">
      <div className="container mx-auto px-4">
        <div className="grid gap-10 md:grid-cols-3">
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <Building2 className="h-6 w-6 text-accent" />
              <span className="font-display text-xl font-semibold">
                Gran<span className="text-accent">Kasa</span>
              </span>
            </div>
            <p className="footer-copy">
              Atuando no mercado imobiliário do Rio de Janeiro, com foco em locação, vendas e atendimento
              personalizado.
            </p>
          </div>

          <div className="space-y-4">
            <h4 className="footer-heading">Contato</h4>
            <div className="space-y-3">
              {footerContacts.map(({ icon: Icon, label, href, external }) => (
                <a
                  key={label}
                  href={href}
                  target={external ? "_blank" : undefined}
                  rel={external ? "noreferrer" : undefined}
                  className="footer-link-inline"
                >
                  <Icon className="h-4 w-4 text-accent" />
                  <span>{label}</span>
                </a>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <h4 className="footer-heading">Links</h4>
            <div className="space-y-2">
              {footerLinks.map((link) => (
                <Link key={link.label} to={link.to} className="footer-link">
                  {link.label}
                </Link>
              ))}
            </div>
            <div className="pt-4 space-y-2">
              {socialLinks.map((link) => (
                <a key={link.label} href={link.href} target="_blank" rel="noreferrer" className="footer-link">
                  {link.label}
                </a>
              ))}
            </div>
          </div>
        </div>

        <div className="mt-10 border-t border-primary-foreground/10 pt-6 text-center font-body text-xs text-primary-foreground/50">
          2017 © - Todos os direitos reservados a GranKasa. Produzido por SV Consultoria e Sistemas.
        </div>
      </div>
    </footer>
  );
};

export default Footer;
