from flask import Flask, render_template
from flask_socketio import SocketIO, emit, disconnect
from flask import request as flask_request
from predictor import AracFiyatModeli
from groq import Groq
from supabase import create_client, Client
from dotenv import load_dotenv
import os, json, re, csv, warnings
import pandas as pd
from datetime import datetime
import subprocess
import sys

warnings.filterwarnings('ignore')
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'gizli_anahtar_123'
socketio = SocketIO(app, cors_allowed_origins="*")

# ── API BAĞLANTILARI (GROQ & SUPABASE) ────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY") 
groq_client = Groq(api_key=GROQ_API_KEY)

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Supabase URL veya Key eksik! Lütfen .env dosyanı kontrol et.")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── GLOBAL AYARLAR ────────────────────────────────────────────────────
MODEL_MODU = "karma"   # karma | gercek | sentetik

SISTEM_PROMPT = (
    "Sen Türkiye ikinci el araç piyasası konusunda uzman bir asistansın. "
    "Yanıtını YALNIZCA Türkçe ver. Başka dil veya alfabe kullanma."
)

# Bekleyen araç bilgisi (sid → kısmi veri)
pending_bilgi: dict[str, dict] = {}

ALAN_TURKCE = {
    "marka": "marka", "model": "model", "yil": "model yılı",
    "km": "kilometre", "yakit": "yakıt tipi", "vites": "vites tipi",
}

# ── BULUT VERİ SENKRONİZASYONU VE ML MODELİ YÜKLEMESİ ─────────────────
print("☁️ Supabase bulut veritabanına bağlanılıyor...")

# 1. Bilgi Bankasını Buluttan Çek
try:
    bb_response = supabase.table('bilgi_bankasi').select("*").execute()
    bilgi_bankasi = bb_response.data
    print(f"📚 Bilgi bankası buluttan yüklendi: {len(bilgi_bankasi)} kayıt.")
except Exception as e:
    print(f"⚠️ Bilgi bankası çekilemedi, yerel JSON kullanılıyor. Hata: {e}")
    with open("bilgi_bankasi.json", "r", encoding="utf-8") as f:
        bilgi_bankasi = json.load(f)

# 2. İlanları Buluttan Çek (ML Modeli için yerel CSV'yi senkronize et)
try:
    ilanlar_response = supabase.table('ilanlar').select("*").execute()
    if ilanlar_response.data:
        df_ilanlar = pd.DataFrame(ilanlar_response.data)
        df_ilanlar.to_csv("arac_verisi.csv", index=False)
        print(f"🚗 Veritabanı senkronize edildi: {len(df_ilanlar)} ilan güncellendi.")
except Exception as e:
    print(f"⚠️ İlanlar çekilemedi, mevcut yerel CSV kullanılacak. Hata: {e}")

print("🤖 ML Modeli yükleniyor...")
ml_model = AracFiyatModeli(veri_yolu="arac_verisi.csv")

# ── FEEDBACK LOGLAMA (BULUTA YAZMA) ───────────────────────────────────
def feedback_kaydet(soru, cevap, puan):
    try:
        supabase.table('feedback_log').insert({
            "soru": soru,
            "cevap": cevap,
            "puan": puan
        }).execute()
        print("✅ Feedback buluta başarıyla kaydedildi.")
    except Exception as e:
        print(f"❌ Feedback buluta kaydedilemedi: {e}")

# ... (Bu satırdan itibaren mevcut kodundaki bilgi_bankasi_ara, arac_bilgisi_cikart vb. fonksiyonlar aynen kalacak)


# ══════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════════════

def bilgi_bankasi_ara(soru: str) -> dict | None:
    soru_k = soru.lower()
    en_iyi, en_skor = None, 0
    for m in bilgi_bankasi:
        s = sum(1 for e in m["etiketler"] if e in soru_k)
        if s > en_skor:
            en_skor, en_iyi = s, m
    return en_iyi if en_skor >= 1 else None


