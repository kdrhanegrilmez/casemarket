
import { useState } from 'react'

// Backend sunucumuzun adresi.
const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000'
).replace(/\/$/, '')

const formatPrice = (price) =>
  Number(price).toLocaleString('tr-TR', {
    style: 'currency',
    currency: 'TRY',
  })

function SellerProductRow({ product, token, onUpdated }) {

  // Bu satir duzenleme modunda mi?
  const [editing, setEditing] = useState(false)

  // Inputlara yazilan fiyat ve stok degerleri.
  const [price, setPrice] = useState(String(product.price))
  const [stock, setStock] = useState(String(product.stock))

  // API istegi devam ederken butonlari kilitleyecegiz.
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  // FastAPI'nin hata mesajini okunabilir hale getir.
  function getErrorMessage(data) {
    if (typeof data?.detail === 'string') {
      return data.detail
    }

    if (Array.isArray(data?.detail)) {
      return data.detail.map((item) => item.msg).join(', ')
    }

    return 'İşlem gerçekleştirilemedi.'
  }

  // Duzenle butonuna basildiginda inputlari hazirla.
  function startEditing() {
    setPrice(String(product.price))
    setStock(String(product.stock))
    setError('')
    setEditing(true)
  }

  // Fiyat ve stok bilgilerini backend'e kaydet.
  async function saveProduct() {
    const newPrice = Number(price)
    const newStock = Number(stock)

    if (
      price.trim() === '' ||
      stock.trim() === '' ||
      !Number.isFinite(newPrice) ||
      newPrice <= 0 ||
      !Number.isInteger(newStock) ||
      newStock < 0
    ) {
      setError('Geçerli bir fiyat ve stok miktarı gir.')
      return
    }

    setBusy(true)
    setError('')

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/sellers/me/products/${product.id}`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            price: newPrice,
            stock: newStock,
          }),
        }
      )

      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(getErrorMessage(data))
      }

      setEditing(false)

      // Ust bilesene "veriler degisti" bilgisini gonder.
      onUpdated()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Bağlantı hatası oluştu.'
      )
    } finally {
      setBusy(false)
    }
  }

  // Urunu yayina al veya yayindan kaldir.
  async function toggleVisibility() {
    setBusy(true)
    setError('')

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/sellers/me/products/${product.id}/visibility`,
        {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            is_active: !product.is_active,
          }),
        }
      )

      const data = await response.json().catch(() => null)

      if (!response.ok) {
        throw new Error(getErrorMessage(data))
      }

      onUpdated()
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Ürün durumu değiştirilemedi.'
      )
    } finally {
      setBusy(false)
    }
  }

  return (
    <tr>
      <td>
        <strong>{product.name}</strong>
        <small>Ürün #{product.id}</small>

        {error && (
          <small
            className="seller-row-error"
            role="alert"
          >
            {error}
          </small>
        )}
      </td>

      {/* Fiyat duzenleniyorsa input, degilse mevcut fiyat. */}
      <td>
        {editing ? (
          <input
            className="seller-edit-input"
            type="number"
            min="0.01"
            step="0.01"
            value={price}
            onChange={(event) =>
              setPrice(event.target.value)
            }
            aria-label={`${product.name} fiyatı`}
          />
        ) : (
          formatPrice(product.price)
        )}
      </td>

      {/* Stok icin de ayni mantigi kullaniyoruz. */}
      <td>
        {editing ? (
          <input
            className="seller-edit-input"
            type="number"
            min="0"
            step="1"
            value={stock}
            onChange={(event) =>
              setStock(event.target.value)
            }
            aria-label={`${product.name} stoku`}
          />
        ) : (
          product.stock
        )}
      </td>

      <td>
        <span
          className={
            product.is_active
              ? 'seller-status seller-status--active'
              : 'seller-status seller-status--inactive'
          }
        >
          {product.is_active ? 'Yayında' : 'Pasif'}
        </span>
      </td>

      <td>
        <div className="seller-row-actions">
          {editing ? (
            <>
              <button
                type="button"
                className="seller-row-button seller-row-button--primary"
                disabled={busy}
                onClick={saveProduct}
              >
                {busy ? 'Kaydediliyor...' : 'Kaydet'}
              </button>

              <button
                type="button"
                className="seller-row-button"
                disabled={busy}
                onClick={() => {
                  setEditing(false)
                  setError('')
                }}
              >
                İptal
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                className="seller-row-button"
                disabled={busy}
                onClick={startEditing}
              >
                Düzenle
              </button>

              <button
                type="button"
                className="seller-row-button"
                disabled={busy}
                onClick={toggleVisibility}
              >
                {product.is_active
                  ? 'Yayından kaldır'
                  : 'Yayına al'}
              </button>
            </>
          )}
        </div>
      </td>
    </tr>
  )
}

export default SellerProductRow
