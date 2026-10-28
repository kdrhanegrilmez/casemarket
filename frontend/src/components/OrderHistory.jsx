
import { useEffect, useState } from 'react'
import { getMyOrders, cancelOrder } from '../api/orders'
import './OrderHistory.css'
import SiteDialog from './SiteDialog'


// Fiyatlari Turk lirasi olarak goster.
const formatPrice = (value) =>
  Number(value).toLocaleString('tr-TR', {
    style: 'currency',
    currency: 'TRY',
  })


// Siparis tarihini Turkiye saatine cevir.
const formatDate = (value) =>
  new Date(value).toLocaleString('tr-TR', {
    timeZone: 'Europe/Istanbul',
    dateStyle: 'long',
    timeStyle: 'short',
  })


// Veritabanindaki siparis durumlarini Turkcelestir.
function getStatusText(status) {
  if (status === 'pending') return 'Ödeme bekliyor'
  if (status === 'paid') return 'Demo ödeme tamamlandı'
  if (status === 'canceled') return 'İptal edildi'

  return status
}


function OrderHistory({ token, onBack, filter = 'history' }) {
  // Musterinin siparislerini React state'inde tut.
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  // SIPARIS IPTAL ISLEMLERI
  const [cancellingId, setCancellingId] = useState(null)

  // SITE ICI ONAY VE SONUC PENCERESI
  const [dialog, setDialog] = useState(null)
  const visibleOrders = filter === 'active'
    ? orders.filter((order) => order.status !== 'canceled')
    : orders

  // Sayfa acilinca backend'den siparisleri getir.
  useEffect(() => {
    let active = true

    async function loadOrders() {
      setLoading(true)
      setError('')

      try {
        const data = await getMyOrders(token)

        if (!Array.isArray(data)) {
          throw new Error('Geçersiz sipariş verisi.')
        }

        if (active) {
          setOrders(data)
        }
      } catch (err) {
        if (active) {
          setError(
            err instanceof Error
              ? err.message
              : 'Siparişler yüklenemedi.'
          )
        }
      } finally {
        if (active) {
          setLoading(false)
        }
      }
    }

    loadOrders()

    return () => {
      active = false
    }
  }, [token, refreshKey])


  // MUSTERININ SIPARISINI IPTAL ET
  function handleCancelOrder(orderId) {
    if (cancellingId !== null) return

    // Yanlislikla iptal edilmesini engelle.
    // Tarayici confirm penceresi yerine kendi penceremizi aciyoruz.
    setDialog({
      variant: 'confirm',
      action: 'cancel',
      orderId,
      title: 'Siparişi iptal et',
      message: `#${orderId} numaralı siparişi iptal etmek istiyor musun? Ürünler yeniden stoğa eklenecek.`,
      confirmText: 'Evet, iptal et',
      danger: true,
    })
  }


  // Kullanici site icindeki pencereden onay verince API'yi cagir.
  async function confirmOrderAction() {
    if (!dialog || dialog.variant !== 'confirm') return
    if (cancellingId !== null) return

    const { orderId } = dialog
    setCancellingId(orderId)

    try {
      await cancelOrder(token, orderId)

      // Siparis listesini backend'den yeniden getir.
      setRefreshKey((previous) => previous + 1)

      setDialog({
        variant: 'success',
        title: 'Sipariş iptal edildi',
        message: `#${orderId} numaralı sipariş iptal edildi ve ürünlerin stoğu geri yüklendi.`,
      })
    } catch (err) {
      setDialog({
        variant: 'error',
        title: 'İşlem tamamlanamadı',
        message: err instanceof Error ? err.message : 'Bir hata oluştu.',
      })
    } finally {
      setCancellingId(null)
    }
  }


  return (
    <section className="order-history">

      <div className="order-history__heading">
        <div>
          <span className="overline">
            CASEMARKET / HESABIM
          </span>

          <h1>{filter === 'active' ? 'Aktif siparişler' : 'Sipariş geçmişi'}</h1>

          <p>
            {filter === 'active' ? 'İşlemdeki siparişlerini buradan takip edebilirsin.' : 'Tüm siparişlerini ve durumlarını burada görebilirsin.'}
          </p>
        </div>

        <button
          type="button"
          className="button button--dark"
          onClick={onBack}
        >
          ← Koleksiyona dön
        </button>
      </div>

      {loading && (
        <p className="status-message">
          Siparişlerin yükleniyor...
        </p>
      )}

      {error && (
        <div
          className="status-message status-message--error"
          role="alert"
        >
          <p>{error}</p>

          <button
            type="button"
            className="button button--dark"
            onClick={() => setRefreshKey((value) => value + 1)}
          >
            Tekrar dene
          </button>
        </div>
      )}

      {!loading && !error && visibleOrders.length === 0 && (
        <div className="order-history__empty">
          <span aria-hidden="true">◇</span>

          <h2>{filter === 'active' ? 'Aktif siparişin bulunmuyor.' : 'Henüz siparişin bulunmuyor.'}</h2>

          <p>
            Koleksiyonumuzdaki telefon kılıflarını keşfederek
            ilk siparişini oluşturabilirsin.
          </p>

          <button
            type="button"
            className="button button--dark"
            onClick={onBack}
          >
            Ürünleri keşfet ↗
          </button>
        </div>
      )}

      {!loading && !error && visibleOrders.length > 0 && (
        <div className="order-history__list">

          {visibleOrders.map((order) => (
            <article
              key={order.id}
              className="order-history__card"
            >

              <div className="order-history__card-heading">
                <div>
                  <span className="order-history__number">
                    SİPARİŞ #{order.id}
                  </span>

                  <p className="order-history__date">
                    {formatDate(order.created_at)}
                  </p>
                </div>

                <span
                  className={`order-history__status order-history__status--${order.status}`}
                >
                  {getStatusText(order.status)}
                </span>
              </div>

              <div className="order-history__items">

                {order.items.map((item, index) => (
                  <div
                    key={`${item.product_id}-${index}`}
                    className="order-history__item"
                  >
                    <div>
                      <strong>{item.product_name}</strong>

                      <p>
                        {item.quantity} adet · Birim fiyat:
                        {' '}{formatPrice(item.unit_price)}
                      </p>
                    </div>

                    <strong>
                      {formatPrice(
                        Number(item.unit_price) * item.quantity
                      )}
                    </strong>
                  </div>
                ))}

              </div>

              <div className="order-history__total">
                <span>Sipariş toplamı</span>

                <strong>
                  {formatPrice(order.total_amount)}
                </strong>
              </div>
              {(order.shipping_address || order.payment_method_summary) && <div className="order-history__details">
                {order.shipping_address && <p><strong>Teslimat:</strong> {order.shipping_address}</p>}
                {order.payment_method_summary && <p><strong>Ödeme:</strong> {order.payment_method_summary}</p>}
              </div>}

              {/* YALNIZCA BEKLEYEN SIPARISLER IPTAL EDILEBILIR */}
              {order.status === 'pending' && (
                <div className="order-history__actions">
                  <button
                    type="button"
                    className="button button--dark"
                    disabled={cancellingId !== null}
                    onClick={() => handleCancelOrder(order.id)}
                  >
                    {cancellingId === order.id
                      ? 'İptal ediliyor...'
                      : 'Siparişi İptal Et'}
                  </button>
                </div>
              )}

            </article>
          ))}

        </div>
      )}

      {/* ORTAK SITE ICI BILDIRIM PENCERESI */}
      <SiteDialog
        open={dialog !== null}
        variant={dialog?.variant}
        title={dialog?.title}
        message={dialog?.message}
        confirmText={dialog?.confirmText}
        danger={dialog?.danger}
        busy={cancellingId !== null}
        onConfirm={confirmOrderAction}
        onClose={() => {
          if (cancellingId === null) setDialog(null)
        }}
      />

    </section>
  )
}

export default OrderHistory
