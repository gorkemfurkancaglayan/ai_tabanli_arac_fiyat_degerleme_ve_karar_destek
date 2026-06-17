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

# Bekleyen araç bilgisi (sohbet_id → kısmi veri)
pending_bilgi: dict[str, dict] = {}

ALAN_TURKCE = {
    "marka": "marka", "model": "model", "yil": "model yılı",
    "km": "kilometre", "yakit": "yakıt tipi", "vites": "vites tipi",
}

print("☁️ Supabase bulut veritabanına bağlanılıyor...")

try:
    bb_response = supabase.table('bilgi_bankasi').select("*").execute()
    bilgi_bankasi = bb_response.data
    print(f"📚 Bilgi bankası buluttan yüklendi: {len(bilgi_bankasi)} kayıt.")
except Exception as e:
    print(f"⚠️ Bilgi bankası çekilemedi, yerel JSON kullanılıyor. Hata: {e}")
    with open("bilgi_bankasi.json", "r", encoding="utf-8") as f:
        bilgi_bankasi = json.load(f)

def bilgi_bankasi_guncelle_global():
    global bilgi_bankasi
    try:
        bb_response = supabase.table('bilgi_bankasi').select("*").order('id').execute()
        bilgi_bankasi = bb_response.data
    except Exception as e:
        print(f"BB güncellenemedi: {e}")


print("🤖 ML Modeli yükleniyor...")
ml_model = AracFiyatModeli(veri_yolu="arac_verisi.csv", mod=MODEL_MODU)

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
    prompt = f"""Kullanıcı mesajını analiz et.
Mesaj: "{mesaj}"
Görev: Bu mesajda ikinci el araç fiyatı, piyasa değeri veya değerlendirme isteği var mı?
Eğer varsa araç bilgilerini çıkar:
- marka: Araç markası (Eğer kullanıcı "Passat", "Focus" gibi sadece model yazdıysa, markayı "Volkswagen", "Ford" şeklinde otomobil bilginle sen tamamla. Asla markayı ve modeli aynı kelime yapma.)
- model: Araç modeli (Sadece model adı)
- yil: Sayı olarak yıl
- km: Sayı olarak kilometre ("85 bin"→85000)
- yakit: Benzin / Dizel / Hibrit / Elektrik
- vites: Manuel / Otomatik

ÖNEMLİ KURALLAR:
1. Kullanıcı mesajında ilgili bilgi kesin olarak YOKSA (örneğin mesaj sadece "kaput boyalı" diyorsa ve yıl/km/marka belirtmiyorsa), O ALANLARI KESİNLİKLE null OLARAK BIRAK. Asla varsayılan bir değer (örn: 2019, 85000, Passat) UYDURMA.
2. SADECE GEÇERLİ BİR JSON DÖNDÜR. Markdown işaretleri KULLANMA.

Format:
{{"fiyat_sorusu": true_veya_false, "marka": "...", "model": "...", "yil": 1234, "km": 12345, "yakit": "...", "vites": "..."}}"""

    try:
        r = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        metin = r.choices[0].message.content.strip()
        
        # Markdown kod bloklarını temizle
        if metin.startswith("```json"):
            metin = metin[7:]
        if metin.startswith("```"):
            metin = metin[3:]
        if metin.endswith("```"):
            metin = metin[:-3]
        metin = metin.strip()

        m = re.search(r'\{.*\}', metin, re.DOTALL)
        if m:
            json_str = m.group()
            return json.loads(json_str)
    except Exception as e:
        print(f"⚠️ Çıkarım hatası: {e}")
        try:
            print(f"LLM Ham Çıktısı: {metin}")
        except:
            pass
    return {"fiyat_sorusu": False}

