# Mesajlaşma ve destek kontrol rehberi

Müşterinin Yardım paneli, satıcının Mesajlar sekmesi ve adminin Destek bölümü
aynı sohbet bileşenlerini kullanır. İlk mesaj ve yanıt aynı kutudan gönderilir.
Müşteri ve satıcı desteğinde kişi başına yalnızca bir **açık** görüşme bulunur.
Sonlandırılan görüşme geçmiş olarak korunur; **Yeni destek talebi** ayrı bir kayıt
açar. Aynı kural müşteri ve ürün başına açık ürün sorusu için de geçerlidir.
Müşteri veya ilgili satıcı ürün sorusunu **Görüşmeyi sonlandır** ile bitirebilir.
Müşteri aynı ürün için **Yeni soru sor** ile tekrar başlayabilir. Moderasyon
konuşmaları ürün başına tek kayıt olmaya devam eder.

## Veritabanını hazırlama

Mevcut veritabanında eksik migration'ları aşağıdaki sırayla uygulayın.
Komutlar repo kökünden başlar; daha önce uygulanan ön koşulları atlayabilirsiniz.
Bu çalışma sırasında migration'lar mevcut veritabanına uygulanmadı.

```bash
cd backend
python scripts/apply_seller_approval_migration.py
python scripts/apply_product_moderation_migration.py
python scripts/apply_support_chat_migration.py
python scripts/apply_support_read_status_migration.py
python scripts/apply_support_sessions_migration.py
```

Ürün moderasyonu migration'ı destek konuşmalarından önce gelmelidir.
`20261117_support_read_status.sql` okundu tablosunu, konuşma durumunu ve
hız sınırı sorgusunun indeksini oluşturur. Ardından `20261117_support_sessions.sql`
kişi/ürün tekilliklerini yalnızca açık görüşmeleri kapsayacak şekilde günceller.
Sonlandırılmış kayıt ve mesajlar silinmez.
Yeni kurulumda `backend/schema.sql`, ardından
`backend/migrations/002_phone_filters.sql` uygulanır. Yeni şema destek alanlarını içerir.
Eski `seller_notifications` tablosu ve bildirim API'leri korunur; arayüz bunları kullanmaz.

## API davranışı

- `GET /api/support/my/threads` ve `/admin/threads`: `status=open|closed|all`, varsayılan `open`.
  Liste öğelerinde `unread_count`, `status`, `closed_at`, `last_sender_role` ve `store_name` bulunur.
- `GET /api/support/threads/{id}`: yalnızca yanıtta dönen son mesajın ID'sine kadar okundu kaydeder.
  Eşzamanlı okuma kaydı geriye gitmez. Kendi mesajları okunmamış sayılmaz.
- `GET /api/support/my/unread-count`: müşterinin veya satıcının toplamı.
  `GET /api/support/admin/unread-count`: müşteri desteği, satıcı desteği ve moderasyon toplamı.
  Kapalı konuşmaların okunmamış mesajları da toplamda yer alır.
- `PATCH /api/support/threads/{id}/status`: admin `{ "status": "open" }` veya
  `{ "status": "closed" }` gönderebilir. Ürün sorusunun müşteri ve satıcısı yalnız
  `closed` gönderebilir; yabancı görüşme için `404`, destek/moderasyon durumunu
  değiştirmek veya yetkisiz yeniden açmak için `403` döner.
  Kapalı durum arayüzde **Sonlandırıldı** olarak gösterilir.
  Sonlandırılan desteğe admin dahil hiçbir katılımcı mesaj gönderemez (`409`).
  `/customer`, `/seller` ve ürün sorusu oluşturma yolları kapalı geçmişi değiştirmez;
  yeni görüşme oluşturur veya aynı kapsamdaki açık görüşmeye ekler. Adminin
  **Desteği yeniden aç** işlemi `closed_at` alanını temizler; aynı kapsamda başka açık
  görüşme varsa indeks kısıtı nedeniyle `409` döner.
  Ürün kaldırma/geri yayınlama gibi ayrı admin moderasyon işlemleri ilgili konuşmayı yeniden açar.
  Arşivleme ve arşiv numarası henüz eklenmemiştir.
