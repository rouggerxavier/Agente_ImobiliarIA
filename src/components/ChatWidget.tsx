import { MessageCircle, X, Send } from "lucide-react";
import { useState } from "react";

const ChatWidget = () => {
  const [open, setOpen] = useState(false);

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {/* Chat window */}
      {open && (
        <div className="mb-4 w-80 sm:w-96 bg-card rounded-2xl shadow-chat border border-border overflow-hidden animate-fade-in-up">
          {/* Header */}
          <div className="bg-primary px-5 py-4 flex items-center justify-between">
            <div>
              <p className="font-display text-sm font-semibold text-primary-foreground">Assistente NovaLar</p>
              <p className="font-body text-xs text-primary-foreground/60">Powered by IA • Online</p>
            </div>
            <button onClick={() => setOpen(false)} className="text-primary-foreground/60 hover:text-primary-foreground transition-colors">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Messages area */}
          <div className="h-64 p-4 overflow-y-auto space-y-3">
            <div className="bg-secondary rounded-xl rounded-tl-sm px-4 py-2.5 max-w-[80%]">
              <p className="font-body text-sm text-foreground">
                Olá! 👋 Sou o assistente virtual da NovaLar. Como posso ajudar você hoje?
              </p>
            </div>
          </div>

          {/* Input */}
          <div className="border-t border-border px-3 py-3 flex items-center gap-2">
            <input
              type="text"
              placeholder="Digite sua mensagem..."
              className="flex-1 bg-muted rounded-full px-4 py-2 font-body text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent/30"
            />
            <button className="bg-accent text-accent-foreground rounded-full p-2 hover:opacity-90 transition-opacity">
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* FAB */}
      <button
        onClick={() => setOpen(!open)}
        className="bg-accent text-accent-foreground rounded-full p-4 shadow-chat hover:opacity-90 transition-opacity animate-pulse-glow"
        aria-label="Abrir chat com assistente virtual"
      >
        {open ? <X className="h-6 w-6" /> : <MessageCircle className="h-6 w-6" />}
      </button>
    </div>
  );
};

export default ChatWidget;
