import React from 'react';
import { Car, Calendar, Gauge, Fuel, Settings2 } from 'lucide-react';

interface VehicleInfoCardProps {
  arac_bilgisi: {
    marka: string;
    model: string;
    yil: number;
    km: number;
    yakit: string;
    vites: string;
  };
}

export default function VehicleInfoCard({ arac_bilgisi }: VehicleInfoCardProps) {
  const formatKm = (km: number) => km.toLocaleString('tr-TR');

  return (
    <div className="mt-4 p-5 bg-white border border-slate-100 shadow-sm rounded-2xl w-full max-w-sm flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Araç Özeti</h4>
        <Car size={16} className="text-blue-500" />
      </div>

      <div className="flex flex-col gap-3 flex-1 justify-center">
        <div className="flex justify-between items-center border-b border-slate-50 pb-2">
           <span className="text-xs text-slate-400 font-medium flex items-center gap-2"><Car size={14}/> Marka / Model</span>
           <span className="text-sm font-bold text-slate-700 text-right">{arac_bilgisi.marka} {arac_bilgisi.model}</span>
        </div>
        <div className="flex justify-between items-center border-b border-slate-50 pb-2">
           <span className="text-xs text-slate-400 font-medium flex items-center gap-2"><Calendar size={14}/> Model Yılı</span>
           <span className="text-sm font-bold text-slate-700">{arac_bilgisi.yil}</span>
        </div>
        <div className="flex justify-between items-center border-b border-slate-50 pb-2">
           <span className="text-xs text-slate-400 font-medium flex items-center gap-2"><Gauge size={14}/> Kilometre</span>
           <span className="text-sm font-bold text-slate-700">{formatKm(arac_bilgisi.km)} km</span>
        </div>
        <div className="flex justify-between items-center border-b border-slate-50 pb-2">
           <span className="text-xs text-slate-400 font-medium flex items-center gap-2"><Fuel size={14}/> Yakıt Tipi</span>
           <span className="text-sm font-bold text-slate-700">{arac_bilgisi.yakit}</span>
        </div>
        <div className="flex justify-between items-center">
           <span className="text-xs text-slate-400 font-medium flex items-center gap-2"><Settings2 size={14}/> Vites Tipi</span>
           <span className="text-sm font-bold text-slate-700">{arac_bilgisi.vites}</span>
        </div>
      </div>
    </div>
  );
}
