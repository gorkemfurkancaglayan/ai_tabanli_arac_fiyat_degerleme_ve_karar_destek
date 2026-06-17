"use client";

import { useState, useEffect, useRef } from "react";
import { Search, Menu, Bot, Send, Loader2, Plus, ChevronDown, ChevronUp } from "lucide-react";
import Sidebar from "@/components/layout/Sidebar";
import socket from "@/lib/socket";
import ValuationCard from "@/components/chat/ValuationCard";
import VehicleInfoCard from "@/components/chat/VehicleInfoCard";
import CarDamageMap from "@/components/chat/CarDamageMap";
import AdminDashboard from "@/components/layout/AdminDashboard";

interface Message {
  id: string;
  sender: 'user' | 'bot';
  type: 'text' | 'degerleme';
  text: string;
  metrics?: {
    tahmin_edilen_fiyat: number;
    min_fiyat: number;
    max_fiyat: number;
  };
}


function CollapsibleDamageMap({ onComplete }: { onComplete: (data: string) => void }) {
  const [isOpen, setIsOpen] = useState(false);
  return (
    <div className="flex flex-col items-start mt-2 animate-in fade-in slide-in-from-top-4 duration-500 w-full">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-xs font-semibold text-slate-500 hover:text-indigo-600 transition-colors bg-white px-4 py-2 rounded-xl shadow-sm border border-slate-100 mt-2"
      >
        Ekspertiz & Hasar Düzenle {isOpen ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
      </button>
      
      {isOpen && (
        <div className="w-full mt-4 animate-in fade-in slide-in-from-top-2 duration-300">
          <CarDamageMap onComplete={(data) => {
            setIsOpen(false);
            onComplete(data);
          }} />
        </div>
      )}
    </div>
  );
}

export default function Home() {
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [isChatStarted, setIsChatStarted] = useState(false);
  const [inputValue, setInputValue] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isDashboardOpen, setIsDashboardOpen] = useState(false);
  
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const pendingMessageRef = useRef<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  useEffect(() => {
    socket.connect();

    socket.on('bot_mesaj', (data) => {
      setIsTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          sender: 'bot',
          type: data.tip || 'text',
          text: data.metin_cevap || data.mesaj || "",
          metrics: data.metrikler,
        }
      ]);
    });

    socket.on('eski_mesajlar', (data) => {
       const formatted = data.mesajlar.map((m: any) => ({
          id: m.id,
          sender: m.gonderen,
          type: m.tip,
          text: m.metin,
          metrics: m.metrikler
       }));
       setMessages(formatted);
       setIsChatStarted(formatted.length > 0);
       setIsTyping(false);
    });

    socket.on('sohbet_olusturuldu', (data) => {
       setActiveChatId(data.sohbet.id);
    });

    return () => {
      socket.off('bot_mesaj');
      socket.off('eski_mesajlar');
      socket.off('sohbet_olusturuldu');
      // socket.disconnect();  // Do not disconnect completely, just clean listeners
    };
  }, []);

  useEffect(() => {
     if (activeChatId) {
         if (pendingMessageRef.current) {
             // Yeni sohbet oluşturuldu, eski mesajları getirme, kullanıcının yazdığı silinmesin.
             socket.emit('kullanici_mesaj', { mesaj: pendingMessageRef.current, sohbet_id: activeChatId });
             pendingMessageRef.current = null;
             setIsChatStarted(true);
         } else {
             // Sidebar'dan eski bir sohbete tıklandı
             setMessages([]);
             setIsTyping(true);
             socket.emit('mesajlari_getir', { sohbet_id: activeChatId });
             setIsChatStarted(true);
         }
     } else {
         setIsChatStarted(false);
         setMessages([]);
     }
  }, [activeChatId]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputValue.trim() === "") return;
    
    setIsChatStarted(true);
    setMessages(prev => [...prev, { 
      id: Date.now().toString(), 
      sender: 'user', 
      type: 'text', 
      text: inputValue 
    }]);
    setIsTyping(true);

    if (!activeChatId) {
       // Yeni sohbet oluştur ve bekle
       pendingMessageRef.current = inputValue;
       socket.emit('sohbet_olustur', { baslik: inputValue.slice(0, 30) + "..." });
    } else {
       socket.emit('kullanici_mesaj', { mesaj: inputValue, sohbet_id: activeChatId });
    }
    
    setInputValue("");
  };

  const handleDamageReport = (damageData: string) => {
    setMessages(prev => [...prev, { 
      id: Date.now().toString(), 
      sender: 'user', 
      type: 'text', 
      text: damageData 
    }]);
    setIsTyping(true);
    socket.emit('kullanici_mesaj', { mesaj: damageData, sohbet_id: activeChatId });
    scrollToBottom();
  };

  return (
    <div className="flex h-screen bg-white overflow-hidden w-full">
      <Sidebar 
        isOpen={isSidebarOpen} 
        onOpenSettings={() => setIsDashboardOpen(true)} 
        activeChatId={activeChatId}
        onSelectChat={(id) => setActiveChatId(id)}
      />
      {isDashboardOpen && <AdminDashboard onClose={() => setIsDashboardOpen(false)} />}
      <main className="flex-1 flex flex-col h-screen relative transition-all duration-300">
        
        <div className="absolute top-0 left-0 p-4 z-10 flex items-center gap-2">
          <button onClick={() => setIsSidebarOpen(!isSidebarOpen)} className="p-2 rounded-xl text-slate-600 hover:bg-slate-100 transition-colors">
            <Menu size={24} />
          </button>
          {!isSidebarOpen && <span className="text-lg sm:text-xl font-semibold text-slate-700 tracking-tight truncate">AI Tabanlı Araç Fiyat Değerleme ve Karar Destek Asistanı</span>}
        </div>

        <div className="flex-1 flex flex-col items-center justify-center w-full overflow-hidden relative">
          
          {!isChatStarted ? (
            <div className="flex flex-col items-center justify-center p-6 text-center w-full max-w-3xl animate-in fade-in zoom-in duration-500">
              <h2 className="text-4xl sm:text-5xl font-bold text-slate-800 mb-8 pb-4 bg-clip-text text-transparent bg-gradient-to-r from-blue-600 to-violet-600">
                Nasıl yardımcı olabilirim?
              </h2>
              
              <form onSubmit={handleSearch} className="w-full relative shadow-[0_0_15px_rgba(0,0,0,0.05)] hover:shadow-[0_0_25px_rgba(0,0,0,0.08)] transition-shadow rounded-2xl bg-white border border-slate-200 p-2 flex items-center">
                <input 
                  type="text" 
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Örn: 2018 model 90 bin km dizel otomatik Passat..." 
                  className="flex-1 bg-transparent border-none outline-none text-slate-700 placeholder:text-slate-400 text-lg px-4"
                />
                <button type="submit" className="bg-slate-100 hover:bg-slate-200 p-3 rounded-xl text-slate-700 transition-colors">
                  <Search size={22} />
                </button>
              </form>
            </div>
          ) : (
            <div className="w-full h-full flex flex-col relative">
              
              <div className="flex-1 w-full max-w-4xl mx-auto pt-20 pb-32 px-4 overflow-y-auto scroll-smooth">
                
                {messages.map((msg, index) => (
                  <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'} mb-8 animate-in slide-in-from-bottom-2 fade-in duration-300`}>
                    
                    {msg.sender === 'bot' && (
                      <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-600 to-violet-600 flex items-center justify-center shrink-0 mt-1 shadow-md mr-4">
                        <Bot size={18} className="text-white" />
                      </div>
                    )}
                    
                    <div className={`py-3 px-5 rounded-3xl max-w-[85%] text-base shadow-sm border ${
                      msg.sender === 'user' 
                        ? 'bg-slate-100 text-slate-800 rounded-tr-sm border-slate-200' 
                        : 'bg-white text-slate-800 rounded-tl-sm border-slate-100'
                    }`}>
                      <div className="leading-relaxed whitespace-pre-wrap">{msg.text}</div>
                      
                      {msg.type === 'degerleme' && msg.metrics && (
                        <div className="flex flex-col gap-3">
                          <div className="flex flex-col sm:flex-row items-stretch gap-4">
                            <ValuationCard metrics={msg.metrics} />
                            {msg.metrics.arac_bilgisi && (
                              <VehicleInfoCard arac_bilgisi={msg.metrics.arac_bilgisi} />
                            )}
                          </div>
                          
                          {index === messages.length - 1 && (
                            <CollapsibleDamageMap onComplete={handleDamageReport} />
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                ))}

                {isTyping && (
                  <div className="flex gap-4 mb-8">
                    <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center shrink-0 mt-1">
                      <Loader2 size={16} className="text-slate-500 animate-spin" />
                    </div>
                    <div className="bg-white py-3 px-5 rounded-3xl rounded-tl-sm border border-slate-100 text-slate-400 text-sm flex items-center">
                      Asistan piyasa verilerini analiz ediyor...
                    </div>
                  </div>
                )}
                
                <div ref={messagesEndRef} />
              </div>

              <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-white via-white to-transparent pt-10 pb-6 px-4 z-20">
                <form onSubmit={handleSearch} className="max-w-3xl mx-auto flex items-center bg-slate-50 border border-slate-200 rounded-2xl shadow-sm hover:shadow-md transition-shadow px-2 py-2 relative z-30">
                  <input 
                    type="text" 
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    placeholder="Aracın tramer kaydı veya boyalı parçası var mı?" 
                    className="flex-1 bg-transparent border-none outline-none text-slate-700 placeholder:text-slate-400 text-base px-4"
                  />
                  <button type="submit" className="bg-blue-600 hover:bg-blue-700 p-2.5 rounded-xl text-white transition-colors" disabled={isTyping}>
                    <Send size={20} />
                  </button>
                </form>
              </div>
              
            </div>
          )}

        </div>
      </main>
    </div>
  );
}