def arac_bilgisi_cikart(mesaj: str) -> dict:
    """
    Groq ile mesajdan araç bilgisi çıkarır.
    Dönüş: {fiyat_sorusu, marka, model, yil, km, yakit, vites}
    """
    prompt = f"""Kullanıcı mesajını analiz et.

Mesaj: "{mesaj}"

Görev: Bu mesajda ikinci el araç fiyatı, piyasa değeri veya değerlendirme isteği var mı?

Eğer varsa araç bilgilerini çıkar:
- marka: Araç markası (Renault, Toyota vb.) Eğer model markayı ima ediyorsa çıkar (Megane→Renault)
- model: Araç modeli
- yil: Sayı olarak yıl (2019 gibi)
- km: Sayı olarak kilometre (nokta/virgül olmadan, "85 bin"→85000)
- yakit: Benzin / Dizel / Hibrit / Elektrik (normalize et)
- vites: Manuel / Otomatik (normalize et, "düz"→Manuel)

Bulunamazsa null yaz. SADECE JSON döndür:
{{"fiyat_sorusu": true veya false, "marka": ..., "model": ..., "yil": ..., "km": ..., "yakit": ..., "vites": ...}}"""

    try:
        r = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        metin = r.choices[0].message.content.strip()
        m = re.search(r'\{.*\}', metin, re.DOTALL)
        if m:
            return json.loads(m.group())
    except Exception as e:
        print(f"⚠️ Çıkarım hatası: {e}")
    return {"fiyat_sorusu": False}


def fiyat_tahmini_yap(bilgi: dict) -> dict:
    """ML tahmini + LLM yorumu üret."""
    tahmini = ml_model.tahmin_et({
        "marka": str(bilgi["marka"]).strip().title(),
        "model": str(bilgi["model"]).strip().title(),
        "yil":   int(bilgi["yil"]),
        "km":    int(bilgi["km"]),
        "yakit": str(bilgi["yakit"]).strip().title(),
        "vites": str(bilgi["vites"]).strip().title(),
    })
    formatli = f"{tahmini:,.0f} TL".replace(",", ".")

    BUGUN = 2026
    yas = BUGUN - int(bilgi["yil"])
    beklenen_km = yas * 10_000
    gercek_km   = int(bilgi["km"])
    yillik_km   = gercek_km / max(yas, 1)

    if yillik_km < 8_000:
        km_durum = "az kullanılmış"
    elif yillik_km <= 12_000:
        km_durum = "normale yakın kullanılmış"
    else:
        km_durum = "yoğun kullanılmış"

    prompt = f"""Sen Türkiye ikinci el araç piyasası uzmanısın.
Yanıtını YALNIZCA Türkçe ver. Kiril veya başka alfabe kullanma.

BİLİNEN BİLGİLER:
Araç: {bilgi['yil']} model {bilgi['marka']} {bilgi['model']}
Kilometre: {gercek_km:,} km | Yakıt: {bilgi['yakit']} | Vites: {bilgi['vites']}
Tahmini Fiyat: {formatli}

KM ANALİZİ ({BUGUN} itibarıyla {yas} yaşında):
- Türkiye ortalaması yılda 10.000 km → Beklenen: {beklenen_km:,} km
- Gerçek: {gercek_km:,} km → {km_durum} (yıllık ort. {int(yillik_km):,} km)

BİLİNMEYEN: Hasar kaydı, boya durumu, motor-mekanik durum bilinmiyor.

ŞABLONA UYAN 3 PARAGRAF YAZ — fazla ekleme, fiyat itirazı yapma:

"{bilgi['yil']} model {bilgi['marka']} {bilgi['model']} sorguladığınız araç için tahmini piyasa değeri {formatli} olarak belirlenmiştir.

Kilometre değerlendirmesi yapacak olursak: Araç {yas} yaşında olup Türkiye ortalamasına (yılda yaklaşık 10.000 km) göre {beklenen_km:,} km civarında olması beklenmektedir; aracın {gercek_km:,} km'si bu ortalamayla kıyaslandığında [az/normale yakın/yoğun] kullanılmış sayılır.

Hasar kaydı, boya durumu ve motor-mekanik gibi bilinmeyen faktörler bu değerlendirmeye dahil edilmemiştir; bu etkenler gerçek piyasa değerini doğrudan etkileyebilir. Aracı detaylı bir ekspere sokarak uzman görüşü almanızı tavsiye ederiz." """

    r = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
    )
    yorum = r.choices[0].message.content

    return {"fiyat": formatli, "yorum": yorum, "ham_fiyat": tahmini}


