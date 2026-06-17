# Arac Asistan

---

## Klasör Yapısı

```
arac_asistan/
├── templates/
│   └── index.html              ← Denemelik basit arayüz
├── arac_verisi.csv             ← Ana veritabanı - çeşitli sitelerden veriler - sentetik/gerçek, elle_girilmis/scrape_edilmis gibi vs.
├── predictor.py                ← RandomForest ML Modeli
├── app.py                      ← Flask & WebSocket Sunucusu
├── model.py                    ← ML modeli basit hali ilk versiyon
├── arabam_scraper.py           ← Arabam.com için özelleştirilmiş otonom scraper
├── arabam_log.txt              ← Arabam.com scraper logları
├── sahibinden_log.txt          ← Sahibinden.com scraper logları
└── sahibinden_scraper.py       ← Sahibinden.com için özelleştirilmiş otonom scraper
```

---

## Kurulum

Sanal ortam kurmak için

```bash
python -m venv venv
```

Sanal ortamı aktif etmek için

```bash
venv\Scripts\activate
```

Gerekli kütüphanelerin kurulumu

```bash
pip install flask scikit-learn pandas flask-socketio eventlet flask-cors playwright playwright-stealth
```

Veri çekmede kullanmak için chromium

```bash
playwright install chromium
```

Basit LLM denemesi için

```bash
pip install groq
```

## Kullanım

ilk versiyon modeli kullanmak için

```bash
python model.py
```

Arayüze entegre Modeli kullanmak için

```bash
python app.py
```

Arabam.com scraper'ını kullanmak için

```bash
python arabam_scraper.py
```

Sahibinden scraper'ını kullanmak için bu sitede güvenlik biraz fazla olduğu için önce
IDE üzerinden değil normal çalıştır > cmd yazıp bir command prompt aç ve alttakini yapıştır
sonrasında açılan google sekmesini kapatma(Google'ın kurulu olduğu yer sendede aynı ise düzgün çalışması lazım.)

```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="C:\localhost_chrome"
```

Sahibinden scraper'ını kullanmak için

```bash
python sahibinden_scraper.py
```

Sahibindende güvenlik yine fazla olduğu için örneğin robot'musunuz gibi doğrulamalar isterse elle manuel tıkla açılan sekmede veya giriş yapın derse CMD kullanarak açtığımız
google sekmesinden sahibinden.com'a giriş yap herhangi bir hesaptan sonrasında tekrar çalıştır scraper'ı.