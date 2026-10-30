# CaseMarket

**React, FastAPI ve PostgreSQL ile geliştirilen çok satıcılı telefon kılıfı pazaryeri.**

CaseMarket, üniversite projesi kapsamında geliştirilen bir e-ticaret uygulamasıdır. Amaç; müşterilerin farklı mağazalardaki telefon kılıflarını keşfedebildiği, satıcıların kendi ürünlerini yönetebildiği ve ileride yöneticilerin siparişleri takip edebildiği bir pazaryeri oluşturmaktır.

> **Proje durumu:** Giriş/kayıt, ürün vitrini, sepet, demo sipariş ve satıcı ürün yönetiminin temel akışları geliştirildi. Gerçek ödeme, kargo/teslimat takibi, admin paneli ve canlı destek henüz tamamlanmadı.

### Hesap ve demo ödeme akışı

- **Hesabım** ekranında profil bilgileri, teslimat adresleri, demo kartın yalnızca görünen bilgileri, aktif siparişler ve tüm sipariş geçmişi bulunur. Satıcı hesabında panel girişi de bu ekrandadır.
- Sepette adres ve demo ödeme yöntemi seçilerek sipariş tamamlanır. Gerçek ödeme alınmaz; tam kart numarası ve güvenlik kodu saklanmaz. Canlı ödeme için ayrı bir ödeme sağlayıcısı entegrasyonu gerekir.
- Mevcut PostgreSQL veritabanını kullanan kurulumlarda bir kez `cd backend && python -m scripts.apply_account_migration` çalıştırılmalıdır. Yeni kurulumlarda `backend/schema.sql` bu alanları içerir.

## Mevcut Özellikler

### Müşteri ve Vitrin

- Premium ve responsive React arayüzü
- Herkese açık ürün kataloğu
- Ürün detay sayfası
- Ürün arama ve sıralama
- Stok durumuna göre filtreleme
- Gerçek ürün görselleri
- Örnek veri kümesinde 40 telefon kılıfı görseli
- Sepete ürün ekleme
- Sepette ürün adedi artırma ve azaltma
- Sepet toplam tutarını hesaplama
- Sepeti localStorage ile tarayıcıda saklama

### Kullanıcı Hesapları

- Kullanıcı kayıt ekranı
- Kullanıcı giriş ekranı
- Argon2 ile parola hashleme
- JWT tabanlı kimlik doğrulama
- Giriş yapan kullanıcının bilgilerini görüntüleme
- Customer ve Seller rolleri
- Kullanıcı rolüne göre arayüz gösterimi
- Oturum açma ve çıkış yapma

### Satıcı Yönetimi

- Satıcı hesabı ve mağaza oluşturma
- Satıcı paneline giriş
- Mağaza bilgilerini görüntüleme
- Toplam ürün sayısı
- Aktif ürün sayısı
- Toplam stok bilgisi
- Satıcının kendi ürünlerini listelemesi
- Yeni ürün oluşturma
- Ürüne görsel adresi ekleme
- Ürün fiyatını düzenleme
- Ürün stok miktarını değiştirme
- Ürünü yayından kaldırma
- Pasif ürünü tekrar yayına alma
- Backend tarafında mağaza sahipliği ve rol kontrolü

> **Devam eden çalışma:** Mevcut ürünün görselini değiştirme özelliğinde Pydantic şeması hazırlandı. SQL güncellemesi ve React düzenleme alanı henüz tamamlanmadı. Fiyat, stok ve görünürlük işlemlerinin uçtan uca testleri de sürüyor.

## Kullanılan Teknolojiler

| Katman | Teknolojiler |
| --- | --- |
| Frontend | React, JavaScript, JSX, Vite, CSS |
| Backend | Python, FastAPI, Pydantic |
| Veritabanı | PostgreSQL |
| Veritabanı bağlantısı | psycopg |
| Kimlik doğrulama | JWT, Argon2 |
| Geliştirme ortamı | Docker Compose, PyCharm |
| Versiyon kontrolü | Git, GitHub |

## Proje Yapısı

```text
casemarket/
├── backend/
│   ├── core/
│   │   └── # JWT ve yetkilendirme yardımcıları
│   ├── data/
│   │   └── # Örnek ürün verileri ve görsel kaynakları
│   ├── routers/
│   │   └── # FastAPI endpoint dosyaları
│   ├── schemas/
│   │   └── # Pydantic doğrulama modelleri
│   ├── scripts/
│   │   └── # Örnek veri ekleme scriptleri
│   ├── main.py
│   └── schema.sql
├── frontend/
│   ├── public/
│   │   └── products/
│   └── src/
│       ├── components/
│       │   ├── AuthPage.jsx
│       │   ├── SellerDashboard.jsx
│       │   └── SellerProductRow.jsx
│       ├── App.jsx
│       ├── App.css
│       └── index.css
├── compose.yaml
└── README.md
```

## Projeyi Yerel Ortamda Çalıştırma

### Gereksinimler

- Python 3.12
- Node.js ve npm
- Docker
- Docker Compose
- PostgreSQL (Docker üzerinden)

Bu komutlar mevcut geliştirme ortamı içindir. İlk kurulumda Python bağımlılıkları, `.env` ayarları ve veritabanı şemasının hazırlanması gerekir.

`.env.example` dosyası örnek alınabilir. Mevcut `.env` dosyasının üzerine yazılmamalıdır.

### 1. PostgreSQL'i Başlatma

Projenin ana klasöründe:

```bash
sudo docker compose up -d db
```

