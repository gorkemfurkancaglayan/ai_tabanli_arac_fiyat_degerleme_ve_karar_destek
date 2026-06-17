import React, { useState } from 'react';
import { Edit2, Send } from 'lucide-react';

interface PartState {
  id: string;
  name: string;
  status: 'orijinal' | 'lokal_boyali' | 'boyali' | 'degisen';
}

const INITIAL_PARTS: PartState[] = [
  { id: 'sol_on_camurluk', name: 'Sol Ön Çamurluk', status: 'orijinal' },
  { id: 'kaput', name: 'Kaput', status: 'orijinal' },
  { id: 'sag_on_camurluk', name: 'Sağ Ön Çamurluk', status: 'orijinal' },
  { id: 'sol_on_kapi', name: 'Sol Ön Kapı', status: 'orijinal' },
  { id: 'tavan', name: 'Tavan', status: 'orijinal' },
  { id: 'sag_on_kapi', name: 'Sağ Ön Kapı', status: 'orijinal' },
  { id: 'sol_arka_kapi', name: 'Sol Arka Kapı', status: 'orijinal' },
  { id: 'bagaj', name: 'Bagaj', status: 'orijinal' },
  { id: 'sag_arka_kapi', name: 'Sağ Arka Kapı', status: 'orijinal' },
  { id: 'sol_arka_camurluk', name: 'Sol Arka Çamurluk', status: 'orijinal' },
  { id: 'tamponlar', name: 'Tamponlar', status: 'orijinal' },
  { id: 'sag_arka_camurluk', name: 'Sağ Arka Çamurluk', status: 'orijinal' },
];

export default function CarDamageMap({ onComplete }: { onComplete: (damageData: string) => void }) {
  const [parts, setParts] = useState<PartState[]>(INITIAL_PARTS);

  const toggleStatus = (index: number) => {
    const newParts = [...parts];
    const current = newParts[index].status;
    
    // 4 Aşamalı Döngü: Orijinal -> Lokal Boyalı -> Boyalı -> Değişen -> Orijinal
    if (current === 'orijinal') newParts[index].status = 'lokal_boyali';
    else if (current === 'lokal_boyali') newParts[index].status = 'boyali';
    else if (current === 'boyali') newParts[index].status = 'degisen';
    else newParts[index].status = 'orijinal';
    
    setParts(newParts);
  };

  const getStatusColor = (status: string) => {
    if (status === 'lokal_boyali') return 'bg-orange-300 border-orange-400 text-orange-900';
    if (status === 'boyali') return 'bg-yellow-400 border-yellow-500 text-yellow-900';
    if (status === 'degisen') return 'bg-red-500 border-red-600 text-white';
    return 'bg-slate-100 border-slate-200 text-slate-600 hover:bg-slate-200';
  };

  const getStatusText = (status: string) => {
    if (status === 'lokal_boyali') return 'Lokal Boyalı';
    if (status === 'boyali') return 'Boyalı';
    if (status === 'degisen') return 'Değişen';
    return 'Orijinal';
  };

  const handleSend = () => {
    const damagedParts = parts.filter(p => p.status !== 'orijinal');
    if (damagedParts.length === 0) {
      onComplete("Araçta boyalı veya değişen parça bulunmamaktadır (Hatasız).");
      return;
    }
    
    const description = damagedParts.map(p => `${p.name} ${getStatusText(p.status).toLowerCase()}`).join(', ');
    onComplete(`Ekspertiz durumu: ${description}. Lütfen fiyatı bu kaporta durumuna göre tekrar analiz et.`);
  };

  return (
    <div className="mt-4 p-5 bg-white border border-slate-200 shadow-sm rounded-2xl w-full max-w-xl">
      <h4 className="text-sm font-semibold text-slate-700 mb-4 flex items-center gap-2">
        <Edit2 size={16} /> Kaporta & Ekspertiz Durumu
      </h4>
      
      <div className="grid grid-cols-3 gap-2 mb-6 p-4 bg-slate-50 rounded-xl border border-slate-100">
        {parts.map((part, index) => (
          <button
            key={part.id}
            onClick={() => toggleStatus(index)}
            className={`p-2 text-xs font-medium rounded-lg border transition-all duration-200 ${getStatusColor(part.status)}`}
          >
            {part.name}
            <div className="text-[10px] mt-1 opacity-80 uppercase tracking-wider">
              {getStatusText(part.status)}
            </div>
          </button>
        ))}
      </div>

      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        {/* Lejant (Bilgi Renkleri) */}
        <div className="flex flex-wrap gap-3 text-[11px] font-medium text-slate-500">
          <span className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-slate-200"></div> Orijinal</span>
          <span className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-orange-300"></div> Lokal</span>
          <span className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-yellow-400"></div> Boyalı</span>
          <span className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded-full bg-red-500"></div> Değişen</span>
        </div>
        
        <button 
          onClick={handleSend}
          className="flex items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white px-4 py-2 rounded-xl text-sm font-medium transition-colors whitespace-nowrap"
        >
          <span>Güncelle</span>
          <Send size={14} />
        </button>
      </div>
    </div>
  );
}