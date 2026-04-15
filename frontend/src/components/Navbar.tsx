import { useState, useEffect } from "react";
import { Link, useLocation } from "react-router-dom";
import { Menu, X } from "lucide-react";

type NavItem = {
  label: string;
  to?: string;
  href?: string;
  external?: boolean;
};

const navItems: NavItem[] = [
  { label: "Imóveis", to: "/#inicio" },
  { label: "Locação", to: "/locacao" },
  { label: "Vendas", to: "/vendas" },
  { label: "Sobre", to: "/sobre" },
  { label: "Fale Conosco", to: "/fale-conosco" },
  {
    label: "Painel do Cliente",
    href: "https://docsuite.com.br/login/granka",
    external: true,
  },
];

const Navbar = () => {
  const [open, setOpen] = useState(false);
  const location = useLocation();
  const mobileMenuId = "mobile-nav-menu";

  const isActive = (to?: string) => {
    if (!to) return false;
    if (to === "/#inicio") return location.pathname === "/" || location.pathname === "/inicio";
    if (to === "/sobre") return location.pathname === "/sobre" || location.pathname === "/a-empresa";
    if (to === "/vendas") return location.pathname === "/vendas" || location.pathname === "/venda";
    return location.pathname === to;
  };

  useEffect(() => {
    if (!open) return;
    const handleEscape = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [open]);

  return (
    <nav className="fixed top-0 w-full z-50 bg-slate-50/70 backdrop-blur-xl transition-all border-b border-outline-variant/20">
      <div className="flex justify-between items-center pl-0 pr-8 md:pl-0 md:pr-16 py-1 md:py-2 w-full max-w-screen-2xl mx-auto">
        {/* Logo */}
        <Link to="/" className="-ml-4 md:-ml-12 flex items-center">
          <img src="/logo-grankasa.png" alt="GranKasa" className="h-24 w-auto" />
        </Link>

        {/* Desktop nav */}
        <div className="hidden md:flex items-center gap-12">
          {navItems.slice(0, 5).map((item) => {
            const active = isActive(item.to);
            return item.external ? (
              <a key={item.label} href={item.href} target="_blank" rel="noreferrer"
                className="text-on-surface-variant hover:text-tertiary-fixed-dim transition-colors uppercase tracking-widest text-sm font-bold">
                {item.label}
              </a>
            ) : (
              <Link key={item.label} to={item.to || "/"}
                className={`uppercase tracking-widest text-sm font-bold transition-colors pb-1 ${
                  active
                    ? "text-tertiary-fixed-dim border-b-2 border-tertiary-fixed-dim"
                    : "text-on-surface-variant hover:text-tertiary-fixed-dim"
                }`}
                aria-current={active ? "page" : undefined}>
                {item.label}
              </Link>
            );
          })}
        </div>

        {/* Right actions */}
        <div className="flex items-center gap-8">
          <a href="tel:+552125499000"
            className="hidden lg:block text-on-surface-variant hover:text-tertiary-fixed-dim transition-all font-medium text-base">
            (21) 2549-9000
          </a>
          <a href="https://docsuite.com.br/login/granka" target="_blank" rel="noreferrer"
            className="bg-primary-dark text-white px-4 py-2.5 md:px-7 md:py-3.5 rounded-lg md:rounded-xl text-[11px] md:text-sm uppercase tracking-[0.14em] md:tracking-widest font-bold leading-none md:leading-normal hover:opacity-90 active:scale-95 transition-all">
            Painel do Cliente
          </a>
          <button type="button"
            className="md:hidden text-on-surface focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-tertiary-fixed-dim"
            onClick={() => setOpen(!open)}
            aria-label={open ? "Fechar menu" : "Abrir menu"}
            aria-expanded={open}
            aria-controls={mobileMenuId}>
            {open ? <X className="h-7 w-7" /> : <Menu className="h-7 w-7" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div id={mobileMenuId}
          className="md:hidden bg-slate-50/95 backdrop-blur-xl border-t border-outline-variant/20 px-8 pb-6 pt-4 space-y-4">
          {navItems.map((item) => {
            const active = isActive(item.to);
            return item.external ? (
              <a key={item.label} href={item.href} target="_blank" rel="noreferrer"
                onClick={() => setOpen(false)}
                className="flex min-h-12 items-center uppercase tracking-widest text-sm font-bold text-on-surface-variant hover:text-tertiary-fixed-dim transition-colors">
                {item.label}
              </a>
            ) : (
              <Link key={item.label} to={item.to || "/"}
                onClick={() => setOpen(false)}
                aria-current={active ? "page" : undefined}
                className={`flex min-h-12 items-center uppercase tracking-widest text-sm font-bold transition-colors ${
                  active ? "text-tertiary-fixed-dim" : "text-on-surface-variant hover:text-tertiary-fixed-dim"
                }`}>
                {item.label}
              </Link>
            );
          })}
        </div>
      )}
    </nav>
  );
};

export default Navbar;
