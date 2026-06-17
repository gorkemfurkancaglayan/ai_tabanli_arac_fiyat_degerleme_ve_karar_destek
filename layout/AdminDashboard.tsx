import React, { useState, useEffect, useRef } from 'react';
import { X, Terminal, Play, Database, Settings, Activity, ServerCog, UserCog, BookOpen, Edit2, Plus, Trash2, Save } from 'lucide-react';
import socket from '@/lib/socket';

interface AdminDashboardProps {
  onClose: () => void;
}

interface BBItem {
  id?: number;
  baslik: string;
  icerik: string;
  etiketler: string[];
}

export default function AdminDashboard({ onClose }: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<'admin' | 'user' | 'knowledge'>('user');
  
  // Admin State
  const [logs, setLogs] = useState<string[]>(['Sistem hazır. Bot tetiklenmesi bekleniyor...']);
  const [isRunning, setIsRunning] = useState(false);
  const [ilanSecimi, setIlanSecimi] = useState('1'); 
  const logsEndRef = useRef<HTMLDivElement>(null);

  // User Settings State
  const [modelMode, setModelMode] = useState<'karma' | 'gercek' | 'sentetik'>('karma');
  const [isRetraining, setIsRetraining] = useState(false);

  // Knowledge Base State
  const [bbItems, setBbItems] = useState<BBItem[]>([]);
  const [editingItem, setEditingItem] = useState<BBItem | null>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  useEffect(() => {
    socket.emit('ayarlar_al');
    socket.emit('bb_getir');
    
    socket.on('ayarlar', (data) => {
      if (data.model_modu) setModelMode(data.model_modu);
    });

    socket.on('scraper_log', (data) => setLogs((prev) => [...prev, data.log]));
    socket.on('scraper_status', (data) => {
      if (data.durum === 'tamamlandi' || data.durum === 'hata') setIsRunning(false);
    });
    
    socket.on('ml_sonuc', (data) => {
      setIsRetraining(false);
      if(data.durum === 'ok') {
        alert(data.mesaj);
        setModelMode(data.mod);
      } else {
        alert("Hata: " + data.mesaj);
      }
    });

    socket.on('bb_liste', (data) => {
      setBbItems(data.veriler || []);
    });

    socket.on('bb_sonuc', (data) => {
      if(data.durum === 'ok') {
        setEditingItem(null);
        socket.emit('bb_getir');
      } else {
        alert("Hata: " + data.mesaj);
      }
    });

    return () => {
      socket.off('ayarlar');
      socket.off('scraper_log');
      socket.off('scraper_status');
      socket.off('ml_sonuc');
      socket.off('bb_liste');
      socket.off('bb_sonuc');
    };
  }, []);

  const startScraper = (scriptName: string) => {
    if (isRunning) return;
    setIsRunning(true);
    setLogs((prev) => [...prev, `\n> ${scriptName} BAŞLATILIYOR... (Seçim: ${ilanSecimi})`]);
    socket.emit('start_scraper', { script: scriptName, secim: ilanSecimi });
  };

  const handleRetrain = (mod: 'karma' | 'gercek' | 'sentetik') => {
    if (isRetraining) return;
    setIsRetraining(true);
    socket.emit('ml_degistir', { mod });
  };

  const handleBBSave = () => {
    if(!editingItem) return;
    socket.emit('bb_ekle_guncelle', editingItem);
  };

  const handleBBDelete = (id?: number) => {
    if(!id) return;
    if(confirm('Bu kaydı silmek istediğinize emin misiniz?')) {
      socket.emit('bb_sil', { id });
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div className="bg-white w-full max-w-5xl h-[80vh] rounded-3xl shadow-2xl flex flex-col overflow-hidden border border-slate-200">
        
        {/* Üst Bar */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100 bg-slate-50">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-slate-900 rounded-lg text-white">
                <Settings size={20} />
              </div>
              <h2 className="text-lg font-bold text-slate-800">Ayarlar & Yönetim</h2>
            </div>
            
            {/* Sekmeler */}
            <div className="flex bg-slate-200 p-1 rounded-lg">
              <button 
                onClick={() => setActiveTab('user')}
                className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors flex items-center gap-2 ${activeTab === 'user' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <UserCog size={16} /> Kullanıcı Ayarları
              </button>
              <button 
                onClick={() => setActiveTab('knowledge')}
                className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors flex items-center gap-2 ${activeTab === 'knowledge' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <BookOpen size={16} /> Bilgi Havuzu
              </button>
              <button 
                onClick={() => setActiveTab('admin')}
                className={`px-4 py-1.5 text-sm font-semibold rounded-md transition-colors flex items-center gap-2 ${activeTab === 'admin' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-500 hover:text-slate-700'}`}
              >
                <ServerCog size={16} /> Sistem Yönetimi
              </button>
            </div>
          </div>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-700 hover:bg-slate-200 rounded-xl transition-colors">
            <X size={24} />
          </button>
        </div>

        {/* İçerik */}
        <div className="flex flex-1 overflow-hidden">
          
          {activeTab === 'user' && (
            <div className="w-full p-8 bg-slate-50 flex flex-col gap-8 overflow-y-auto">
              <div>
                <h3 className="text-xl font-bold text-slate-800 mb-2">Makine Öğrenimi (ML) Modeli Veri Seti</h3>
                <p className="text-sm text-slate-500 mb-6">Modelin eğitileceği veri setini seçin. Model anında yeniden eğitilecektir.</p>
                
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  {[
                    { id: 'gercek', title: 'Sadece Gerçek Veri', desc: 'İlan sitelerinden çekilen organik veriler.' },
                    { id: 'sentetik', title: 'Sadece Sentetik Veri', desc: 'AI tarafından üretilmiş simüle veriler.' },
                    { id: 'karma', title: 'Karma (Gerçek + Sentetik)', desc: 'Her iki veri seti birleştirilir (Önerilen).' }
                  ].map((mode) => (
                    <button
                      key={mode.id}
                      onClick={() => handleRetrain(mode.id as 'karma' | 'gercek' | 'sentetik')}
                      disabled={isRetraining}
                      className={`p-6 text-left rounded-2xl border-2 transition-all ${
                        modelMode === mode.id 
                          ? 'border-blue-500 bg-blue-50/50' 
                          : 'border-slate-200 bg-white hover:border-slate-300'
                      } ${isRetraining ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      <div className="flex items-center justify-between mb-4">
                        <Database size={24} className={modelMode === mode.id ? 'text-blue-500' : 'text-slate-400'} />
                        {modelMode === mode.id && <span className="bg-blue-100 text-blue-700 text-xs px-2 py-1 rounded font-bold">Aktif</span>}
                      </div>
                      <h4 className="font-bold text-slate-800 mb-1">{mode.title}</h4>
                      <p className="text-sm text-slate-500">{mode.desc}</p>
                    </button>
                  ))}
                </div>
                {isRetraining && (
                  <div className="mt-6 flex items-center justify-center p-4 bg-yellow-50 text-yellow-800 rounded-xl font-medium animate-pulse">
                    Model yeniden eğitiliyor, lütfen bekleyin...
                  </div>
                )}
              </div>
            </div>
          )}

          {activeTab === 'knowledge' && (
             <div className="w-full flex h-full">
                {/* Sol Taraf: Liste */}
                <div className="w-1/3 border-r border-slate-200 bg-slate-50 flex flex-col">
                  <div className="p-4 border-b border-slate-200 flex justify-between items-center">
                     <h3 className="font-bold text-slate-800">Kayıtlar</h3>
                     <button onClick={() => setEditingItem({ baslik: '', icerik: '', etiketler: [] })} className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors">
                        <Plus size={16} />
                     </button>
                  </div>
                  <div className="flex-1 overflow-y-auto p-2">
                     {bbItems.map(item => (
                        <div key={item.id} className={`p-3 rounded-xl cursor-pointer mb-2 border ${editingItem?.id === item.id ? 'bg-blue-50 border-blue-200' : 'bg-white border-slate-100 hover:border-slate-300'} transition-all`} onClick={() => setEditingItem({...item})}>
                           <div className="font-semibold text-sm text-slate-800">{item.baslik}</div>
                           <div className="text-xs text-slate-500 truncate mt-1">{item.icerik}</div>
                        </div>
                     ))}
                  </div>
                </div>

                {/* Sağ Taraf: Düzenleyici */}
                <div className="w-2/3 p-6 bg-white overflow-y-auto">
                   {editingItem ? (
                      <div className="flex flex-col gap-4 animate-in fade-in">
                         <div className="flex justify-between items-center mb-4">
                            <h3 className="text-xl font-bold text-slate-800">{editingItem.id ? 'Kaydı Düzenle' : 'Yeni Kayıt Ekle'}</h3>
                            <div className="flex gap-2">
                               {editingItem.id && (
                                  <button onClick={() => handleBBDelete(editingItem.id)} className="px-4 py-2 bg-red-100 text-red-600 rounded-xl hover:bg-red-200 font-medium text-sm flex items-center gap-2">
                                     <Trash2 size={16} /> Sil
                                  </button>
                               )}
                               <button onClick={handleBBSave} className="px-4 py-2 bg-green-600 text-white rounded-xl hover:bg-green-700 font-medium text-sm flex items-center gap-2">
                                  <Save size={16} /> Kaydet
                               </button>
                            </div>
                         </div>

                         <div>
                            <label className="text-sm font-bold text-slate-600 mb-1 block">Başlık</label>
                            <input 
                               type="text" 
                               value={editingItem.baslik} 
                               onChange={e => setEditingItem({...editingItem, baslik: e.target.value})}
                               className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-blue-500"
                               placeholder="Kayıt başlığı..."
                            />
                         </div>
                         <div>
                            <label className="text-sm font-bold text-slate-600 mb-1 block">İçerik (Kullanıcıya iletilecek cevap)</label>
                            <textarea 
                               rows={6}
                               value={editingItem.icerik} 
                               onChange={e => setEditingItem({...editingItem, icerik: e.target.value})}
                               className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-blue-500 resize-none"
                               placeholder="Detaylı bilgi..."
                            />
                         </div>
                         <div>
                            <label className="text-sm font-bold text-slate-600 mb-1 block">Etiketler (Virgülle ayırın)</label>
                            <input 
                               type="text" 
                               value={editingItem.etiketler.join(', ')} 
                               onChange={e => setEditingItem({...editingItem, etiketler: e.target.value.split(',').map(s => s.trim()).filter(s => s)})}
                               className="w-full p-3 bg-slate-50 border border-slate-200 rounded-xl outline-none focus:border-blue-500"
                               placeholder="beyan, dilekce, nasil yazilir..."
                            />
                            <p className="text-xs text-slate-400 mt-1">Asistan kullanıcının cümlesinde bu kelimeleri arar.</p>
                         </div>
                      </div>
                   ) : (
                      <div className="h-full flex flex-col items-center justify-center text-slate-400">
                         <BookOpen size={48} className="mb-4 opacity-50" />
                         <p>Düzenlemek için soldan bir kayıt seçin veya yeni ekleyin.</p>
                      </div>
                   )}
                </div>
             </div>
          )}

          {activeTab === 'admin' && (
            <>
              {/* Sol Panel: Bot Kontrolleri */}
              <div className="w-80 bg-slate-50 border-r border-slate-100 p-6 flex flex-col gap-6 overflow-y-auto">
                <div>
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">Veri Hedefi</label>
                  <select 
                    value={ilanSecimi}
                    onChange={(e) => setIlanSecimi(e.target.value)}
                    disabled={isRunning}
                    className="w-full p-3 bg-white border border-slate-200 rounded-xl text-sm text-slate-700 focus:outline-none focus:border-blue-500 shadow-sm"
                  >
                    <option value="1">5 İlan (Hızlı Test)</option>
                    <option value="2">20 İlan (1 Sayfa)</option>
                    <option value="3">100 İlan (5 Sayfa)</option>
                    <option value="4">Sınırsız (Otonom)</option>
                  </select>
                </div>
                <div>
                  <label className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2 block">Botları Tetikle</label>
                  <div className="flex flex-col gap-2">
                    {[
                      { name: 'Arabam.com Botu', script: 'arabam_scraper.py', color: 'bg-red-50 text-red-600 border-red-100 hover:bg-red-100' },
                      { name: 'Sahibinden Botu', script: 'sahibinden_scraper.py', color: 'bg-yellow-50 text-yellow-600 border-yellow-100 hover:bg-yellow-100' },
                      { name: 'Letgo Botu', script: 'letgo_scraper.py', color: 'bg-rose-50 text-rose-600 border-rose-100 hover:bg-rose-100' },
                      { name: 'Otokoç Botu', script: 'otokoc_scraper.py', color: 'bg-blue-50 text-blue-600 border-blue-100 hover:bg-blue-100' },
                    ].map((bot) => (
                      <button 
                        key={bot.script}
                        onClick={() => startScraper(bot.script)}
                        disabled={isRunning}
                        className={`w-full flex items-center justify-between p-3 rounded-xl border text-sm font-medium transition-all ${isRunning ? 'opacity-50 cursor-not-allowed grayscale' : bot.color}`}
                      >
                        <span className="flex items-center gap-2"><Play size={16} /> {bot.name}</span>
                      </button>
                    ))}
                  </div>
                </div>
                <div className="mt-auto p-4 bg-white border border-slate-200 rounded-xl shadow-sm">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-bold text-slate-500 uppercase">Sistem Durumu</span>
                    {isRunning ? (
                      <span className="flex h-2.5 w-2.5 relative">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-green-500"></span>
                      </span>
                    ) : (
                      <span className="h-2.5 w-2.5 rounded-full bg-slate-300"></span>
                    )}
                  </div>
                  <p className="text-sm font-medium text-slate-700">
                    {isRunning ? 'Bot Çalışıyor...' : 'Beklemede'}
                  </p>
                </div>
              </div>

              {/* Sağ Panel: Canlı Terminal */}
              <div className="flex-1 bg-slate-950 p-6 flex flex-col relative">
                <div className="absolute top-0 left-0 right-0 p-3 bg-slate-900/80 backdrop-blur-sm border-b border-slate-800 flex items-center gap-2 z-10">
                  <Activity size={16} className="text-green-400" />
                  <span className="text-xs font-mono text-slate-300 uppercase tracking-widest">Canlı Terminal Akışı</span>
                </div>
                <div className="flex-1 mt-8 overflow-y-auto font-mono text-sm text-green-400 leading-relaxed pb-4 scroll-smooth">
                  {logs.map((log, i) => <div key={i} className="mb-1 break-words">{log}</div>)}
                  <div ref={logsEndRef} />
                </div>
              </div>
            </>
          )}

        </div>
      </div>
    </div>
  );
}