- Kullanıcı başına tüm destek gönderim yollarında dakikada en fazla 10 mesaj; aşımda `429`.
- Yabancı konuşma için `404`; admin dışındakilere `*_email` alanları verilmez.
  Admin adı müşteri ve satıcıya `Admin` olarak gösterilir.

Açık liste 15, açık sohbet 8 saniyede yenilenir; her istek bittikten sonra beklenir.
Sonlandırılan listesi ve sohbet filtre veya sekme görünürlüğü değiştiğinde okunur; periyodik
detay isteği gönderilmez. Arka planda timer ve istekler iptal edilir, sekme görünür
olunca bir kez yenilenir. Rozetler 15 saniyede bir kontrol edilir. Sohbet okuması
sonrası sayaç yalnızca görülen son mesaj değiştiyse ayrıca yenilenir.

## Otomatik kontroller

Repo kökünden ayrı ayrı çalıştırın:

```bash
cd backend
python -m unittest
```

```bash
cd frontend
npm run lint
npm run build
```

Backend testleri FakeCursor ile sorgu kapsamını, parametreleri, dönüş değerlerini,
yetki sınırlarını ve transaction davranışını kontrol eder.

Gerçek PostgreSQL ve ASGI/HTTP regresyon testi (test kayıtları rollback edilir):

```bash
cd backend
CASEMARKET_DB_TESTS=1 python -m unittest tests.test_support_sessions_database -v
```

Tarayıcı regresyon testi için frontend dev sunucusu 5173 portunda açık olmalıdır.
Playwright proje bağımlılıklarını değiştirmeden kurulabilir:

```bash
npm install --prefix /tmp/casemarket-support-check --no-save playwright
node /tmp/casemarket-support-check/node_modules/playwright/cli.js install chromium --only-shell
cd frontend
NODE_PATH=/tmp/casemarket-support-check/node_modules node tests/support-browser-check.cjs
```

Bu test gerçek React bileşenlerini mock API ile çalıştırır; müşteri/satıcı için yeni
görüşmeyi, ürün sorusu sonlandırmayı, aktif polling sıklığını, bitmiş görüşmelerde
polling yapılmamasını, gizli sekmeyi ve mobil panel genişliğini doğrular.
Test HTML'i `frontend/tests/` altındadır ve üretim derlemesinin girdisi değildir.
Ekran görüntüleri `/tmp/casemarket-support-check/` altına yazılır.

Mağaza tablosunun ekran genişliklerine sığması, gerekçe pencereleri ve satıcı
sekme boyutları için aynı ortamda:

```bash
NODE_PATH=/tmp/casemarket-support-check/node_modules node tests/admin-store-layout-check.cjs
```

Sohbet araç çubuğunda ayrı bir Yenile düğmesi yoktur; açık görüşmeler otomatik
güncellenir. Satıcıda pano sekmeleri, iletişim kanalları ve sohbet işlemleri
sırasıyla 46, 38 ve 30 piksel minimum yüksekliktedir.

## Elle test: müşteri → admin → satıcı

Ön koşul: ayrı tarayıcı profillerinde müşteri, admin ve onaylı satıcı oturumları;
satıcıya ait yayında bir ürün. Rozet kontrolünde alıcının sohbetini kapalı tutun;
açık sohbet otomatik okunur.

1. Müşteri: Yardım → Destek bölümünü açın. Konuşma yoksa tek mesaj kutusu
   görünmeli. İlk mesajı gönderin, aynı kutudan ikinci mesajı yazın. Tek konuşma
   içinde iki mesaj görünmeli. Seçili konuşmaya tekrar tıklayın; içerik boşalmamalı.
2. Admin: Destek menüsündeki rozeti kontrol edin; en geç 15 saniyede yenilenir.
   Müşteri desteği → Açık bölümünden konuşmayı okuyun. Liste rozeti ve toplam
   azalsın. Yanıt gönderin. Müşterinin Yardım rozeti artsın; konuşmayı açınca
   temizlensin ve yanıtın göndereni `Admin` görünsün.
