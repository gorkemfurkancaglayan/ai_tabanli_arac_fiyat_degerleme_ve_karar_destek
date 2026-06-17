import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
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
log_dosyasi = "otokoc_log.txt"
logging.basicConfig(
    filename=log_dosyasi, 
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

async def otokoc_otonom_scraper():
    print("\n========================================")
    print(" 🏢 OTOKOÇ OTONOM VERİ AVCISI (SAF TABLO & İKON MODU) ")
    print("========================================")
    print("Kaç adet ilan taramak istersiniz?")
    print("  1 - 5 İlan (Hızlı Test)")
    print("  2 - 20 İlan")
    print("  3 - 100 İlan")
    print("  4 - SINIRSIZ")
    print("========================================")
    secim = input("Seçiminiz (1/2/3/4): ").strip()
    
    hedef_ilan = 0
    if secim == "1": hedef_ilan = 5
    elif secim == "2": hedef_ilan = 20
    elif secim == "3": hedef_ilan = 100
    elif secim == "4": hedef_ilan = 9999999
    else: 
        hedef_ilan = 5

    mevcut_ilanlar = set()
    ana_veritabani_dosyasi = 'arac_verisi.csv'
    
    if os.path.exists(ana_veritabani_dosyasi):
        try:
            df_mevcut = pd.read_csv(ana_veritabani_dosyasi)
            df_mevcut['ilan_no'] = df_mevcut['ilan_no'].astype(str).str.strip()
            mevcut_ilanlar = set(df_mevcut['ilan_no'])
            print(f"📚 Veritabanında {len(mevcut_ilanlar)} adet kayıtlı araç hafızaya alındı.")
        except Exception as e:
            logging.error(f"Veritabanı okunurken hata: {e}")

    csv_header = not os.path.exists(ana_veritabani_dosyasi)
    son_eklenen_ilan = "Henüz eklenen olmadı"
    
    eklenen_yeni_ilan = 0 
    islenen_ilan_sayisi = 0
    sayfa_no = 1

    async with Stealth().use_async(async_playwright()) as p:
        try:
            browser = await p.chromium.launch(headless=False) 
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            page = await context.new_page()

            while eklenen_yeni_ilan < hedef_ilan:
                url = f"https://www.otokocikinciel.com/ikinci-el-araba?advertiserTypeName=otokoc-2-el&page={sayfa_no}"
                print(f"\n🌐 Otokoç Sayfa {sayfa_no} açılıyor...")
                await page.goto(url, timeout=60000)
                await page.wait_for_timeout(random.uniform(4, 7) * 1000)

                ilan_linkleri = await page.evaluate('''() => {
                    const a_taglari = Array.from(document.querySelectorAll('a'));
                    const hrefler = a_taglari.map(a => a.href).filter(href => href.includes('/ilan/'));
                    return [...new Set(hrefler)];
                }''')

                if not ilan_linkleri:
                    print("⚠️ Bu sayfada ilan bulunamadı veya son sayfaya gelindi.")
                    break

                print(f"🎯 Sayfa {sayfa_no}'da Toplam {len(ilan_linkleri)} adet potansiyel ilan bulundu.")

                for i, link in enumerate(ilan_linkleri, 1):
                    if eklenen_yeni_ilan >= hedef_ilan: break

                    ilan_numarasi = link.split('/')[-1].split('?')[0].split('-')[-1].strip()

                    if ilan_numarasi in mevcut_ilanlar:
                        print(f"⏭️ [Atlandı] İlan zaten veritabanında kayıtlı: {ilan_numarasi}")
                        continue

                    print(f"\n[{eklenen_yeni_ilan+1}/...] İlan Çekiliyor: {ilan_numarasi}")
                    await page.goto(link, timeout=60000)
                    await page.wait_for_timeout(random.uniform(3, 5) * 1000) 

                    await page.mouse.wheel(0, 500)
                    await page.wait_for_timeout(1000)

                    try:
                        await page.evaluate('''() => {
                            const elements = Array.from(document.querySelectorAll('div, span, button, h2, h3'));
                            const detayBtn = elements.find(el => el.innerText && el.innerText.trim() === 'Detaylar');
                            if (detayBtn) detayBtn.click();
                        }''')
                        await page.wait_for_timeout(1500) 
                    except:
                        pass

                    detay_verisi = await page.evaluate('''() => {
                        const veri = {};
                        const bodyMetni = document.body.innerText;

                        const fiyatArama = bodyMetni.match(/([0-9.,]+)\s*(TL|₺)/i);
                        if (fiyatArama) veri['Fiyat'] = fiyatArama[0];

                        const satirlar = bodyMetni.split('\\n').map(s => s.trim()).filter(s => s !== '');
                        let kmIndex = -1;
                        
                        for (let j = 0; j < satirlar.length; j++) {
                            if (satirlar[j].length < 25 && /([0-9.,]+)\s*km/i.test(satirlar[j])) {
                                const kmMatch = satirlar[j].match(/([0-9.,]+)\s*km/i);
                                veri['KM'] = kmMatch[1];
                                kmIndex = j;
                                break;
                            }
                        }

                        if (kmIndex !== -1) {
                            const baslangic = Math.max(0, kmIndex - 2);
                            const bitis = Math.min(satirlar.length, kmIndex + 4);
                            const cevreSatirlar = satirlar.slice(baslangic, bitis);

                            cevreSatirlar.forEach(satir => {
                                const s = satir.toLowerCase();
                                if (s === 'otomatik' || s === 'yarı otomatik') veri['Vites'] = 'Otomatik';
                                else if (s === 'manuel' || s === 'düz') veri['Vites'] = 'Manuel';

                                if (s === 'dizel') veri['Yakıt'] = 'Dizel';
                                else if (s === 'benzin') veri['Yakıt'] = 'Benzin';
                                else if (s === 'hibrit' || s === 'hybrid') veri['Yakıt'] = 'Hibrit';
                                else if (s === 'elektrik') veri['Yakıt'] = 'Elektrik';
                            });
                        }

                        const tumElementler = Array.from(document.querySelectorAll('div, span, p, li, td, th')).filter(el => {
                            return el.textContent && el.textContent.trim().length > 0 && el.textContent.trim().length < 40;
                        });

                        for(let k = 0; k < tumElementler.length - 1; k++) {
                            let key = tumElementler[k].textContent.replace(':', '').trim();
                            let val = tumElementler[k+1].textContent.trim();

                            const arananlar = ['Marka', 'Model', 'Model Yılı', 'Yıl'];

                            if (arananlar.includes(key) && !veri[key] && val !== key) {
                                if (val.length < 30) {
                                    veri[key] = val.split('\\n')[0].trim();
                                }
                            }
                        }

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

                        ham_yakit = str(guvenli_getir(['Yakıt'])).lower()
                        temiz_yakit = ""
                        if 'dizel' in ham_yakit: temiz_yakit = 'Dizel'
                        elif 'benzin' in ham_yakit or 'lpg' in ham_yakit: temiz_yakit = 'Benzin'
                        elif 'hibrit' in ham_yakit or 'hybrid' in ham_yakit: temiz_yakit = 'Hibrit'
                        elif 'elektrik' in ham_yakit: temiz_yakit = 'Elektrik'

                        ham_vites = str(guvenli_getir(['Vites'])).lower()
                        temiz_vites = ""
                        if 'otomatik' in ham_vites or 'yarı otomatik' in ham_vites: temiz_vites = 'Otomatik'
                        elif 'manuel' in ham_vites or 'düz' in ham_vites: temiz_vites = 'Manuel'

                        yeni_kayit = pd.DataFrame([{
                            'ilan_no': str(ilan_numarasi),
                            'site': 'otokoc.com',
                            'yil': str(guvenli_getir(['Yıl', 'Model Yılı'])).strip(),
                            'marka': str(guvenli_getir(['Marka'])).strip().capitalize(), 
                            'model': str(guvenli_getir(['Model'])).strip().upper(),      
                            'km': str(guvenli_getir(['KM'])).replace('.', '').replace(' km', '').strip(),
                            'yakit': temiz_yakit,
                            'vites': temiz_vites,
                            'fiyat': temiz_fiyat,
                            'kaynak': 'gercek',
                            'veri_tipi': 'scrape_edilmis'
                        }])

                        cekilen_marka = str(yeni_kayit['marka'].iloc[0]).strip()
                        cekilen_model = str(yeni_kayit['model'].iloc[0]).strip()
                        cekilen_fiyat = str(yeni_kayit['fiyat'].iloc[0]).strip()
                        cekilen_km = str(yeni_kayit['km'].iloc[0]).strip()
                        cekilen_vites = str(yeni_kayit['vites'].iloc[0]).strip()
                        cekilen_yil = str(yeni_kayit['yil'].iloc[0]).strip()
                        cekilen_yakit = str(yeni_kayit['yakit'].iloc[0]).strip()

                        if cekilen_marka != "" and cekilen_fiyat != "" and cekilen_km != "" and cekilen_vites != "" and cekilen_yil != "" and cekilen_yakit != "":
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

                            mevcut_ilanlar.add(ilan_numarasi)
                            eklenen_yeni_ilan += 1
                            son_eklenen_ilan = f"{cekilen_yil} {cekilen_marka} {cekilen_model} ({cekilen_yakit}, {cekilen_vites})"
                            
                            print(f"   ✅ Eklendi: {cekilen_yil} {cekilen_marka} {cekilen_model} ({cekilen_fiyat} TL, {cekilen_km} KM, {cekilen_yakit}, {cekilen_vites})")
                            logging.info(f"YENİ KAYIT (Otokoç): {son_eklenen_ilan}")
                        else:
                            print(f"   ⚠️ Eksik veri sebebiyle atlandı.")

                    except Exception as e:
                        print(f"   ❌ Kayıt hatası: {e}")

                    islenen_ilan_sayisi += 1

                sayfa_no += 1 

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if "Target page, context or browser has been closed" not in str(e):
                print(f"❌ Bir hata oluştu: {e}")
        finally:
            print("\n🏁 OTOKOÇ İŞLEMİ TAMAMLANDI!")
            print(f"📊 Toplam Taranan: {islenen_ilan_sayisi} | Yeni Eklenen Temiz İlan: {eklenen_yeni_ilan}")
            
            try:
                if browser: await browser.close()
            except: pass

if __name__ == "__main__":
    try:
        asyncio.run(otokoc_otonom_scraper())
    except KeyboardInterrupt:
        print("\n🛑 Kullanıcı tarafından zorla durduruldu! (Ctrl+C)")