### 2. Backend'i Başlatma

Yeni terminal açın:

```bash
cd ~/PycharmProjects/casemarket

source .venv/bin/activate

cd backend

python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Backend API:

http://127.0.0.1:8000

Swagger API dokümantasyonu:

http://127.0.0.1:8000/docs

### 3. Frontend'i Başlatma

Başka bir terminal açın:

```bash
cd ~/PycharmProjects/casemarket/frontend

npm install

npm run dev
```

Frontend:

http://localhost:5173

Frontend varsayılan olarak `http://127.0.0.1:8000` adresindeki backend'e bağlanır.

Gerekirse `VITE_API_BASE_URL` ortam değişkeniyle API adresi değiştirilebilir.

### Örnek Ürün Verileri

Örnek ürün verileri:

`backend/data/phone_cases.json`

Ürün görselleri:

`frontend/public/products/`

Örnek veri ekleme betiği:

`backend/scripts/seed_phone_cases.py`

Örnek ürünleri eklemeden önce veritabanının ve uygun satıcı mağazasının hazırlanması gerekir.

## API Endpoint'leri

### Authentication

| Metot | Endpoint | Açıklama |
| --- | --- | --- |
| POST | `/api/auth/register` | Kullanıcı kaydı |
| POST | `/api/auth/login` | Kullanıcı girişi |
| GET | `/api/auth/me` | Aktif kullanıcı bilgisi |

### Seller

| Metot | Endpoint | Açıklama |
| --- | --- | --- |
| POST | `/api/sellers` | Mağaza oluşturma |
| GET | `/api/sellers/me` | Kendi mağazasını görüntüleme |
| GET | `/api/sellers/me/products` | Ürünlerini listeleme |
| POST | `/api/sellers/me/products` | Yeni ürün ekleme |
| PATCH | `/api/sellers/me/products/{product_id}` | Fiyat ve stok düzenleme |
| PATCH | `/api/sellers/me/products/{product_id}/visibility` | Ürün görünürlüğünü değiştirme |

### Catalog

| Metot | Endpoint | Açıklama |
| --- | --- | --- |
| GET | `/api/catalog/products` | Aktif ürünleri listeleme |
| GET | `/api/catalog/products/{product_id}` | Ürün detaylarını görüntüleme |

Satıcı işlemlerinde JWT doğrulaması ve ürün sahipliği kontrolü backend tarafında yapılır.

## Geliştirme Yol Haritası

### Tamamlananlar

- [x] FastAPI backend altyapısı
- [x] PostgreSQL bağlantısı
- [x] Veritabanı tabloları
- [x] Kullanıcı kayıt ve giriş sistemi
- [x] JWT kimlik doğrulaması
- [x] React ana sayfa tasarımı
- [x] Ürün kataloğu
- [x] Ürün detay sayfası
- [x] Sepet
- [x] Satıcı mağazası oluşturma
- [x] Satıcı paneli
- [x] Yeni ürün oluşturma
- [x] Yeni ürüne görsel adresi ekleme
- [x] Ürün düzenleme ve görünürlük için API ve arayüz

### Geliştirilmekte Olanlar

- [ ] Mevcut ürünün görselini değiştirme
- [ ] Satıcı ürün işlemlerinin uçtan uca testleri
- [ ] Dosyadan ürün görseli yükleme (opsiyonel)
- [ ] Sipariş oluşturma
- [ ] Sipariş sırasında stok güncelleme
- [ ] Demo ödeme akışı
- [ ] Müşteri paneli
- [ ] Müşteri sipariş geçmişi
- [ ] Admin yönetim paneli
- [ ] Mağaza ve sipariş denetimi
- [ ] Komisyon hesaplama
- [ ] WebSocket ile müşteri–admin canlı destek sohbeti
- [ ] Müşteri–satıcı özel mesajlaşması
- [ ] Güvenlik ve yetkilendirme testleri
- [ ] Mobil görünümün son düzenlemeleri

## Güvenlik ve Demo Kapsamı

- Parolalar veritabanında düz metin olarak tutulmaz.
- Satıcı işlemleri backend tarafında yetki kontrolünden geçer.
- Kullanıcı başka satıcıya ait ürünü düzenleyemez.
- Mevcut frontend oturum yönetimi demo amaçlı olarak `sessionStorage` kullanır.
- Üretim ortamında HttpOnly çerez tabanlı oturum yönetimi değerlendirilecektir.
- Sepet henüz gerçek sipariş ve ödeme işlemi oluşturmaz.
- Projede şu an gerçek ödeme alınmamaktadır.
- `.env`, JWT anahtarları ve veritabanı parolaları GitHub'a yüklenmemelidir.

## Görsel Kaynakları ve Lisans

Örnek telefon kılıfı görselleri **Amazon Berkeley Objects (ABO)** veri kümesinden alınmıştır.

Görseller **Creative Commons Attribution 4.0 (CC BY 4.0)** lisans koşullarıyla kullanılmaktadır.

Görsel bazındaki kaynak bilgileri:

`backend/data/IMAGE_SOURCES.md`

Kaynaklar:

- [Amazon Berkeley Objects](https://amazon-berkeley-objects.s3.us-east-1.amazonaws.com/index.html)
- [Creative Commons BY 4.0](https://creativecommons.org/licenses/by/4.0/)

---

**CaseMarket**, eğitim amaçlı geliştirilmeye devam eden bir üniversite projesidir.

## Proje Yol Haritası

Güncel geliştirme planı için [ROADMAP.md](ROADMAP.md) dosyasına bakın.
