import { Building2, Menu, X } from "lucide-react";
import { useState } from "react";
import { Link } from "react-router-dom";

const Navbar = () => {
  const [open, setOpen] = useState(false);

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 bg-background/80 backdrop-blur-md border-b border-border">
      <div className="container mx-auto flex items-center justify-between h-16 px-4">
        <Link to="/" className="flex items-center gap-2">
          <Building2 className="h-7 w-7 text-accent" />
          <span className="font-display text-xl font-semibold text-foreground">
            Gran<span className="text-accent">Kasa</span>
          </span>
        </Link>

        <div className="hidden md:flex items-center gap-8 font-body text-sm font-medium">
          <a href="/#inicio" className="text-muted-foreground hover:text-foreground transition-colors">
            Inicio
          </a>
          <Link to="/locacao" className="text-muted-foreground hover:text-foreground transition-colors">
            Locacao
          </Link>
          <Link to="/venda" className="text-muted-foreground hover:text-foreground transition-colors">
            Venda
          </Link>
          <a href="/#sobre" className="text-muted-foreground hover:text-foreground transition-colors">
            Sobre
          </a>
          <Link to="/a-empresa" className="text-muted-foreground hover:text-foreground transition-colors">
            A Empresa
          </Link>
          <Link to="/fale-conosco" className="text-muted-foreground hover:text-foreground transition-colors">
            Fale Conosco
          </Link>
        </div>

        <button className="md:hidden text-foreground" onClick={() => setOpen(!open)}>
          {open ? <X className="h-6 w-6" /> : <Menu className="h-6 w-6" />}
        </button>
      </div>

      {open && (
        <div className="md:hidden bg-background border-b border-border px-4 pb-4 font-body text-sm font-medium space-y-3">
          <a href="/#inicio" className="block text-muted-foreground hover:text-foreground" onClick={() => setOpen(false)}>
            Inicio
          </a>
          <Link to="/locacao" className="block text-muted-foreground hover:text-foreground" onClick={() => setOpen(false)}>
            Locacao
          </Link>
          <Link to="/venda" className="block text-muted-foreground hover:text-foreground" onClick={() => setOpen(false)}>
            Venda
          </Link>
          <a href="/#sobre" className="block text-muted-foreground hover:text-foreground" onClick={() => setOpen(false)}>
            Sobre
          </a>
          <Link to="/a-empresa" className="block text-muted-foreground hover:text-foreground" onClick={() => setOpen(false)}>
            A Empresa
          </Link>
          <Link to="/fale-conosco" className="block text-muted-foreground hover:text-foreground" onClick={() => setOpen(false)}>
            Fale Conosco
          </Link>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
