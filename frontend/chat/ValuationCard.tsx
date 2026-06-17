import React from 'react';

interface ValuationCardProps {
  metrics: {
    tahmin_edilen_fiyat: number;
    min_fiyat: number;
    max_fiyat: number;
  };
}

export default function ValuationCard({ metrics }: ValuationCardProps) {
  const { tahmin_edilen_fiyat, min_fiyat, max_fiyat } = metrics;
  
  const range = max_fiyat - min_fiyat;
  const position = ((tahmin_edilen_fiyat - min_fiyat) / range) * 100;

  const formatPrice = (price: number) => price.toLocaleString('tr-TR');

  return (
    <div className="mt-4 p-5 bg-white border border-slate-100 shadow-sm rounded-2xl w-full max-w-md">
      <div className="flex items-center justify-between mb-4">
        <h4 className="text-sm font-semibold text-slate-500 uppercase tracking-wide">Piyasa Analizi</h4>
        <span className="px-2.5 py-1 bg-green-100 text-green-700 text-xs font-bold rounded-full">
          Yüksek Güven
        </span>
      </div>

      <div className="text-center mb-8">
        <div className="text-3xl font-extrabold text-slate-800 tracking-tight">
          {formatPrice(tahmin_edilen_fiyat)} <span className="text-xl text-slate-400 font-medium">TL</span>
        </div>
        <p className="text-xs text-slate-400 mt-1">Yapay Zeka Destekli Tahmin</p>
      </div>

      {/* Görsel Bar / Gösterge - YENİ HİZALAMA */}
      <div className="relative pt-2 pb-4">
        {/* Min / Max Etiketleri */}
        <div className="flex justify-between text-xs text-slate-400 font-medium mb-3">
          <span>Min: {formatPrice(min_fiyat)}</span>
          <span>Max: {formatPrice(max_fiyat)}</span>
        </div>
        
        {/* Arka Plan Barı ve Nokta (Pin) Konteyneri */}
        <div className="relative h-3 w-full bg-slate-100 rounded-full flex items-center">
          {/* Renkli Bar */}
          <div className="h-full bg-gradient-to-r from-blue-400 via-indigo-500 to-violet-500 rounded-full w-full opacity-80"></div>

          {/* Tahmin Noktası (Pin) - Artık tam çizgide ortalanmış durumda (-translate-y-1/2) */}
          <div 
            className="absolute top-1/2 -translate-y-1/2 -ml-3 flex flex-col items-center transition-all duration-700 ease-out z-10"
            style={{ left: `${Math.max(5, Math.min(95, position))}%` }}
          >
            <div className="w-6 h-6 bg-white border-4 border-indigo-600 rounded-full shadow-md"></div>
          </div>
        </div>
      </div>
    </div>
  );
}