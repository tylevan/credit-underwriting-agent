import { useRef, useEffect, useState } from "react";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Send, Bot, User as UserIcon } from "lucide-react";
import { ResultCard, AssessmentResult } from "./ResultCard";
import { format } from "date-fns";

export interface Message {
  id: string;
  role: "system" | "user";
  content?: string;
  cardData?: AssessmentResult;
  timestamp: Date;
}

interface ChatInterfaceProps {
  messages: Message[];
  onSendMessage?: (message: string) => void;
  isLoading?: boolean;
}

export function ChatInterface({ messages, onSendMessage, isLoading }: ChatInterfaceProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState("");

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || !onSendMessage || isLoading) return;
    onSendMessage(trimmed);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  return (
    <div className="flex flex-col h-full bg-slate-50/50">
      {/* Header */}
      <div className="bg-primary px-6 py-5 flex justify-between items-center shadow-lg z-10 border-b border-primary/10">
        <div className="flex items-center gap-4">
          <div className="bg-white/10 p-2.5 rounded-xl backdrop-blur-md border border-white/20 shadow-inner">
            <Bot className="text-white w-6 h-6" />
          </div>
          <div>
            <h2 className="text-white font-bold text-xl tracking-tight">FinSafe AI Assistant</h2>
            <div className="flex items-center gap-2">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
              </span>
              <span className="text-primary-foreground/90 text-[11px] font-semibold uppercase tracking-wider">Hệ thống sẵn sàng</span>
            </div>
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-2 bg-black/10 px-4 py-1.5 rounded-full border border-white/10 backdrop-blur-sm">
          <div className="w-1.5 h-1.5 rounded-full bg-green-400"></div>
          <span className="text-[10px] font-bold text-white uppercase tracking-widest">v2.4.0</span>
        </div>
      </div>

      {/* Messages Area */}
      <ScrollArea className="flex-1 px-4 md:px-10 py-8">
        <div className="space-y-10 max-w-4xl mx-auto">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex w-full gap-5 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"
                } animate-in fade-in slide-in-from-bottom-4 duration-500`}
            >
              <div className="flex-shrink-0 mt-1">
                <Avatar className={`w-11 h-11 shadow-md border-2 ${msg.role === "user" ? "border-white bg-slate-100" : "border-primary/10 bg-white"}`}>
                  <AvatarFallback className={msg.role === "user" ? "bg-white text-slate-600" : "bg-primary text-white"}>
                    {msg.role === "user" ? <UserIcon className="w-6 h-6" /> : <Bot className="w-6 h-6" />}
                  </AvatarFallback>
                </Avatar>
              </div>

              <div className={`flex flex-col gap-2 max-w-[85%] sm:max-w-[80%]`}>
                {msg.content && (
                  <div
                    className={`relative p-5 rounded-2xl shadow-sm text-[15px] leading-relaxed tracking-wide ${msg.role === "user"
                      ? "bg-primary text-white rounded-tr-none font-medium"
                      : "bg-white text-slate-800 border border-slate-100 rounded-tl-none"
                      }`}
                  >
                    <span dangerouslySetInnerHTML={{
                      __html: msg.content
                        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="underline font-semibold hover:opacity-80 transition-opacity">$1</a>')
                        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                        .replace(/\n/g, '<br/>')
                    }} />
                    {/* Message tail indicator */}
                    <div className={`absolute top-0 w-3 h-3 ${msg.role === "user"
                      ? "-right-1 bg-primary [clip-path:polygon(0_0,0%_100%,100%_0)]"
                      : "-left-1 bg-white border-l border-t border-slate-100 [clip-path:polygon(0_0,100%_100%,100%_0)]"
                      }`} />
                  </div>
                )}

                {msg.cardData && (
                  <div className="mt-4 transition-all hover:scale-[1.01] duration-300">
                    <ResultCard data={msg.cardData} />
                  </div>
                )}

                <span className={`text-[10px] font-bold text-slate-400 mt-1 uppercase tracking-tighter ${msg.role === "user" ? "text-right" : "text-left"
                  }`}>
                  {format(msg.timestamp, "HH:mm")} • {msg.role === "system" ? "AI ANALYTICS" : "AGENT"}
                </span>
              </div>
            </div>
          ))}
          <div ref={scrollRef} className="h-4" />
        </div>
      </ScrollArea>

      {/* Input Area */}
      <div className="p-6 bg-white border-t border-slate-100 shadow-[0_-4px_20px_-5px_rgba(0,0,0,0.05)]">
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3 relative group">
            <Input
              placeholder="Yêu cầu phân tích thêm hoặc hỏi về hồ sơ..."
              className="pr-14 h-14 bg-slate-50/50 border-slate-200 focus-visible:ring-primary/20 rounded-xl transition-all group-hover:bg-slate-50"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
            />
            <Button
              size="icon"
              className="absolute right-1.5 top-1.5 w-11 h-11 rounded-lg shadow-lg shadow-primary/20"
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
            >
              <Send className="w-5 h-5" />
            </Button>
          </div>
          <div className="flex justify-between items-center mt-3 px-1">
            <div className="flex gap-4">
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                Secure Session
              </span>
              <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest flex items-center gap-1">
                <span className="w-1 h-1 rounded-full bg-slate-300"></span>
                AES-256
              </span>
            </div>
            <div className="text-[10px] font-bold text-slate-300 uppercase tracking-widest">
              FinSafe AI Engine v2.4
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
