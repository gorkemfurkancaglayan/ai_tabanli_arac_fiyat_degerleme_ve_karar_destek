import os
import json
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

# .env dosyasından ayarları yükle
load_dotenv()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL veya Key bulunamadı! .env dosyasını kontrol et.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("🚀 Supabase Veri Aktarımı Başlıyor...\n")

# ---------------------------------------------------------
# 1. BİLGİ BANKASI AKTARIMI
# ---------------------------------------------------------
try:
    if os.path.exists("bilgi_bankasi.json"):
        with open("bilgi_bankasi.json", "r", encoding="utf-8") as f:
            bb_data = json.load(f)
        
        # upsert: Veri varsa günceller, yoksa ekler
        supabase.table("bilgi_bankasi").upsert(bb_data).execute()
        print(f"✅ Bilgi Bankası aktarıldı ({len(bb_data)} kayıt).")
    else:
        print("⚠️ bilgi_bankasi.json bulunamadı, atlanıyor.")
except Exception as e:
    print(f"❌ Bilgi Bankası aktarım hatası: {e}")

# ---------------------------------------------------------
# 2. FEEDBACK LOG AKTARIMI
# ---------------------------------------------------------
try:
    if os.path.exists("feedback_log.csv"):
        df_fb = pd.read_csv("feedback_log.csv")
        # Eğer dosya boş değilse
        if not df_fb.empty:
            fb_records = df_fb.to_dict(orient="records")
            supabase.table("feedback_log").insert(fb_records).execute()
            print(f"✅ Feedback Log aktarıldı ({len(fb_records)} kayıt).")
        else:
            print("⚠️ Feedback log dosyası boş, atlanıyor.")
    else:
        print("⚠️ feedback_log.csv bulunamadı, atlanıyor.")
except Exception as e:
    print(f"❌ Feedback log aktarım hatası: {e}")

# ---------------------------------------------------------
# 3. İLANLAR (ARAÇ VERİSİ) AKTARIMI
# ---------------------------------------------------------
try:
    if os.path.exists("arac_verisi.csv"):
        df_arac = pd.read_csv("arac_verisi.csv")
        
        # NaN (boş) değerleri veritabanı için None'a çevir
        df_arac = df_arac.where(pd.notnull(df_arac), None)
        arac_records = df_arac.to_dict(orient="records")
        
        # Eğer çok ilan varsa Supabase limiti takılmasın diye 500'erli paketler (chunk) halinde yolluyoruz
        chunk_size = 500
        for i in range(0, len(arac_records), chunk_size):
            chunk = arac_records[i:i + chunk_size]
            # on_conflict: Eğer aynı ilan_no ve site varsa üzerine yazar (mükerrer kaydı önler)
            supabase.table("ilanlar").upsert(chunk, on_conflict="ilan_no,site").execute()
            
        print(f"✅ Araç Verileri (İlanlar) aktarıldı ({len(arac_records)} kayıt).")
    else:
        print("⚠️ arac_verisi.csv bulunamadı, atlanıyor.")
except Exception as e:
    print(f"❌ Araç verisi aktarım hatası: {e}")

print("\n🎉 Tüm veri aktarım işlemleri başarıyla tamamlandı!")