import { Link } from "react-router-dom";
import { MapPin, Phone, Mail } from "lucide-react";

const footerLinks = [
  { label: "Início", to: "/#inicio" },
  { label: "Sobre", to: "/sobre" },
  { label: "Locação", to: "/locacao" },
  { label: "Vendas", to: "/vendas" },
  { label: "Fale Conosco", to: "/fale-conosco" },
];

const Footer = () => (
  <footer id="contato" className="bg-slate-950 text-slate-50 w-full">
    <div className="grid grid-cols-1 md:grid-cols-4 gap-12 px-8 md:px-16 py-20 w-full max-w-screen-2xl mx-auto">
      {/* Brand */}
      <div className="md:col-span-1">
        <div className="mb-8">
          <img src="/logo-grankasa.png" alt="GranKasa" className="h-14 w-auto" />
        </div>
        <p className="text-slate-400 leading-relaxed mb-8 text-sm">
          A principal referência em curadoria imobiliária de alto padrão em Copacabana e no Rio de Janeiro.
        </p>
        <div className="flex gap-4">
          <a href="https://www.facebook.com/grankasa" target="_blank" rel="noreferrer"
            className="w-10 h-10 rounded-full border border-slate-800 flex items-center justify-center text-slate-400 hover:border-amber-200 hover:text-amber-200 transition-all"
            aria-label="Facebook da GranKasa">
            <span className="text-xs font-bold">Fb</span>
          </a>
          <a href="https://www.youtube.com/user/grankasa" target="_blank" rel="noreferrer"
            className="w-10 h-10 rounded-full border border-slate-800 flex items-center justify-center text-slate-400 hover:border-amber-200 hover:text-amber-200 transition-all"
            aria-label="YouTube da GranKasa">
            <span className="text-xs font-bold">Yt</span>
          </a>
          <a href="https://docsuite.com.br/login/granka" target="_blank" rel="noreferrer"
            className="w-10 h-10 rounded-full border border-slate-800 flex items-center justify-center text-slate-400 hover:border-amber-200 hover:text-amber-200 transition-all"
            aria-label="Painel do Cliente">
            <span className="text-xs font-bold">DC</span>
          </a>
        </div>
      </div>

      {/* Quick Links */}
      <div>
        <h4 className="text-white text-xs font-bold uppercase tracking-[0.2em] mb-8">Links Rápidos</h4>
        <ul className="space-y-4">
          {footerLinks.map((link) => (
            <li key={link.label}>
              <Link to={link.to} className="text-slate-400 hover:text-white transition-colors text-sm">
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
      </div>

      {/* Contact */}
      <div>
        <h4 className="text-white text-xs font-bold uppercase tracking-[0.2em] mb-8">Contato</h4>
        <ul className="space-y-4 text-sm text-slate-400">
          <li className="flex items-start gap-3">
            <MapPin className="text-amber-200 h-4 w-4 mt-0.5 shrink-0" />
            <span>Av. Nossa Sra. de Copacabana, 749<br />Sl 501 — Copacabana, RJ</span>
          </li>
          <li className="flex items-center gap-3">
            <Phone className="text-amber-200 h-4 w-4 shrink-0" />
            <a href="tel:+552125499000" className="hover:text-white transition-colors">(21) 2549-9000</a>
          </li>
          <li className="flex items-center gap-3">
            <Mail className="text-amber-200 h-4 w-4 shrink-0" />
            <a href="mailto:grankasa@grankasa.com.br" className="hover:text-white transition-colors">grankasa@grankasa.com.br</a>
          </li>
        </ul>
      </div>

      {/* Newsletter / Client area */}
      <div>
        <h4 className="text-white text-xs font-bold uppercase tracking-[0.2em] mb-8">Painel do Cliente</h4>
        <p className="text-slate-400 text-sm mb-6">Acesse documentos, contratos e acompanhe seu processo de locação ou compra.</p>
        <a href="https://docsuite.com.br/login/granka" target="_blank" rel="noreferrer"
          className="inline-flex items-center justify-center w-full bg-amber-200 text-black py-3 px-6 rounded font-bold text-xs uppercase tracking-widest hover:bg-amber-100 transition-colors">
          Acessar Painel
        </a>
      </div>
    </div>

    {/* Bottom bar */}
    <div className="px-8 md:px-16 py-6 border-t border-slate-900 flex flex-col md:flex-row justify-between items-center gap-4 max-w-screen-2xl mx-auto">
      <p className="text-slate-500 text-xs uppercase tracking-widest">
        2017 © GranKasa. Todos os direitos reservados. Produzido por SV Consultoria e Sistemas.
      </p>
      <div className="flex gap-8">
        {["Rio de Janeiro", "Copacabana", "Ipanema", "Leblon"].map((city) => (
          <span key={city} className="text-[10px] uppercase tracking-widest text-slate-600 font-bold">{city}</span>
        ))}
      </div>
    </div>
  </footer>
);

export default Footer;