def genel_soru_cevapla(mesaj: str) -> dict:
    """Bilgi bankası + LLM ile genel soru cevapla."""
    eslesen = bilgi_bankasi_ara(mesaj)
    ctx = (
        f"Bilgi bankamızdan:\nKonu: {eslesen['baslik']}\n{eslesen['icerik']}"
        if eslesen else
        "Bu konuda doğrudan kayıt yok, genel bilginle yardımcı ol."
    )

    prompt = f"""{SISTEM_PROMPT}

Kullanıcı sorusu: {mesaj}

{ctx}

Kurallar:
- Verilen bilgiyi kendi cümlelerinle aktar, samimi ve anlaşılır ol.
- Kesinlikle fiyat uydurmaya çalışma; fiyat soruları için araç bilgilerini iste.
- 3-5 cümle yaz."""

    r = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
    )
    return {
        "cevap":  r.choices[0].message.content,
        "kaynak": eslesen["baslik"] if eslesen else None,
    }


def feedback_kaydet(soru, cevap, puan):
    with open(FEEDBACK_DOSYASI, "a", newline="", encoding="utf-8") as f:
        csv.writer(f).writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M"),
            soru[:200], cevap[:300], puan
        ])


# ══════════════════════════════════════════════════════════════════════
# FLASK ROUTE
# ══════════════════════════════════════════════════════════════════════

@app.route('/')
def index():
    return render_template('index.html')


# ══════════════════════════════════════════════════════════════════════
# WEBSOCKET OLAYLARI
# ══════════════════════════════════════════════════════════════════════

@socketio.on('connect')
def on_connect():
    print("🟢 Bağlandı:", flask_request.sid)


@socketio.on('disconnect')
def on_disconnect():
    sid = flask_request.sid
    if sid in pending_bilgi:
        del pending_bilgi[sid]
    print("🔴 Ayrıldı:", sid)


