import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Index from "./pages/Index";
import Sobre from "./pages/Sobre";
import FaleConosco from "./pages/FaleConosco";
import Locacao from "./pages/Locacao";
import Venda from "./pages/Venda";
import ImovelDetalhe from "./pages/ImovelDetalhe";
import Busca from "./pages/Busca";
import NotFound from "./pages/NotFound";
import ChatWidget from "./components/ChatWidget";

const queryClient = new QueryClient();

const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Index />} />
          <Route path="/sobre" element={<Sobre />} />
          <Route path="/fale-conosco" element={<FaleConosco />} />
          <Route path="/locacao" element={<Locacao />} />
          <Route path="/venda" element={<Venda />} />
          <Route path="/imovel/:codigo" element={<ImovelDetalhe />} />
          <Route path="/busca" element={<Busca />} />
          {/* ADD ALL CUSTOM ROUTES ABOVE THE CATCH-ALL "*" ROUTE */}
          <Route path="*" element={<NotFound />} />
        </Routes>
        <ChatWidget />
      </BrowserRouter>
    </TooltipProvider>
  </QueryClientProvider>
);

export default App;