def asistan_fiyat_guncelle(yeni_mesaj: str, baz_fiyat: int) -> dict:
    formatli_fiyat = f"{baz_fiyat:,.0f} TL".replace(",", ".")
    
    kurallar_metni = "Hasar/Boya kaydı oranları sisteme tanımlanmamış. Piyasa tecrübene dayanarak adil bir % düşüş hesapla."
    if 'bilgi_bankasi' in globals():
        for b in bilgi_bankasi:
            if b.get("etiketler") and "hasar_kurallari" in [str(e).strip().lower() for e in b["etiketler"]]:
                kurallar_metni = f"Değer Kaybı Kuralları Tablosu:\n{b['icerik']}"
                break
                
    prompt = f"""Sen Türkiye ikinci el araç piyasası uzmanı ve değerleme asistanısın.
Sistemimiz (ML Modeli) bu aracın HATASIZ ve ORTALAMA DURUMDAKİ baz fiyatını {formatli_fiyat} olarak kesin bir şekilde belirlemiştir. 
ML modelinin ürettiği bu baz fiyat en büyük otoritedir ve DEĞİŞTİRİLEMEZ BİR ÇIPADIR.

Kullanıcı araca dair şu yeni bilgiyi verdi: "{yeni_mesaj}"

AŞAĞIDAKİ KURALLARA KESİNLİKLE UY:
{kurallar_metni}

GÖREVİN:
1. Kullanıcının verdiği bilginin (boya, tramer, değişen vs.) arabanın değerini nasıl etkileyeceğini YUKARIDAKİ KURALLAR TABLOSUNU kullanarak hesapla.
2. Kurallara göre bulunan oranları topla ve baz fiyat olan {baz_fiyat} üzerinden tam o oranda indirim yap.
3. Asla yepyeni, bağımsız bir fiyat uydurma veya kendi kafandan oran ekleme. Kurallara sadık kal. "Modelimizin belirlediği X fiyatı üzerinden, belirttiğiniz hasar sebebiyle (tablomuzdaki kurallara göre %Y düşüş) güncel değer Z civarında tahmin edilmektedir" gibi açıklayıcı ve yapıcı bir dil kullan.

SADECE JSON döndür:
{{"yorum": "kullanıcıya gösterilecek 2-3 cümlelik asistan yorumu", "guncel_fiyat": hesaplanan_yeni_fiyat_int}}"""

    try:
        r = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        metin = r.choices[0].message.content.strip()
        m = re.search(r'\{.*\}', metin, re.DOTALL)
        if m:
            data = json.loads(m.group())
            yeni_fiyat = int(data.get("guncel_fiyat", baz_fiyat))
            return {
                "yorum": data.get("yorum", ""),
                "metrikler": {
                    "tahmin_edilen_fiyat": yeni_fiyat,
                    "min_fiyat": int(yeni_fiyat * 0.95),
                    "max_fiyat": int(yeni_fiyat * 1.05)
                }
            }
    except Exception as e:
        print(f"Asistan Hata: {e}")
        
    return {
        "yorum": "Verdiğiniz bilgiler doğrultusunda fiyat analizimiz güncellenemedi.",
        "metrikler": {
            "tahmin_edilen_fiyat": baz_fiyat,
            "min_fiyat": int(baz_fiyat * 0.95),
            "max_fiyat": int(baz_fiyat * 1.05)
        }
    }

def fiyat_tahmini_yap(bilgi: dict) -> dict:
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


# ══════════════════════════════════════════════════════════════════════
# WEBSOCKET OLAYLARI (SUPABASE HAFIZASI EKLENDİ)
# ══════════════════════════════════════════════════════════════════════

@socketio.on('connect')
def on_connect():
    print("🟢 Bağlandı:", flask_request.sid)

@socketio.on('disconnect')
def on_disconnect():
    print("🔴 Ayrıldı:", flask_request.sid)

@socketio.on('sohbetleri_getir')
def handle_sohbetleri_getir():
    sid = flask_request.sid
    try:
        res = supabase.table('sohbetler').select('*').eq('aktif', True).order('created_at', desc=True).execute()
        emit("sohbetler_liste", {"sohbetler": res.data}, to=sid)
    except Exception as e:
        print(f"⚠️ Sohbetler çekilemedi: {e}")

