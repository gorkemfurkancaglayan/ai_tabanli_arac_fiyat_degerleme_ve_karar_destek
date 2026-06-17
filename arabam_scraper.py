import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
import random
import pandas as pd
import os
import logging
from datetime import datetime
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
log_dosyasi = "scraper_log.txt"
logging.basicConfig(
    filename=log_dosyasi, 
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

async def arabam_com_detay_scraper():
    print("\n========================================")
    print(" 🤖 ARAÇ_ASİSTAN OTONOM VERİ TOPLAYICI ")
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

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=False) 
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = await context.new_page()

        islenen_ilan_sayisi = 0
        sayfa_no = 1
        eklenen_yeni_ilan = 0

        try:
            while islenen_ilan_sayisi < hedef_ilan:
                url = f"https://www.arabam.com/ikinci-el/otomobil?page={sayfa_no}"
                print(f"\n🌐 Sayfa {sayfa_no} açılıyor...")
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(random.uniform(4, 7) * 1000)

                ilan_linkleri = await page.evaluate('''() => {
                    const a_taglari = Array.from(document.querySelectorAll('.listing-list-item a'));
                    const hrefler = a_taglari.map(a => a.href).filter(href => href.includes('/ilan/'));
                    return [...new Set(hrefler)];
                }''')

                if not ilan_linkleri:
                    print("⚠️ Bu sayfada ilan bulunamadı veya son sayfaya gelindi.")
                    break

                for link in ilan_linkleri:
                    if islenen_ilan_sayisi >= hedef_ilan: break

                    ilan_numarasi = link.split('/')[-1].split('?')[0]
                    benzersiz_kimlik = f"arabam.com_{ilan_numarasi}"

                    if benzersiz_kimlik in mevcut_ilanlar:
                        print(f"⏭️ [Atlandı] İlan zaten veritabanında mevcut: {ilan_numarasi}")
                        islenen_ilan_sayisi += 1
                        continue

                    print(f"\n[{islenen_ilan_sayisi+1}/{'Sınırsız' if hedef_ilan == 9999999 else hedef_ilan}] İlan Çekiliyor: {ilan_numarasi}")
                    await page.goto(link, timeout=60000)
                    
                    await page.wait_for_timeout(random.uniform(3, 6) * 1000)

                    detay_verisi = await page.evaluate('''() => {
                        const veri = {};
                        
                        const fiyatElement = document.querySelector('.color-red4, .product-price, .price');
                        if (fiyatElement) veri['Fiyat'] = fiyatElement.innerText.trim();

                        const nodes = Array.from(document.querySelectorAll('span, p, div, a, h1, h2, h3, li, td, th')).filter(el => {
                            return el.innerText && el.innerText.trim().length > 0 && el.innerText.trim().length < 50;
                        });
                        
                        for(let i=0; i < nodes.length - 1; i++) {
                            let key = nodes[i].innerText.replace(':', '').trim();
                            let val = nodes[i+1].innerText.trim();
                            
                            const arananlar = ['Marka', 'Seri', 'Yıl', 'Kilometre', 'Yakıt Tipi', 'Vites Tipi'];
                            
                            if (arananlar.includes(key) && !veri[key] && val !== key) {
                                veri[key] = val;
                            }
                        }
                        
                        if (!veri['Fiyat']) {
                            const fiyatNode = nodes.find(n => n.innerText.includes(' TL'));
                            if (fiyatNode) veri['Fiyat'] = fiyatNode.innerText.trim();
                        }
                        
                        return veri;
                    }''')

                    try:
                        df = pd.DataFrame([detay_verisi])
                        def guvenli_getir(kolon): return df[kolon].iloc[0] if kolon in df.columns else ""

                        ham_fiyat = str(guvenli_getir('Fiyat'))
                        guncel_fiyat = ham_fiyat.split('\n')[-1] 
                        temiz_fiyat = "".join([c for c in guncel_fiyat if c.isdigit()])

                        yeni_kayit = pd.DataFrame([{
                            'ilan_no': str(ilan_numarasi),
                            'site': 'arabam.com',
                            'yil': guvenli_getir('Yıl'),
                            'marka': guvenli_getir('Marka'),
                            'model': guvenli_getir('Seri'),
                            'km': str(guvenli_getir('Kilometre')).replace('.', '').replace(' km', ''),
                            'yakit': str(guvenli_getir('Yakıt Tipi')).replace('LPG & Benzin', 'Benzin').replace('LPG', 'Benzin'),
                            'vites': str(guvenli_getir('Vites Tipi')).replace('Düz', 'Manuel').replace('Yarı Otomatik', 'Otomatik'),
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
                            logging.info(f"YENİ KAYIT: {son_eklenen_ilan}")
                        else:
                            sayfa_basligi = await page.title()
                            print(f"   ⚠️ Eksik veri sebebiyle atlandı.")
                            print(f"      ↳ Sorun: Marka='{cekilen_marka}', Fiyat='{cekilen_fiyat}'")
                            print(f"      ↳ Ekrandaki Başlık: {sayfa_basligi}")
                            logging.warning(f"Eksik veri: Marka='{cekilen_marka}', Fiyat='{cekilen_fiyat}' | İlan: {ilan_numarasi} | Başlık: {sayfa_basligi}")

                    except Exception as e:
                        print(f"   ❌ Kayıt hatası: {e}")
                        logging.error(f"İlan parse/kayıt hatası ({ilan_numarasi}): {e}")

                    islenen_ilan_sayisi += 1

                sayfa_no += 1
                
        except asyncio.CancelledError:
            pass 
        except Exception as e:
            if "Target page, context or browser has been closed" not in str(e):
                print(f"\n❌ Beklenmeyen Hata: {e}")
                logging.error(f"Beklenmeyen Hata: {e}")
        finally:
            print(f"\n🏁 İŞLEM TAMAMLANDI VEYA DURDURULDU!")
            print(f"📊 Taranan İlan: {islenen_ilan_sayisi} | Yeni Eklenen: {eklenen_yeni_ilan}")
            logging.info(f"BOT DURDU. Son başarıyla eklenen: {son_eklenen_ilan}")
            logging.info(f"Oturum Özeti - Taranan: {islenen_ilan_sayisi}, Eklenen: {eklenen_yeni_ilan}\n")
            
            try:
                if browser: await browser.close()
            except: pass

if __name__ == "__main__":
    try:
        asyncio.run(arabam_com_detay_scraper())
    except KeyboardInterrupt:
        print("\n🛑 Kullanıcı tarafından zorla durduruldu! (Ctrl+C)")
        logging.warning("Sistem Kullanıcı tarafından CTRL+C ile durduruldu.")