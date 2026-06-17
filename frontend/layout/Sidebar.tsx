import { useState, useEffect } from 'react';
import { MessageSquare, Settings, Plus, Trash2 } from 'lucide-react';
import socket from '@/lib/socket';

interface SidebarProps {
  isOpen: boolean;
  onOpenSettings: () => void;
  activeChatId: string | null;
  onSelectChat: (id: string | null) => void;
}

interface Chat {
  id: string;
  baslik: string;
}

export default function Sidebar({ isOpen, onOpenSettings, activeChatId, onSelectChat }: SidebarProps) {
  const [chats, setChats] = useState<Chat[]>([]);

  useEffect(() => {
    socket.emit('sohbetleri_getir');

    socket.on('sohbetler_liste', (data) => {
      setChats(data.sohbetler || []);
    });

    socket.on('sohbet_olusturuldu', () => {
      socket.emit('sohbetleri_getir');
    });

    socket.on('sohbet_silindi', (data) => {
      setChats(prev => prev.filter(c => c.id !== data.sohbet_id));
      if (activeChatId === data.sohbet_id) {
        onSelectChat(null);
      }
    });

    return () => {
      socket.off('sohbetler_liste');
      socket.off('sohbet_olusturuldu');
      socket.off('sohbet_silindi');
    };
  }, [activeChatId]);

  const handleDelete = (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    socket.emit('sohbeti_sil', { sohbet_id: id });
  };

  return (
    <aside
      className={`fixed md:relative z-20 flex flex-col h-screen bg-[#1e1e1e] text-slate-300 border-r border-slate-800 transition-all duration-300 ease-in-out ${
        isOpen ? 'w-64 translate-x-0' : 'w-0 -translate-x-full md:w-0'
      } overflow-hidden`}
    >
      <div className="p-3 mt-4">
        <button 
          onClick={() => onSelectChat(null)}
          className="w-full flex items-center gap-3 bg-[#2a2a2a] hover:bg-[#333333] text-white py-3 px-4 rounded-xl transition-colors"
        >
          <Plus size={20} className="shrink-0" />
          <span className="text-sm font-medium whitespace-nowrap">Yeni Sohbet</span>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-2 mt-2 space-y-1">
        <p className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider mb-2 px-2 whitespace-nowrap">
          Geçmiş Sohbetler
        </p>
        
        {chats.map(chat => (
          <div key={chat.id} className="group relative flex items-center">
            <button 
              onClick={() => onSelectChat(chat.id)}
              className={`flex-1 flex items-center gap-3 p-2.5 rounded-lg text-left transition-colors ${activeChatId === chat.id ? 'bg-[#333333] text-white' : 'hover:bg-[#2a2a2a] text-slate-300 hover:text-white'}`}
            >
              <MessageSquare size={16} className="shrink-0" />
              <span className="text-sm truncate w-36">{chat.baslik}</span>
            </button>
            <button 
              onClick={(e) => handleDelete(e, chat.id)}
              className="absolute right-2 opacity-0 group-hover:opacity-100 p-1.5 text-slate-500 hover:text-red-400 transition-all"
            >
              <Trash2 size={16} />
            </button>
          </div>
        ))}
      </div>

      <div className="p-4 flex justify-center mb-2">
        <button 
            onClick={onOpenSettings} 
            className="p-3 hover:bg-[#2a2a2a] rounded-xl text-slate-400 hover:text-white transition-colors" 
            title="Ayarlar / Dashboard"
        >
            <Settings size={22} />
        </button>
      </div>
    </aside>
  );
}
