import { Building2, Menu, X } from "lucide-react";
import { useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";

type NavItem = {
  label: string;
  to?: string;
  href?: string;
  external?: boolean;
};

const navItems: NavItem[] = [
  { label: "Início", to: "/#inicio" },
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
    return location.pathname === to;
  };

  useEffect(() => {
    if (!open) return;

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [open]);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="container mx-auto flex items-center justify-between h-16 px-4">
        <Link to="/" className="flex items-center gap-2">
          <Building2 className="h-7 w-7 text-accent" />
          <span className="font-display text-xl font-semibold text-foreground">
            Gran<span className="text-accent">Kasa</span>
          </span>
        </Link>

        <div className="hidden items-center gap-8 font-body text-sm font-medium md:flex">
          {navItems.map((item) =>
            item.external ? (
              <a key={item.label} href={item.href} target="_blank" rel="noreferrer" className="nav-link">
                {item.label}
              </a>
            ) : (
              <Link
                key={item.label}
                to={item.to || "/"}
                className={`nav-link ${isActive(item.to) ? "nav-link-active" : ""}`}
                aria-current={isActive(item.to) ? "page" : undefined}
              >
                {item.label}
              </Link>
            ),
          )}
        </div>

        <button
          type="button"
          className="md:hidden text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 focus-visible:ring-offset-background"
          onClick={() => setOpen(!open)}
          aria-label={open ? "Fechar menu principal" : "Abrir menu principal"}
          aria-expanded={open}
          aria-controls={mobileMenuId}
        >
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {open && (
        <div
          id={mobileMenuId}
          className="md:hidden bg-background border-b border-border px-4 pb-4 font-body text-sm font-medium space-y-3"
        >
          {navItems.map((item) =>
            item.external ? (
              <a
                key={item.label}
                href={item.href}
                target="_blank"
                rel="noreferrer"
                className="nav-link-mobile"
                onClick={() => setOpen(false)}
              >
                {item.label}
              </a>
            ) : (
              <Link
                key={item.label}
                to={item.to || "/"}
                className={`nav-link-mobile ${isActive(item.to) ? "nav-link-active" : ""}`}
                onClick={() => setOpen(false)}
                aria-current={isActive(item.to) ? "page" : undefined}
              >
                {item.label}
              </Link>
            ),
          )}
        </div>
      )}
    </nav>
  );
};

export default Navbar;
