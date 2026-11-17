# Mesajlaşma ve destek kontrol rehberi

Müşterinin Yardım paneli, satıcının Mesajlar sekmesi ve adminin Destek bölümü
aynı sohbet bileşenlerini kullanır. İlk mesaj ve yanıt aynı kutudan gönderilir.
Müşteri ve satıcı desteği kişi başına tek konuşmadır; ürün soruları müşteri ve
ürün başına, moderasyon konuşmaları ürün başına tek kayıttır.

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
```

Ürün moderasyonu migration'ı destek konuşmalarından önce gelmelidir.
Son migration `20261117_support_read_status.sql`; okundu tablosunu,
konuşma durumunu ve hız sınırı sorgusunun indeksini oluşturur.
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
- `PATCH /api/support/threads/{id}/status`: yalnızca admin, `{ "status": "open" }`
  veya `{ "status": "closed" }`. Yeni mesaj konuşmayı açar ve `closed_at` alanını temizler.
- Kullanıcı başına tüm destek gönderim yollarında dakikada en fazla 10 mesaj; aşımda `429`.
- Yabancı konuşma için `404`; admin dışındakilere `*_email` alanları verilmez.
  Admin adı müşteri ve satıcıya `Admin` olarak gösterilir.

Liste 15, sohbet 8 saniyede yenilenir. Arka planda polling isteği yapılmaz;
sekme görünür olduğunda hemen yenilenir. Sayaçlar okuma sonrası ayrıca yenilenir.

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
yetki sınırlarını ve transaction davranışını kontrol eder. Gerçek PostgreSQL
eşzamanlılık davranışı ve tarayıcı yerleşimleri bu testlerin kapsamında değildir.

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
3. Admin: Konuşmayı kapatın. Açık listeden çıkıp Kapalı listede görünsün.
   Yeniden açıp tekrar kapatın. Müşteri aynı kutudan mesaj gönderince Açık
   listesine geri dönsün.
4. Müşteri: Ürün detayından satıcıya soru gönderin. Admin toplamı ürün sorusu
   nedeniyle artmamalı. Satıcı: İstatistikler yukarıda kalmalı; Ürünler /
   Siparişler / Mesajlar sekmelerinde Mesajlar rozeti görünmeli. Mesajlar →
   Müşteri soruları bölümünde soruyu okuyup yanıtlayın. Müşteri tarafında
   yanıt mağaza adıyla görünsün.
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
  `backend/scripts/apply_support_read_status_migration.py`.
- Testler: `backend/tests/test_support_chat.py`, `backend/tests/test_product_moderation.py`.
- Frontend: `frontend/src/api/support.js`, `frontend/src/components/ThreadCenter.jsx`,
  `ThreadCenter.css`, `ThreadList.jsx`, `ThreadView.jsx`, `threadTitle.js`,
  `MessageComposer.jsx`, `ModerationRestoreForm.jsx`, `UnreadBadge.jsx`,
  `useSupportUnread.js`, `CustomerSupportWidget.jsx`, `CustomerSupportWidget.css`,
  `SellerDashboard.jsx`, `AdminDashboard.jsx` (kısa adlar `frontend/src/components/` altındadır).
- Dokümantasyon: `ROADMAP.md`, `docs/support-system.md`.

WebSocket, dosya/görsel gönderimi, e-posta bildirimi ve sipariş bazlı konuşma
bu çalışmanın kapsamına eklenmedi.
