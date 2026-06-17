import pandas as pd
import numpy as np

# Eski dosyanı oku
df = pd.read_csv('arac_verisi.csv')

# Yeni 'veri_tipi' sütununu oluştur.
# Eğer kaynak 'sentetik' ise 'ai_uretilen', değilse 'elle_girilmis' yapalım.
df['veri_tipi'] = np.where(df['kaynak'] == 'sentetik', 'ai_uretilen', 'elle_girilmis')

# Sütunları senin istediğin o temiz mantığa göre yeniden sırala
yeni_sira = ['yil', 'marka', 'model', 'km', 'yakit', 'vites', 'fiyat', 'kaynak', 'veri_tipi']
df = df[yeni_sira]

# Yeni dosya olarak kaydet
df.to_csv('arac_verisi.csv', index=False, encoding="utf-8-sig")
print("✅ Eski veriler başarıyla yeni şablona uyarlandı!")