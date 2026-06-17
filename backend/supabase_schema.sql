-- 1. Sohbetler Tablosunu Oluştur
CREATE TABLE IF NOT EXISTS public.sohbetler (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    baslik TEXT NOT NULL,
    aktif BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- 2. Mesajlar Tablosunu Oluştur
CREATE TABLE IF NOT EXISTS public.mesajlar (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sohbet_id UUID REFERENCES public.sohbetler(id) ON DELETE CASCADE,
    gonderen TEXT CHECK (gonderen IN ('user', 'bot')),
    tip TEXT DEFAULT 'text',
    metin TEXT,
    metrikler JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT timezone('utc'::text, now()) NOT NULL
);

-- RLS (Row Level Security) Ayarları
ALTER TABLE public.sohbetler DISABLE ROW LEVEL SECURITY;
ALTER TABLE public.mesajlar DISABLE ROW LEVEL SECURITY;
