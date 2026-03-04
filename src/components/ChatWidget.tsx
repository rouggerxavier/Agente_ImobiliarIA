import { MessageCircle, X, Send, Loader2 } from "lucide-react";
import { useState, useRef, useEffect } from "react";

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || "";
const BACKEND_API_KEY = import.meta.env.VITE_BACKEND_API_KEY as string | undefined;

interface Message {
  role: "user" | "agent";
  text: string;
}

const ChatWidget = () => {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    { role: "agent", text: "Olá! 👋 Sou o assistente virtual da GranKasa. Como posso ajudar você hoje?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    setInput("");
    setMessages((prev) => [...prev, { role: "user", text }]);
    setLoading(true);

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (BACKEND_API_KEY) {
        headers["X-API-Key"] = BACKEND_API_KEY;
      }

      const res = await fetch(`${BACKEND_URL}/webhook`, {
        method: "POST",
        headers,
        body: JSON.stringify({ session_id: sessionId, message: text }),
      });
      const data = await res.json();
      const reply = data.reply || data.response || data.message || "Sem resposta.";
      setMessages((prev) => [...prev, { role: "agent", text: reply }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "agent", text: "Desculpe, não consegui me conectar ao servidor. Tente novamente." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="fixed bottom-6 right-6 z-50">
      {open && (
        <div className="mb-4 w-80 sm:w-96 bg-card rounded-2xl shadow-chat border border-border overflow-hidden animate-fade-in-up">
          {/* Header */}
          <div className="bg-primary px-5 py-4 flex items-center justify-between">
            <div>
              <p className="font-display text-sm font-semibold text-primary-foreground">Assistente GranKasa</p>
              <p className="font-body text-xs text-primary-foreground/60">Powered by IA • Online</p>
            </div>
            <button onClick={() => setOpen(false)} className="text-primary-foreground/60 hover:text-primary-foreground transition-colors">
              <X className="h-5 w-5" />
            </button>
          </div>

          {/* Messages */}
          <div className="h-72 p-4 overflow-y-auto space-y-3">
            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`rounded-xl px-4 py-2.5 max-w-[80%] font-body text-sm ${
                    msg.role === "user"
                      ? "bg-accent text-accent-foreground rounded-br-sm"
                      : "bg-secondary text-foreground rounded-tl-sm"
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-secondary rounded-xl rounded-tl-sm px-4 py-2.5">
                  <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Input */}
          <div className="border-t border-border px-3 py-3 flex items-center gap-2">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Digite sua mensagem..."
              className="flex-1 bg-muted rounded-full px-4 py-2 font-body text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-accent/30"
              disabled={loading}
            />
            <button
              onClick={sendMessage}
              disabled={loading || !input.trim()}
              className="bg-accent text-accent-foreground rounded-full p-2 hover:opacity-90 transition-opacity disabled:opacity-50"
            >
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
