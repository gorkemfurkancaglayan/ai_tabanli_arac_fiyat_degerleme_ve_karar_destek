import pandas as pd
import uuid

print("🔄 Ana veritabanı yeni şablona (ilan_no ve site) güncelleniyor...")

# Mevcut ana verimizi okuyalım
df = pd.read_csv('arac_verisi.csv')

# Yeni 'site' sütunu (Eski veriler için 'manuel_ekleme' diyelim)
df['site'] = 'manuel_ekleme'

# Yeni 'ilan_no' sütunu (Eski verilerin ilan nosu olmadığı için rastgele benzersiz ID atıyoruz)
# Böylece modelimiz bunların hepsini ayrı birer araç olarak görmeye devam edecek.
df['ilan_no'] = [str(uuid.uuid4())[:8] for _ in range(len(df))]

# Sütunları mükemmel bir sıraya koyalım (ID ve Site en başta olsun)
yeni_sira = ['ilan_no', 'site', 'yil', 'marka', 'model', 'km', 'yakit', 'vites', 'fiyat', 'kaynak', 'veri_tipi']
df = df[yeni_sira]

# Ana dosyamızı güncelleyip kaydedelim
df.to_csv('arac_verisi.csv', index=False, encoding="utf-8-sig")
print("✅ arac_verisi.csv başarıyla güncellendi! Artık otonom scraper için hazır.")