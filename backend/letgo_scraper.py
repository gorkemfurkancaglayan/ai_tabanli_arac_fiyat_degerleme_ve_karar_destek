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
log_dosyasi = "letgo_log.txt"
logging.basicConfig(
    filename=log_dosyasi, 
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    encoding='utf-8'
)

async def letgo_otonom_scraper():
    print("\n========================================")
    print(" 🕵️ LETGO.COM OTONOM VERİ AVCISI (ÇİFT SEKME & SINIRSIZ MOD) ")
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
            df_mevcut['ilan_no'] = df_mevcut['ilan_no'].astype(str)
            mevcut_ilanlar = set(df_mevcut['site'] + "_" + df_mevcut['ilan_no'])
            print(f"📚 Veritabanında {len(mevcut_ilanlar)} adet kayıtlı araç hafızaya alındı.")
        except Exception as e:
            logging.error(f"Veritabanı okunurken hata: {e}")

    csv_header = not os.path.exists(ana_veritabani_dosyasi)
    son_eklenen_ilan = "Henüz eklenen olmadı"
    
    eklenen_yeni_ilan = 0 
    islenen_ilan_sayisi = 0
    bu_oturumda_ziyaret_edilen_linkler = set() 

    async with Stealth().use_async(async_playwright()) as p:
        try:
            browser = await p.chromium.launch(headless=False) 
            context = await browser.new_context(
                viewport={'width': 1920, 'height': 1080},
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            )
            
            ana_sayfa = await context.new_page()
            detay_sayfasi = await context.new_page()

            hedef_url = "https://www.letgo.com/arabalar_c15706"
            print("🌐 Letgo Ana Arabalar sekmesi açılıyor (Burası hiç kapanmayacak)...")
            await ana_sayfa.goto(hedef_url, timeout=60000)
            
            while islenen_ilan_sayisi < hedef_ilan:
                
                print("⏳ Ana sayfa aşağı kaydırılıyor (Yeni ilanlar aranıyor)...")
                for _ in range(5):
                    await ana_sayfa.mouse.wheel(0, 3000)
                    await ana_sayfa.wait_for_timeout(random.uniform(1.5, 3) * 1000)
                    
                    try:
                        tiklandi = await ana_sayfa.evaluate('''() => {
                            const butonlar = Array.from(document.querySelectorAll('button'));
                            const yukleButonu = butonlar.find(b => b.innerText && b.innerText.toLowerCase().includes('daha fazla'));
                            if (yukleButonu && !yukleButonu.disabled && yukleButonu.offsetParent !== null) {
                                yukleButonu.click();
                                return true;
                            }
                            return false;
                        }''')
                        
                        if tiklandi:
                            print("   🖱️ 'Daha fazla yükle' butonuna basıldı, ilan akışı devam ediyor...")
                            await ana_sayfa.wait_for_timeout(random.uniform(2, 4) * 1000)
                    except:
                        pass

                print("🔗 Sayfadaki linkler toplanıyor...")
                ilan_linkleri = await ana_sayfa.evaluate('''() => {
                    const a_taglari = Array.from(document.querySelectorAll('a'));
                    const hrefler = a_taglari.map(a => a.href).filter(href => href.includes('/item/'));
                    return [...new Set(hrefler)];
                }''')

                if not ilan_linkleri:
                    print("⚠️ Link bulunamadı. Sayfa sonuna gelinmiş veya bot engellenmiş olabilir.")
                    await ana_sayfa.wait_for_timeout(5000)
                    continue

                yeni_linkler = [link for link in ilan_linkleri if link not in bu_oturumda_ziyaret_edilen_linkler]
                
                if not yeni_linkler:
                    print("🔄 Ekranda yeni ilan yok, daha fazla aşağı kaydırılıyor...")
                    continue

                print(f"🎯 Ekranda {len(yeni_linkler)} adet YENİ potansiyel ilan bulundu.")

                for i, link in enumerate(yeni_linkler, 1):
                    if islenen_ilan_sayisi >= hedef_ilan: break

                    bu_oturumda_ziyaret_edilen_linkler.add(link)
                    ilan_numarasi = link.split('-iid-')[-1].replace('/', '') if '-iid-' in link else link.split('/')[-1]
                    benzersiz_kimlik = f"letgo.com_{ilan_numarasi}"

                    if benzersiz_kimlik in mevcut_ilanlar:
                        print(f"⏭️ [Atlandı] İlan zaten veritabanında mevcut: {ilan_numarasi}")
                        islenen_ilan_sayisi += 1
                        continue

                    print(f"\n[{islenen_ilan_sayisi+1}/{'Sınırsız' if hedef_ilan == 9999999 else hedef_ilan}] İkinci Sekmede Çekiliyor: {ilan_numarasi}")
                    
                    try:
                        await detay_sayfasi.goto(link, timeout=60000)
                        await detay_sayfasi.wait_for_timeout(random.uniform(4, 7) * 1000) 

                        detay_verisi = await detay_sayfasi.evaluate('''() => {
                            const veri = {};
                            const bodyMetni = document.body.innerText;
                            
                            const fiyatArama = bodyMetni.match(/([0-9.,]+)\s*(TL|₺)/i);
                            if (fiyatArama) veri['Fiyat'] = fiyatArama[0];

                            const satirlar = bodyMetni.split('\\n').map(s => s.trim()).filter(s => s !== '');
                            const etiketler = ['Marka', 'Model', 'Yıl', 'Kilometre', 'KM', 'Vites', 'Vites Kutusu', 'Vites Tipi', 'Yakıt', 'Yakıt Tipi'];
                            
                            for (let j = 0; j < satirlar.length - 1; j++) {
                                let temizSatir = satirlar[j].replace(':', '').trim();
                                if (etiketler.includes(temizSatir)) {
                                    veri[temizSatir] = satirlar[j + 1];
                                }
                            }

                            if (!veri['Vites'] && !veri['Vites Kutusu'] && !veri['Vites Tipi']) {
                                if (/otomatik|edc|dsg|cvt|tronic/i.test(bodyMetni)) {
                                    veri['Vites'] = 'Otomatik';
                                } else if (/manuel|düz\s*vites/i.test(bodyMetni)) {
                                    veri['Vites'] = 'Manuel';
                                }
                            }
                            return veri;
                        }''')

                        df = pd.DataFrame([detay_verisi])
                        def guvenli_getir(olasi_isimler): 
                            for isim in olasi_isimler:
                                if isim in df.columns: return df[isim].iloc[0]
                            return ""

                        ham_fiyat = str(guvenli_getir(['Fiyat']))
                        temiz_fiyat = "".join([c for c in ham_fiyat if c.isdigit()])

                        ham_yakit = str(guvenli_getir(['Yakıt', 'Yakıt Tipi'])).lower()
                        temiz_yakit = ""
                        if 'dizel' in ham_yakit: temiz_yakit = 'Dizel'
                        elif 'benzin' in ham_yakit or 'lpg' in ham_yakit: temiz_yakit = 'Benzin'
                        elif 'elektrik' in ham_yakit: temiz_yakit = 'Elektrik'
                        elif 'hibrit' in ham_yakit or 'hybrid' in ham_yakit: temiz_yakit = 'Hibrit'

                        ham_vites = str(guvenli_getir(['Vites', 'Vites Tipi', 'Vites Kutusu'])).lower()
                        temiz_vites = ""
                        if 'otomatik' in ham_vites or 'yarı otomatik' in ham_vites: temiz_vites = 'Otomatik'
                        elif 'manuel' in ham_vites or 'düz' in ham_vites: temiz_vites = 'Manuel'

                        yeni_kayit = pd.DataFrame([{
                            'ilan_no': str(ilan_numarasi),
                            'site': 'letgo.com',
                            'yil': guvenli_getir(['Yıl']),
                            'marka': guvenli_getir(['Marka']),
                            'model': guvenli_getir(['Model']), 
                            'km': str(guvenli_getir(['Kilometre', 'KM'])).replace('.', '').replace(' km', '').strip(),
                            'yakit': temiz_yakit,
                            'vites': temiz_vites,
                            'fiyat': temiz_fiyat,
                            'kaynak': 'gercek',
                            'veri_tipi': 'scrape_edilmis'
                        }])

                        cekilen_marka = str(yeni_kayit['marka'].iloc[0]).strip()
                        cekilen_fiyat = str(yeni_kayit['fiyat'].iloc[0]).strip()
                        cekilen_km = str(yeni_kayit['km'].iloc[0]).strip()
                        cekilen_vites = str(yeni_kayit['vites'].iloc[0]).strip()

                        if cekilen_marka != "" and cekilen_fiyat != "" and cekilen_km != "" and cekilen_vites != "":
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
                            son_eklenen_ilan = f"İlan No: {ilan_numarasi} ({cekilen_marka} {yeni_kayit['model'].iloc[0]} - {cekilen_vites})"
                            
                            print(f"   ✅ Eklendi: {cekilen_marka} {yeni_kayit['model'].iloc[0]} ({cekilen_fiyat} TL, {cekilen_vites})")
                            logging.info(f"YENİ KAYIT (Letgo): {son_eklenen_ilan}")
                        else:
                            print(f"   ⚠️ Eksik veri sebebiyle atlandı. (Marka, Fiyat, KM veya Vites okunamadı)")

                    except Exception as e:
                        print(f"   ❌ Kayıt hatası (İlan atlandı): {e}")

                    islenen_ilan_sayisi += 1

        except asyncio.CancelledError:
            pass
        except Exception as e:
            if "Target page, context or browser has been closed" not in str(e):
                print(f"❌ Bir hata oluştu: {e}")
        finally:
            print("\n🏁 LETGO İŞLEMİ TAMAMLANDI!")
            print(f"📊 Taranan İlan: {islenen_ilan_sayisi} | Yeni Eklenen: {eklenen_yeni_ilan}")
            
            try:
                if browser: await browser.close()
            except: pass

if __name__ == "__main__":
    try:
        asyncio.run(letgo_otonom_scraper())
    except KeyboardInterrupt:
        print("\n🛑 Kullanıcı tarafından zorla durduruldu! (Ctrl+C)")