@socketio.on('sohbet_olustur')
def handle_sohbet_olustur(data):
    sid = flask_request.sid
    baslik = data.get("baslik", "Yeni Sohbet")
    try:
        res = supabase.table('sohbetler').insert({"baslik": baslik, "aktif": True}).execute()
        emit("sohbet_olusturuldu", {"sohbet": res.data[0]}, to=sid)
    except Exception as e:
        print(f"⚠️ Sohbet oluşturulamadı: {e}")

@socketio.on('sohbeti_sil')
def handle_sohbet_sil(data):
    sohbet_id = data.get("sohbet_id")
    if sohbet_id:
        try:
            supabase.table('sohbetler').update({"aktif": False}).eq("id", sohbet_id).execute()
            emit("sohbet_silindi", {"sohbet_id": sohbet_id})
        except Exception as e:
            print(f"⚠️ Sohbet silinemedi: {e}")

@socketio.on('mesajlari_getir')
def handle_mesajlari_getir(data):
    sid = flask_request.sid
    sohbet_id = data.get("sohbet_id")
    if sohbet_id:
        try:
            res = supabase.table('mesajlar').select('*').eq('sohbet_id', sohbet_id).order('created_at').execute()
            emit("eski_mesajlar", {"mesajlar": res.data}, to=sid)
        except Exception as e:
            print(f"⚠️ Mesajlar çekilemedi: {e}")

