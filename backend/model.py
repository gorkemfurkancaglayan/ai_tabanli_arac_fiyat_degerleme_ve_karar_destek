import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.preprocessing import LabelEncoder

# ========================
# VERİ KAYNAĞI SEÇİMİ
# ========================
print("\n========================================")
print("       İKİNCİ EL ARAÇ FİYAT TAHMİN      ")
print("========================================")
print("\nHangi verilerle çalışmak istiyorsunuz?")
print("  1 - Karma       (sentetik + gerçek)")
print("  2 - Sadece Sentetik")
print("  3 - Sadece Gerçek")
print("========================================")
veri_secim = input("Seçiminiz (1/2/3): ").strip()

veri_map = {"1": "karma", "2": "sentetik", "3": "gercek"}
if veri_secim not in veri_map:
    print("Geçersiz seçim, karma mod ile devam ediliyor.")
    veri_secim = "1"
veri_modu = veri_map[veri_secim]

# ========================
# VERİYİ HAZIRLA
# ========================
df_tum = pd.read_csv("arac_verisi.csv")

if veri_modu == "sentetik":
    df = df_tum[df_tum["kaynak"] == "sentetik"].copy()
elif veri_modu == "gercek":
    df = df_tum[df_tum["kaynak"] == "gercek"].copy()
else:
    df = df_tum.copy()

df = df.reset_index(drop=True)
df_gosterim = df.copy()

print(f"\nKullanılan veri: {len(df)} araç ({veri_modu} mod)")

if len(df) < 10:
    print("⚠️  Uyarı: Veri sayısı çok az, tahminler güvenilir olmayabilir.")

# Kategorik verileri sayılara dönüştür
encoders = {}
for sutun in ["marka", "model", "yakit", "vites"]:
    le = LabelEncoder()
    df[sutun] = le.fit_transform(df[sutun])
    encoders[sutun] = le

# ==========================================
# 🚀 ÇÖZÜM: SADECE ÖZELLİKLERİ (FEATURES) SEÇ
# ==========================================
# İlan no, site, kaynak gibi ML'in anlamayacağı metinleri dışarıda bırakıyoruz
features = ["marka", "model", "yil", "km", "yakit", "vites"]
X = df[features]
y = df["fiyat"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

# ========================
# MENÜ
# ========================
print("\n========================================")
print("       İKİNCİ EL ARAÇ FİYAT TAHMİN      ")
print("========================================")
print(f"Toplam veri: {len(df)} araç")
print("\n1 - Otomatik Test (veri setinin %20'si)")
print("2 - Manuel Araç Girişi")
print("========================================")
secim = input("Seçiminiz (1 veya 2): ").strip()

# ========================
# SEÇİM 1: OTOMATİK TEST
# ========================
if secim == "1":
    tahminler = model.predict(X_test)
    hata = mean_absolute_error(y_test, tahminler)
    r2 = r2_score(y_test, tahminler) # Başarı oranını (R2) da ekledik

    print(f"\nModel Başarı Oranı (R2): %{r2 * 100:.2f}")
    print(f"Ortalama Hata Payı: ±{hata:,.0f} TL")
    print(f"Test edilen araç sayısı: {len(X_test)}")
    print("\n--- Tahmin Sonuçları (İlk 10 Araç) ---")

    # Çok fazla veri olduğu için sadece ilk 10 tanesini ekrana basalım
    for i, (gercek, tahmin) in enumerate(zip(y_test[:10], tahminler[:10])):
        idx = X_test.index[i]
        marka = df_gosterim["marka"].iloc[idx]
        model_adi = df_gosterim["model"].iloc[idx]
        yil = df_gosterim["yil"].iloc[idx]
        km = df_gosterim["km"].iloc[idx]
        print(f"\n  Araç    : {marka} {model_adi} - Yıl: {yil} - KM: {km:,}")
        print(f"  Gerçek  : {gercek:>10,.0f} TL")
        print(f"  Tahmin  : {tahmin:>10,.0f} TL")
        print(f"  Fark    : {abs(gercek-tahmin):>10,.0f} TL")
        print(f"  {'-'*40}")

# ========================
# SEÇİM 2: MANUEL GİRİŞ
# ========================
elif secim == "2":
    print("\n--- Araç Bilgilerini Girin ---")
    print("(Büyük/küçük harf önemli değil)\n")

    marka = input("Marka (örn: Hyundai): ").strip().title()
    model_adi = input("Model (örn: Accent Blue): ").strip().upper() # Model adını databasedeki gibi büyüttük
    yil = int(input("Yıl (örn: 2019): "))
    km = int(input("Kilometre (örn: 75000): "))

    print("\nYakıt Tipi:")
    print("  1. Benzin")
    print("  2. Dizel")
    print("  3. Hibrit")
    print("  4. Elektrik")
    yakit_secim = input("Seçiminiz (1/2/3/4): ").strip()
    yakit_map = {"1": "Benzin", "2": "Dizel", "3": "Hibrit", "4": "Elektrik"}
    yakit = yakit_map.get(yakit_secim, "Benzin")

    print("\nVites Tipi:")
    print("  1. Manuel")
    print("  2. Otomatik")
    vites_secim = input("Seçiminiz (1/2): ").strip()
    vites_map = {"1": "Manuel", "2": "Otomatik"}
    vites = vites_map.get(vites_secim, "Otomatik")

    marka_bilindi = marka in df_gosterim["marka"].values
    model_bilindi = model_adi in df_gosterim["model"].values

    try:
        marka_enc = encoders["marka"].transform([marka])[0]
        model_enc = encoders["model"].transform([model_adi])[0]
    except:
        marka_enc = 0
        model_enc = 0

    yakit_enc = encoders["yakit"].transform([yakit])[0]
    vites_enc = encoders["vites"].transform([vites])[0]

    girdi = pd.DataFrame([[marka_enc, model_enc, yil, km, yakit_enc, vites_enc]],
                         columns=["marka", "model", "yil", "km", "yakit", "vites"])

    tahmin = model.predict(girdi)[0]

    print(f"\n========================================")
    print(f"  {marka} {model_adi} | {yil} | {km:,} KM | {yakit} | {vites}")
    print(f"  Tahmini Fiyat: {tahmin:,.0f} TL")

    if not marka_bilindi:
        print(f"\n  ⚠️  '{marka}' markası veri setinde yok.")
    elif not model_bilindi:
        print(f"\n  ⚠️  '{model_adi}' modeli veri setinde yok.")

    print(f"========================================")