3. Admin: **Desteği sonlandır** düğmesini kullanın. Görüşme Devam eden listesinden
   çıkıp Sonlandırılan listesinde görünsün. Müşteri ve satıcıda mesaj kutusu kalkmalı;
   sonlandırılma bilgisi ve salt okunur geçmiş görünmeli. Eski açık sekmeden veya
   API'den eski görüşmeye mesaj gönderme denemesi `409` dönmeli. Müşteri ve satıcı
   **Yeni destek talebi** ile ayrı görüşme açabilmeli; eski mesajlar Sonlandırılan
   listesinde kalmalı. Aynı kapsamda açık görüşme varken eskiyi yeniden açma `409` dönmeli.
4. Müşteri: Ürün detayından satıcıya soru gönderin. Admin toplamı ürün sorusu
   nedeniyle artmamalı. Satıcı: İstatistikler yukarıda kalmalı; Ürünler /
   Siparişler / Mesajlar sekmelerinde Mesajlar rozeti görünmeli. Mesajlar →
   Müşteri soruları bölümünde soruyu okuyup yanıtlayın. Müşteri tarafında
   yanıt mağaza adıyla görünsün. Müşteri veya satıcı **Görüşmeyi sonlandır** ile
   soruyu bitirebilmeli. Müşteri aynı üründe yeni soru açabilmeli; eski mesajlar korunmalı.
5. Admin: Satıcının ürününü gerekçeyle kaldırın. Satıcı: Bildirimler sekmesi
   bulunmamalı. Mesajlar → Admin / Destek altında tek moderasyon konuşmasında
   gerekçe görünmeli. Yanıt gönderin; adminin Satıcı desteği listesinde görünsün.
   Admin aynı konuşmadan ürünü yeniden yayınlasın; satıcı aynı geçmişte geri
   yayınlama mesajını görsün. Kapalı moderasyon konuşması bu işlemlerle açılsın.
6. Her rolde tarayıcı Network panelini açın. Sekmeyi en az 20 saniye arka plana
   alın: yeni polling isteği oluşmamalı. Görünür yapınca hemen yenilensin.
7. Müşteri hesabıyla bir dakika içinde 11 mesaj deneyin: 11. istekte `429`
   ve `role="alert"` hata metni görünmeli; yazılan mesaj kaybolmamalı.
   Başka müşterinin/satıcının konuşma ID'sine GET ve POST denemeleri `404` dönmeli.
8. Mobil genişliği 520px veya altına indirin. Yardım paneli tam genişlikte
   alttan açılmalı; mesaj kutusu ve kapatma düğmesi kullanılabilir olmalı.

## Değişen dosyalar (beş aşama)

- Backend: `backend/routers/support.py`, `backend/routers/admin_dashboard.py`,
  `backend/schema.sql`, `backend/migrations/20261117_support_read_status.sql`,
  `backend/scripts/apply_support_read_status_migration.py`,
  `backend/migrations/20261117_support_sessions.sql`, `backend/scripts/apply_support_sessions_migration.py`.
- Testler: `backend/tests/test_support_chat.py`, `backend/tests/test_product_moderation.py`,
  `backend/tests/test_support_sessions_database.py`, `frontend/tests/support-browser-check.cjs`,
  `frontend/tests/support-browser-check.html`.
- Frontend: `frontend/src/api/support.js`, `frontend/src/components/ThreadCenter.jsx`,
  `ThreadCenter.css`, `ThreadList.jsx`, `ThreadView.jsx`, `threadTitle.js`,
  `MessageComposer.jsx`, `ModerationRestoreForm.jsx`, `UnreadBadge.jsx`,
  `useSupportUnread.js`, `useVisiblePolling.js`, `CustomerSupportWidget.jsx`, `CustomerSupportWidget.css`,
  `SellerDashboard.jsx`, `AdminDashboard.jsx` (kısa adlar `frontend/src/components/` altındadır).
- Dokümantasyon: `ROADMAP.md`, `docs/support-system.md`.

WebSocket, dosya/görsel gönderimi, e-posta bildirimi ve sipariş bazlı konuşma
bu çalışmanın kapsamına eklenmedi.
