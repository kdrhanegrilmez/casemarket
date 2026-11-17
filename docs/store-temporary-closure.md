# Mağazayı geçici kapatma

Admin → Mağazalar → Mağaza yayını sütununda **Mağazayı geçici kapat**
düğmesini kullanın. 5–500 karakter gerekçe girip onaylayın. Durum **Geçici kapalı**
olarak görünür. Aynı yerden gerekçeyle **Mağazayı yeniden aç** işlemi yapılır.

Satıcı rolü ve mağaza onayı korunur. Kapalı mağazanın ürünleri katalogda ve ürün
detayında görünmez; yeni sipariş ve yeni ürün sorusu oluşturulamaz. Satıcı mevcut
siparişlerini, ürünlerini ve konuşmalarını yönetebilir. Kapanış gerekçesini panelinde
görür. Yeniden açma, tek tek gizli veya moderasyon nedeniyle kaldırılmış ürünleri
yayınlamaz; yalnızca zaten yayındaki ürünler vitrinde tekrar görünür.

API: `PATCH /api/admin/stores/{seller_id}/temporary-closure`.
Gövde: `{ "is_temporarily_closed": true, "reason": "İnceleme gerekçesi" }`.
Yeniden açmak için aynı gövdede `false` gönderin. Yalnızca admin ve onaylı mağazalar
için kullanılabilir. Değişiklik ile admin denetim kaydı aynı transaction içindedir.

Mevcut veritabanında repo kökünden:

```bash
cd backend
python scripts/apply_store_temporary_closure_migration.py
```

Yeni kurulum için alanlar `backend/schema.sql` içinde bulunur.

Elle kontrol: Onaylı bir mağazayı kapatın; katalogdan ürünün kaybolduğunu,
eski ürün bağlantısının ve sepetteki ürün için yeni siparişin reddedildiğini
kontrol edin. Satıcıyla giriş yapıp kapanış gerekçesini, mevcut sipariş ve mesajlara
erişimi kontrol edin. Adminle yeniden açın; daha önce gizlenmiş ürünler gizli kalmalı,
yayındaki ürünler katalogda görünmelidir.
