# CaseMarket — Proje Yol Haritası

Son güncelleme: 30 Ekim 2026

## Teknolojiler

- Frontend: React, Vite, JavaScript, CSS
- Backend: Python, FastAPI
- Veritabanı: PostgreSQL
- Altyapı: Docker Compose
- Güvenlik: JWT, Argon2
- Veritabanı bağlantıları: Psycopg 3, Connection Pool

## 1. Temel altyapı ve kullanıcı sistemi

- [x] FastAPI backend
- [x] React frontend
- [x] PostgreSQL ve Docker Compose
- [x] Kullanıcı kayıt ve giriş sistemi
- [x] JWT ile kimlik doğrulama
- [x] Müşteri ve satıcı rolleri
- [x] Kullanıcı profil bilgileri
- [x] JWT süresi dolunca otomatik çıkış
- [x] PostgreSQL Connection Pool
- [ ] Tüm API istekleri için ortak 401 oturum yönetimi

## 2. Ürün kataloğu ve alışveriş sepeti

- [x] Premium ana sayfa tasarımı
- [x] Ürün listesi ve detay sayfası
- [x] Ürün arama ve sıralama
- [x] Stok filtreleme
- [x] Öne çıkan ürünler
- [x] Sepete ürün ekleme
- [x] Ürün adedini değiştirme
- [x] X butonuyla ürün kaldırma
- [x] Sepeti tamamen temizleme
- [x] Sepeti localStorage ile saklama
- [x] SiteDialog ile özel bildirimler

## 3. Hesabım ve sipariş sistemi

- [x] Hesabım sayfası
- [x] Profil düzenleme
- [x] Teslimat adresleri
- [x] Demo ödeme yöntemleri
- [x] Demo checkout
- [x] Sipariş oluşturma
- [x] Stok kontrolü ve stok azaltma
- [x] Çok ürünlü sipariş düzeltmesi
- [x] Sipariş geçmişi
- [x] Bekleyen siparişlerin iptali
- [x] İptalde stok iadesi
- [x] 8 sipariş birim testi
- [ ] Eski ve yeni ödeme akışlarını netleştirme
- [ ] Ödenmiş siparişler için iptal/iade politikası
- [ ] Gerçek PostgreSQL entegrasyon testleri

## 4. Satıcı yönetimi

- [x] Satıcı mağazası
- [x] Satıcı ürün listeleme
- [x] Ürün ekleme
- [x] Fiyat ve stok düzenleme
- [x] Ürün görünürlüğünü değiştirme
- [x] Ürün görsel URL yönetimi
- [ ] Satıcıya gelen siparişler ekranı
- [ ] Satıcı bazında sipariş kalemlerini listeleme
- [ ] Satıcı satış ve ciro istatistikleri

## 5. Sipariş ve kargo yönetimi

- [ ] Sipariş hazırlanıyor durumu
- [ ] Kargoya verildi durumu
- [ ] Kargo firması ve takip numarası
- [ ] Teslim edildi durumu
- [ ] Müşterinin sipariş takibi
- [ ] Sipariş durumu değiştirme yetkileri

Planlanan akış:
paid -> preparing -> shipped -> delivered

## 6. Admin paneli

- [ ] Admin yönetim arayüzü
- [ ] Kullanıcı yönetimi
- [ ] Satıcı ve mağaza denetimi
- [ ] Ürün ve sipariş denetimi
- [ ] Komisyon hesaplama
- [ ] Platform satış raporları

## 7. Mesajlaşma ve destek

- [ ] Müşteri-satıcı mesajlaşması
- [ ] Mesaj geçmişinin veritabanında tutulması
- [ ] WebSocket ile gerçek zamanlı mesajlaşma
- [ ] Müşteri-admin destek sistemi

## 8. Güvenlik, test ve yayınlama

- [x] JWT doğrulaması
- [x] Temel yetkilendirme kontrolleri
- [x] Parametreli SQL sorguları
- [x] Sipariş transaction yönetimi
- [x] PostgreSQL Connection Pool
- [x] Sipariş birim testleri
- [x] JWT otomatik çıkış testi
- [ ] Genişletilmiş yetkilendirme testleri
- [ ] PostgreSQL entegrasyon testleri
- [ ] Performans ve yük testleri
- [ ] Mobil arayüz son kontrolleri
- [ ] API dokümantasyonu güncellemesi
- [ ] Deployment
- [ ] Üniversite proje raporu ve sunum

## 30 Ekim 2026 — Yapılan geliştirmeler

- orders.py çok ürünlü sipariş hatası düzeltildi.
- Tek sipariş altında birden fazla ürün kontrol edildi.
- Psycopg Connection Pool eklendi.
- PostgreSQL'de iki hazır bağlantı gözlemlendi.
- Sekiz sipariş birim testi başarıyla geçti.
- JWT süresi React tarafından takip edilmeye başlandı.
- Bir dakikalık JWT testiyle otomatik çıkış doğrulandı.
- JWT süresinin test sonrasında normal değere döndürülmesi planlandı.

## Sıradaki geliştirme

Ders 22: Satıcı sipariş yönetimi.

Satıcı, müşterilerin kendi mağazasından satın aldığı
ürünleri ve siparişleri görebilmeli.

Ardından kargo süreçleri, müşteri takibi ve admin paneli
geliştirilecek.
