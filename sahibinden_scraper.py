import asyncio
from playwright.async_api import async_playwright
import random
import pandas as pd
import os
import logging
from dotenv import load_dotenv
from supabase import create_client, Client

# ==========================================
# SUPABASE BAĞLANTISI
# ==========================================
load_dotenv()
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = None

if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
else:
    print("⚠️ Supabase bilgileri .env dosyasından okunamadı. Sadece CSV'ye yazılacak.")

# ==========================================
# LOGLAMA SİSTEMİ
# ==========================================
log_dosyasi = "sahibinden_log.txt"
logging.basicConfig(
    filename=log_dosyasi, 
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

async def sahibinden_otonom_scraper():
    print("\n========================================")
    print(" 🕵️ SAHİBİNDEN.COM OTONOM VERİ AVCISI (GİZLİ MOD) ")
    print("========================================")
    print("Kaç adet ilan taramak istersiniz?")
    print("  1 - 5 İlan (Hızlı Test)")
    print("  2 - 20 İlan (1 Sayfa)")
    print("  3 - 100 İlan (5 Sayfa)")
    print("  4 - SINIRSIZ (Durdurana kadar çalışır)")
    print("========================================")
    secim = input("Seçiminiz (1/2/3/4): ").strip()
    
    hedef_ilan = 0
    if secim == "1": hedef_ilan = 5
    elif secim == "2": hedef_ilan = 20
    elif secim == "3": hedef_ilan = 100
    elif secim == "4": hedef_ilan = 9999999
    else: 
        hedef_ilan = 5

    logging.info(f"Otonom Scraper Başlatıldı. Hedef: {'Sınırsız' if hedef_ilan == 9999999 else hedef_ilan} ilan.")

    mevcut_ilanlar = set()
    ana_veritabani_dosyasi = 'arac_verisi.csv'
    
    if os.path.exists(ana_veritabani_dosyasi):
        try:
            df_mevcut = pd.read_csv(ana_veritabani_dosyasi)
            df_mevcut['ilan_no'] = df_mevcut['ilan_no'].astype(str)
            mevcut_ilanlar = set(df_mevcut['site'] + "_" + df_mevcut['ilan_no'])
            print(f"📚 Veritabanında {len(mevcut_ilanlar)} adet kayıtlı araç hafızaya alındı.")
        except Exception as e:
            logging.error(f"Veritabanı okunurken hata: {e}")

    csv_header = not os.path.exists(ana_veritabani_dosyasi)
    son_eklenen_ilan = "Henüz eklenen olmadı"

    async with async_playwright() as p:
        try:
            print("🔗 9222 portundaki Gerçek Google Chrome'a bağlanılıyor...")
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
            context = browser.contexts[0]
            page = await context.new_page()

            islenen_ilan_sayisi = 0
            offset = 0
            eklenen_yeni_ilan = 0

            while islenen_ilan_sayisi < hedef_ilan:
                url = f"https://www.sahibinden.com/kategori-vitrin?viewType=Gallery&category=3530&pagingOffset={offset}"
                print(f"\n🌐 Liste Sayfası açılıyor (Offset: {offset})...")
                await page.goto(url, timeout=60000)
                
                bekleme_suresi = random.uniform(10, 15)
                print(f"⏳ Anti-Bot Koruması: Sayfada {bekleme_suresi:.1f} saniye bekleniyor...")
                await page.wait_for_timeout(bekleme_suresi * 1000)

                sayfa_basligi = await page.title()
                if "Doğrulama" in sayfa_basligi or "Yükleniyor" in sayfa_basligi:
                    print("🚨 Captcha veya Giriş ekranı çıktı! Lütfen Chrome'da manuel müdahale edin.")
                    await page.wait_for_timeout(60000)

                print("🔗 İlan linkleri toplanıyor...")
                ilan_linkleri = await page.evaluate('''() => {
                    const a_taglari = Array.from(document.querySelectorAll('a'));
                    const hrefler = a_taglari.map(a => a.href).filter(href => href.includes('/ilan/'));
                    return [...new Set(hrefler)];
                }''')

                if not ilan_linkleri:
                    print("⚠️ Bu sayfada link bulunamadı, son sayfa olabilir veya yapı değişti.")
                    break

                for link in ilan_linkleri:
                    if islenen_ilan_sayisi >= hedef_ilan: break

                    ilan_numarasi = link.split('/')[-2].split('-')[-1]
                    benzersiz_kimlik = f"sahibinden.com_{ilan_numarasi}"

                    if benzersiz_kimlik in mevcut_ilanlar:
                        print(f"⏭️ [Atlandı] İlan zaten veritabanında mevcut: {ilan_numarasi}")
                        islenen_ilan_sayisi += 1
                        continue

                    print(f"\n[{islenen_ilan_sayisi+1}/{'Sınırsız' if hedef_ilan == 9999999 else hedef_ilan}] İlan Çekiliyor: {ilan_numarasi}")
                    await page.goto(link, timeout=60000)
                    
                    ilan_bekleme = random.uniform(12, 25)
                    await page.wait_for_timeout(ilan_bekleme * 1000) 

                    detay_verisi = await page.evaluate('''() => {
                        const veri = {};
                        const fiyatElement = document.querySelector('.classifiedInfo h3');
                        if (fiyatElement) veri['Fiyat'] = fiyatElement.innerText.trim();

                        const listeElemanlari = document.querySelectorAll('ul.classifiedInfoList li');
                        listeElemanlari.forEach(li => {
                            const baslikElement = li.querySelector('strong');
                            const degerElement = li.querySelector('span');
                            if (baslikElement && degerElement) {
                                const baslik = baslikElement.innerText.replace(':', '').trim();
                                const deger = degerElement.innerText.trim();
                                if (baslik.length > 0 && deger.length > 0) {
                                    veri[baslik] = deger;
                                }
                            }
                        });
                        return veri;
                    }''')

                    try:
                        df = pd.DataFrame([detay_verisi])
                        def guvenli_getir(olasi_isimler): 
                            for isim in olasi_isimler:
                                if isim in df.columns: return df[isim].iloc[0]
                            return ""

                        ham_fiyat = str(guvenli_getir(['Fiyat']))
                        temiz_fiyat = "".join([c for c in ham_fiyat if c.isdigit()])

                        ham_yakit = str(guvenli_getir(['Yakıt', 'Yakıt Tipi'])).lower()
                        if 'dizel' in ham_yakit: temiz_yakit = 'Dizel'
                        elif 'benzin' in ham_yakit or 'lpg' in ham_yakit: temiz_yakit = 'Benzin'
                        elif 'elektrik' in ham_yakit: temiz_yakit = 'Elektrik'
                        elif 'hibrit' in ham_yakit or 'hybrid' in ham_yakit: temiz_yakit = 'Hibrit'
                        else: temiz_yakit = 'Benzin'

                        ham_vites = str(guvenli_getir(['Vites', 'Vites Tipi'])).lower()
                        if 'otomatik' in ham_vites: temiz_vites = 'Otomatik'
                        else: temiz_vites = 'Manuel'

                        yeni_kayit = pd.DataFrame([{
                            'ilan_no': str(ilan_numarasi),
                            'site': 'sahibinden.com',
                            'yil': guvenli_getir(['Yıl']),
                            'marka': guvenli_getir(['Marka']),
                            'model': guvenli_getir(['Seri']), 
                            'km': str(guvenli_getir(['KM', 'Kilometre'])).replace('.', '').replace(' km', '').strip(),
                            'yakit': temiz_yakit,
                            'vites': temiz_vites,
                            'fiyat': temiz_fiyat,
                            'kaynak': 'gercek',
                            'veri_tipi': 'scrape_edilmis'
                        }])

                        cekilen_marka = str(yeni_kayit['marka'].iloc[0]).strip()
                        cekilen_fiyat = str(yeni_kayit['fiyat'].iloc[0]).strip()

                        if cekilen_marka != "" and cekilen_fiyat != "":
                            # 1. CSV'ye Kaydet
                            yeni_kayit.to_csv(ana_veritabani_dosyasi, mode='a', header=csv_header, index=False, encoding="utf-8-sig")
                            csv_header = False 
                            
                            # 2. Supabase'e Gönder
                            if supabase:
                                try:
                                    kayit_dict = yeni_kayit.where(pd.notnull(yeni_kayit), None).to_dict(orient="records")[0]
                                    supabase.table("ilanlar").upsert(kayit_dict, on_conflict="ilan_no,site").execute()
                                except Exception as sp_err:
                                    print(f"   ❌ Supabase kayıt hatası: {sp_err}")
                                    logging.error(f"Supabase kayıt hatası: {sp_err}")

                            mevcut_ilanlar.add(benzersiz_kimlik)
                            eklenen_yeni_ilan += 1
                            son_eklenen_ilan = f"İlan No: {ilan_numarasi} ({cekilen_marka} {yeni_kayit['model'].iloc[0]})"
                            
                            print(f"   ✅ Eklendi: {cekilen_marka} {yeni_kayit['model'].iloc[0]} ({cekilen_fiyat} TL)")
                            logging.info(f"YENİ KAYIT (Sahibinden): {son_eklenen_ilan}")
                        else:
                            print(f"   ⚠️ Eksik veri sebebiyle atlandı.")

                    except Exception as e:
                        print(f"   ❌ Kayıt hatası: {e}")

                    islenen_ilan_sayisi += 1

                offset += 20 

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if "Target page, context or browser has been closed" not in str(e):
                print(f"❌ Bir hata oluştu: {e}")
        finally:
            print("\n🏁 İŞLEM TAMAMLANDI VEYA DURDURULDU!")
            print(f"📊 Taranan İlan: {islenen_ilan_sayisi} | Yeni Eklenen: {eklenen_yeni_ilan}")
            logging.info(f"BOT DURDU. Son başarıyla eklenen: {son_eklenen_ilan}")
            
            if 'page' in locals():
                try: await page.close()
                except: pass

if __name__ == "__main__":
    try:
        asyncio.run(sahibinden_otonom_scraper())
    except KeyboardInterrupt:
        print("\n🛑 Kullanıcı tarafından zorla durduruldu! (Ctrl+C)")