@socketio.on('kullanici_mesaj') # DİKKAT 1: İsim değişti (React'ın gönderdiği isim)
def handle_chat(data):
    """
    Tüm kullanıcı mesajlarını işler.
    Fiyat sorusuysa ML + LLM, değilse bilgi bankası + LLM.
    """
    sid = flask_request.sid
    mesaj = data.get("mesaj", "").strip()
    if not mesaj:
        return

    print(f"💬 [{sid[:6]}] {mesaj}")

    try:
        # ── Bekleyen araç bilgisi var mı? ──────────────────────────
        if sid in pending_bilgi:
            yeni = arac_bilgisi_cikart(mesaj)

            if not yeni.get("fiyat_sorusu"):
                # Kullanıcı konuyu değiştirdi
                del pending_bilgi[sid]
                sonuc = genel_soru_cevapla(mesaj)
                emit("bot_mesaj", { # DİKKAT 2: chat_yanit yerine bot_mesaj oldu
                    "tip": "text",
                    "metin_cevap": sonuc["cevap"]
                })
                return

            # Yeni gelen alanları birleştir
            for k in ["marka", "model", "yil", "km", "yakit", "vites"]:
                if yeni.get(k):
                    pending_bilgi[sid][k] = yeni[k]

            eksik = [k for k in ["marka","model","yil","km","yakit","vites"]
                     if not pending_bilgi[sid].get(k)]

            if eksik:
                eksik_str = "\n• ".join(ALAN_TURKCE[k] for k in eksik)
                emit("bot_mesaj", {
                    "tip": "text",
                    "metin_cevap": f"Şu bilgilere hâlâ ihtiyacım var:\n• {eksik_str}"
                })
                return

            # Tüm bilgiler tamam → tahmin
            bilgi = dict(pending_bilgi[sid])
            del pending_bilgi[sid]
            print(f"💰 Tahmin yapılıyor: {bilgi}")
            sonuc = fiyat_tahmini_yap(bilgi)
            
            # YENİ JSON YAPISI BURADA:
            emit("bot_mesaj", {
                "tip": "degerleme",
                "metin_cevap": sonuc["yorum"],
                "metrikler": {
                    "tahmin_edilen_fiyat": int(sonuc["ham_fiyat"]),
                    "min_fiyat": int(sonuc["ham_fiyat"] * 0.95), # %5 alt sınır
                    "max_fiyat": int(sonuc["ham_fiyat"] * 1.05)  # %5 üst sınır
                }
            })
            return

        # ── Yeni mesaj ─────────────────────────────────────────────
        cikartilan = arac_bilgisi_cikart(mesaj)
        print(f"🎯 Intent: {'fiyat' if cikartilan.get('fiyat_sorusu') else 'bilgi'}")

        if cikartilan.get("fiyat_sorusu"):
            eksik = [k for k in ["marka","model","yil","km","yakit","vites"]
                     if not cikartilan.get(k)]

            if not eksik:
                # Direkt tahmin
                bilgi = {k: cikartilan[k] for k in
                         ["marka","model","yil","km","yakit","vites"]}
                print(f"💰 Direkt tahmin: {bilgi}")
                sonuc = fiyat_tahmini_yap(bilgi)
                
                # YENİ JSON YAPISI BURADA:
                emit("bot_mesaj", {
                    "tip": "degerleme",
                    "metin_cevap": sonuc["yorum"],
                    "metrikler": {
                        "tahmin_edilen_fiyat": int(sonuc["ham_fiyat"]),
                        "min_fiyat": int(sonuc["ham_fiyat"] * 0.95),
                        "max_fiyat": int(sonuc["ham_fiyat"] * 1.05)
                    }
                })
            else:
                # Eksik bilgi iste, beklet
                pending_bilgi[sid] = {
                    k: cikartilan[k]
                    for k in ["marka","model","yil","km","yakit","vites"]
                    if cikartilan.get(k)
                }
                eksik_str = "\n• ".join(ALAN_TURKCE[k] for k in eksik)
                emit("bot_mesaj", {
                    "tip": "text",
                    "metin_cevap": f"Fiyat tahmini yapabilmek için şu bilgilere ihtiyacım var:\n• {eksik_str}"
                })
        else:
            # Genel soru
            sonuc = genel_soru_cevapla(mesaj)
            emit("bot_mesaj", {
                "tip": "text",
                "metin_cevap": sonuc["cevap"]
            })

    except Exception as e:
        print(f"❌ Hata: {e}")
        emit("bot_mesaj", {"tip": "text", "metin_cevap": f"Bir hata oluştu: {str(e)}"})


@socketio.on('ml_degistir')
def handle_ml_degistir(data):
    """Modeli farklı veri moduyla yeniden eğit."""
    global ml_model, MODEL_MODU
    mod = data.get("mod", "karma")
    print(f"🔄 Model yeniden eğitiliyor: {mod}")
    try:
        MODEL_MODU = mod
        ml_model = AracFiyatModeli(veri_yolu="arac_verisi.csv")
        emit("ml_sonuc", {"durum": "ok", "mod": mod,
                          "mesaj": f"Model '{mod}' verisiyle yeniden eğitildi."})
    except Exception as e:
        emit("ml_sonuc", {"durum": "hata", "mesaj": str(e)})


@socketio.on('prompt_guncelle')
def handle_prompt_guncelle(data):
    """Sistem promptunu güncelle."""
    global SISTEM_PROMPT
    yeni = data.get("prompt", "").strip()
    if yeni:
        SISTEM_PROMPT = yeni
        print("📝 Sistem promptu güncellendi.")
        emit("prompt_sonuc", {"durum": "ok"})
    else:
        emit("prompt_sonuc", {"durum": "hata", "mesaj": "Prompt boş olamaz."})


