# AI Tabanlı Araç Fiyat Değerleme ve Karar Destek Sistemi

Bu proje, ikinci el araçların piyasa değerini makine öğrenmesi modeli ile tahmin eden ve yapay zekâ destekli analiz sunan bir karar destek sistemidir.

## Proje Yapısı

```
ai_tabanli_arac_fiyat_degerleme_ve_karar_destek
│
├── backend/
├── frontend/
└── README.md
```

---

# Kurulum

## 1. Repoyu klonlayın

```bash
git clone <repo_linki>
cd ai_tabanli_arac_fiyat_degerleme_ve_karar_destek
```

---

## 2. Backend

Backend klasörüne geçin.

```bash
cd backend
```

Gerekli Python kütüphanelerini yükleyin.

```bash
python -m pip install -r requirements.txt
```

Backend'i çalıştırın.

```bash
python app.py
```

Varsayılan olarak backend:

```
http://localhost:5000
```

adresinde çalışacaktır.

---

## 3. Frontend

Yeni bir terminal açın.

Frontend klasörüne geçin.

```bash
cd frontend
```

Node.js paketlerini yükleyin.

```bash
npm install
```

Frontend'i başlatın.

```bash
npm run dev
```

Ardından tarayıcıdan aşağıdaki adresi açın:

```
http://localhost:3000
```

---

## Gereksinimler

- Python 3.10 veya üzeri
- Node.js 18 veya üzeri
- npm
- Git

---

## Not

Backend çalışmadan frontend üzerinden fiyat tahmini ve yapay zekâ analizleri gerçekleştirilemez.

Backend ve frontend aynı anda çalıştırılmalıdır.