@socketio.on('kullanici_mesaj')
def handle_chat(data):
    sid = flask_request.sid
    mesaj = data.get("mesaj", "").strip()
    sohbet_id = data.get("sohbet_id")
    
    if not mesaj or not sohbet_id:
        emit("bot_mesaj", {"tip": "text", "metin_cevap": "Geçerli bir sohbet bulunamadı veya mesaj boş."})
        return

    print(f"💬 [{sid[:6]}] (Sohbet: {sohbet_id[:8]}) {mesaj}")

    try:
        # 1. Kullanıcı mesajını kaydet
        supabase.table('mesajlar').insert({
            "sohbet_id": sohbet_id,
            "gonderen": "user",
            "tip": "text",
            "metin": mesaj
        }).execute()

        # 2. Geçmişi çekip analiz et
        gecmis_res = supabase.table('mesajlar').select('*').eq('sohbet_id', sohbet_id).order('created_at', desc=True).limit(10).execute()
        gecmis = list(reversed(gecmis_res.data))
        degerleme_mesajlari = [m for m in gecmis if m.get("tip") == "degerleme"]

        # 3. LLM Niyet Çıkarımı (Tek Sefer)
        cikartilan = arac_bilgisi_cikart(mesaj)
        yeni_arac_mi = bool(cikartilan.get("marka") and cikartilan.get("model"))

        # ── SOHBET DEVAMLILIĞI ──
        if degerleme_mesajlari and not yeni_arac_mi and cikartilan.get("fiyat_sorusu"):
            son_degerleme = degerleme_mesajlari[-1]
            baz_fiyat = son_degerleme.get("metrikler", {}).get("tahmin_edilen_fiyat") if son_degerleme.get("metrikler") else None
            eski_arac_bilgisi = son_degerleme.get("metrikler", {}).get("arac_bilgisi", {})
            
            if baz_fiyat:
                asistan_yaniti = asistan_fiyat_guncelle(mesaj, baz_fiyat)
                asistan_yaniti["metrikler"]["arac_bilgisi"] = eski_arac_bilgisi
                supabase.table('mesajlar').insert({
                    "sohbet_id": sohbet_id, "gonderen": "bot", "tip": "degerleme",
                    "metin": asistan_yaniti["yorum"], "metrikler": asistan_yaniti["metrikler"]
                }).execute()
                emit("bot_mesaj", {"tip": "degerleme", "metin_cevap": asistan_yaniti["yorum"], "metrikler": asistan_yaniti["metrikler"]})
                return

        # ── NORMAL AKIŞ (EKSİK BİLGİ TAMAMLAMA) ──
        if sohbet_id in pending_bilgi:
            if not cikartilan.get("fiyat_sorusu"):
                del pending_bilgi[sohbet_id]
                sonuc = genel_soru_cevapla(mesaj)
                supabase.table('mesajlar').insert({"sohbet_id": sohbet_id, "gonderen": "bot", "tip": "text", "metin": sonuc["cevap"]}).execute()
                emit("bot_mesaj", {"tip": "text", "metin_cevap": sonuc["cevap"]})
                return

            for k in ["marka", "model", "yil", "km", "yakit", "vites"]:
                if cikartilan.get(k):
                    pending_bilgi[sohbet_id][k] = cikartilan[k]

            eksik = [k for k in ["marka","model","yil","km","yakit","vites"] if not pending_bilgi[sohbet_id].get(k)]
            if eksik:
                eksik_str = "\\n• ".join(ALAN_TURKCE[k] for k in eksik)
                cevap = f"Şu bilgilere hâlâ ihtiyacım var:\\n• {eksik_str}"
                supabase.table('mesajlar').insert({"sohbet_id": sohbet_id, "gonderen": "bot", "tip": "text", "metin": cevap}).execute()
                emit("bot_mesaj", {"tip": "text", "metin_cevap": cevap})
                return

            bilgi = dict(pending_bilgi[sohbet_id])
            del pending_bilgi[sohbet_id]
            sonuc = fiyat_tahmini_yap(bilgi)
            metrikler = {"tahmin_edilen_fiyat": int(sonuc["ham_fiyat"]), "min_fiyat": int(sonuc["ham_fiyat"] * 0.95), "max_fiyat": int(sonuc["ham_fiyat"] * 1.05), "arac_bilgisi": bilgi}
            supabase.table('mesajlar').insert({"sohbet_id": sohbet_id, "gonderen": "bot", "tip": "degerleme", "metin": sonuc["yorum"], "metrikler": metrikler}).execute()
            emit("bot_mesaj", {"tip": "degerleme", "metin_cevap": sonuc["yorum"], "metrikler": metrikler})
            return

        # ── YENİ ARAÇ SORGUSU VEYA GENEL SORU ──
        if cikartilan.get("fiyat_sorusu"):
            eksik = [k for k in ["marka","model","yil","km","yakit","vites"] if not cikartilan.get(k)]
            if not eksik:
                bilgi = {k: cikartilan[k] for k in ["marka","model","yil","km","yakit","vites"]}
                sonuc = fiyat_tahmini_yap(bilgi)
                metrikler = {"tahmin_edilen_fiyat": int(sonuc["ham_fiyat"]), "min_fiyat": int(sonuc["ham_fiyat"] * 0.95), "max_fiyat": int(sonuc["ham_fiyat"] * 1.05), "arac_bilgisi": bilgi}
                supabase.table('mesajlar').insert({"sohbet_id": sohbet_id, "gonderen": "bot", "tip": "degerleme", "metin": sonuc["yorum"], "metrikler": metrikler}).execute()
                emit("bot_mesaj", {"tip": "degerleme", "metin_cevap": sonuc["yorum"], "metrikler": metrikler})
            else:
                pending_bilgi[sohbet_id] = {k: cikartilan[k] for k in ["marka","model","yil","km","yakit","vites"] if cikartilan.get(k)}
                eksik_str = "\\n• ".join(ALAN_TURKCE[k] for k in eksik)
                cevap = f"Fiyat tahmini yapabilmek için şu bilgilere ihtiyacım var:\\n• {eksik_str}"
                supabase.table('mesajlar').insert({"sohbet_id": sohbet_id, "gonderen": "bot", "tip": "text", "metin": cevap}).execute()
                emit("bot_mesaj", {"tip": "text", "metin_cevap": cevap})
        else:
            # GENEL SORU (örn: beyan nedir)
            sonuc = genel_soru_cevapla(mesaj)
            supabase.table('mesajlar').insert({"sohbet_id": sohbet_id, "gonderen": "bot", "tip": "text", "metin": sonuc["cevap"]}).execute()
            emit("bot_mesaj", {"tip": "text", "metin_cevap": sonuc["cevap"]})

    except Exception as e:
        print(f"❌ Hata: {e}")
        emit("bot_mesaj", {"tip": "text", "metin_cevap": f"Bir hata oluştu: {str(e)}"})