@socketio.on('ayarlar_al')
def handle_ayarlar_al():
    """Mevcut ayarları gönder."""
    emit("ayarlar", {
        "model_modu": MODEL_MODU,
        "sistem_prompt": SISTEM_PROMPT,
        "bilgi_bankasi": [{"id": m["id"], "baslik": m["baslik"]}
                          for m in bilgi_bankasi],
    })


@socketio.on('feedback')
def handle_feedback(data):
    try:
        feedback_kaydet(data.get("soru",""), data.get("cevap",""), data.get("puan",0))
        emit("feedback_alindi", {"durum": "ok"})
    except Exception as e:
        print(f"❌ Feedback hata: {e}")


def run_scraper_task(script_name, secim_kodu, sid):
    """Botları arka planda çalıştırır ve çıktılarını anlık olarak arayüze yollar."""
    try:
        # Botu alt işlem olarak başlat
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # Bota kaç ilan çekeceği bilgisini (1, 2, 3, 4) gönder (Sanki terminalden girilmiş gibi)
        process.stdin.write(f"{secim_kodu}\n")
        process.stdin.flush()

        # Botun terminale yazdırdığı her satırı anlık olarak React'a (Frontend) fırlat
        for line in process.stdout:
            socketio.emit('scraper_log', {'log': line.strip()}, to=sid)

        process.wait()
        socketio.emit('scraper_log', {'log': f'--- {script_name} İŞLEMİ TAMAMLANDI ---'}, to=sid)
        socketio.emit('scraper_status', {'durum': 'tamamlandi'}, to=sid)
        
    except Exception as e:
        socketio.emit('scraper_log', {'log': f'❌ Hata oluştu: {str(e)}'}, to=sid)
        socketio.emit('scraper_status', {'durum': 'hata'}, to=sid)

@socketio.on('start_scraper')
def handle_start_scraper(data):
    """React'tan gelen bot başlatma komutunu yakalar."""
    script_name = data.get('script')
    secim = data.get('secim', '1') # Varsayılan: 1 (5 ilan)
    sid = flask_request.sid
    
    # İşlemi ana Flask sunucusunu dondurmamak için arka planda (Background Task) başlat
    socketio.start_background_task(run_scraper_task, script_name, secim, sid)


if __name__ == '__main__':
    print("🚀 Araç Asistan → http://127.0.0.1:5000")
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)

    """Merhaba! Ben Araç Asistan. 👋

Araç fiyatı öğrenmek için bilgileri doğrudan yazabilirsiniz:
"2019 Renault Megane 85.000 km benzin otomatik kaç eder?"

Ya da ikinci el araç, sigorta, hasar, ekspertiz gibi konularda soru sorabilirsiniz.
2007 model 220000 kilometrede Dizel Manuel bir Hyundai Getz'im var piyasada oluru nedir ?
TAHMİNİ PİYASA DEĞERİ
393.000 TL
2007 model Hyundai Getz sorguladığınız araç için tahmini piyasa değeri 393.000 TL olarak belirlenmiştir.

Kilometre değerlendirmesi yapacak olursak: Araç 19 yaşında olup Türkiye ortalamasına (yılda yaklaşık 10.000 km) göre 190,000 km civarında olması beklenmektedir; aracın gerçek kilometre değeri 220,000 km olarak kaydedilmiştir. Bu durum aracı normale yakın kullanılan bir araç kategorisine yerletirir.

Hasar kaydı, boya durumu ve motor-mekanik gibi bilinmeyen faktörler bu değerlendirmeye dahil edilmemiştir; bu etkenler gerçek piyasa değerini doğrudan etkileyebilir. Aracı detaylı bir ekspere sokarak uzman görüşü almanızı tavsiye ederiz.

tam isabet ya da yaklaşık fiyat aralığı

sohbet devamlılığı 2 parça boya var 

grafiklerle destek

feedbackte hata.

bilgi bankası siteden düzenlenebilir.
"""