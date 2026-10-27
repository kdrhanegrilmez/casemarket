import { useEffect, useState } from 'react'
import { getMyOrders, cancelOrder } from '../api/orders'
import './OrderHistory.css'


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
  if (status === 'paid') return 'Ödendi'
  if (status === 'canceled') return 'İptal edildi'

  return status
}


function OrderHistory({ token, onBack }) {
  // Musterinin siparislerini React state'inde tut.
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)

  // SIPARIS IPTAL ISLEMLERI
  const [cancellingId, setCancellingId] = useState(null)
  const [cancelError, setCancelError] = useState('')

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
  async function handleCancelOrder(orderId) {
    if (cancellingId !== null) return

    // Yanlislikla iptal edilmesini engelle.
    const confirmed = window.confirm(
      `#${orderId} numaralı siparişi iptal etmek istiyor musun?`
    )

    if (!confirmed) return

    setCancellingId(orderId)
    setCancelError('')

    try {
      // FastAPI'ye iptal istegi gonder.
      await cancelOrder(token, orderId)

      // Siparis listesini backend'den yeniden getir.
      setRefreshKey((previous) => previous + 1)
    } catch (err) {
      setCancelError(
        err instanceof Error
          ? err.message
          : 'Sipariş iptal edilemedi.'
      )
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

          <h1>Siparişlerim</h1>

          <p>
            Önceki siparişlerini ve güncel durumlarını
            buradan takip edebilirsin.
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

      {cancelError && (
        <p
          className="status-message status-message--error"
          role="alert"
        >
          {cancelError}
        </p>
      )}

      {!loading && !error && orders.length === 0 && (
        <div className="order-history__empty">
          <span aria-hidden="true">◇</span>

          <h2>Henüz siparişin bulunmuyor.</h2>

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

      {!loading && !error && orders.length > 0 && (
        <div className="order-history__list">

          {orders.map((order) => (
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

    </section>
  )
}

export default OrderHistory