@socketio.on('ml_degistir')
def handle_ml_degistir(data):
    global ml_model, MODEL_MODU
    mod = data.get("mod", "karma")
    try:
        MODEL_MODU = mod
        ml_model = AracFiyatModeli(veri_yolu="arac_verisi.csv", mod=MODEL_MODU)
        emit("ml_sonuc", {"durum": "ok", "mod": mod, "mesaj": f"Model '{mod}' verisiyle yeniden eğitildi."})
    except Exception as e:
        emit("ml_sonuc", {"durum": "hata", "mesaj": str(e)})

@socketio.on('prompt_guncelle')
def handle_prompt_guncelle(data):
    global SISTEM_PROMPT
    yeni = data.get("prompt", "").strip()
    if yeni:
        SISTEM_PROMPT = yeni
        emit("prompt_sonuc", {"durum": "ok"})
    else:
        emit("prompt_sonuc", {"durum": "hata", "mesaj": "Prompt boş olamaz."})

@socketio.on('ayarlar_al')
def handle_ayarlar_al():
    emit("ayarlar", {
        "model_modu": MODEL_MODU,
        "sistem_prompt": SISTEM_PROMPT
    })

def run_scraper_task(script_name, secim_kodu, sid):
    try:
        env = dict(os.environ)
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            encoding='utf-8',
            env=env
        )
        process.stdin.write(f"{secim_kodu}\n")
        process.stdin.flush()

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
    script_name = data.get('script')
    secim = data.get('secim', '1')
    sid = flask_request.sid
    socketio.start_background_task(run_scraper_task, script_name, secim, sid)


@socketio.on('bb_getir')
def handle_bb_getir():
    sid = flask_request.sid
    bilgi_bankasi_guncelle_global()
    emit("bb_liste", {"veriler": bilgi_bankasi}, to=sid)

@socketio.on('bb_ekle_guncelle')
def handle_bb_ekle_guncelle(data):
    item_id = data.get("id")
    try:
        if item_id:
            supabase.table('bilgi_bankasi').update({
                "baslik": data["baslik"],
                "icerik": data["icerik"],
                "etiketler": data["etiketler"]
            }).eq("id", item_id).execute()
        else:
            supabase.table('bilgi_bankasi').insert({
                "baslik": data["baslik"],
                "icerik": data["icerik"],
                "etiketler": data["etiketler"]
            }).execute()
            
        bilgi_bankasi_guncelle_global()
        emit("bb_sonuc", {"durum": "ok"})
    except Exception as e:
        emit("bb_sonuc", {"durum": "hata", "mesaj": str(e)})

@socketio.on('bb_sil')
def handle_bb_sil(data):
    item_id = data.get("id")
    try:
        supabase.table('bilgi_bankasi').delete().eq("id", item_id).execute()
        bilgi_bankasi_guncelle_global()
        emit("bb_sonuc", {"durum": "ok"})
    except Exception as e:
        emit("bb_sonuc", {"durum": "hata", "mesaj": str(e)})

if __name__ == '__main__':

    print("🚀 Araç Asistan → http://127.0.0.1:5000")
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)
