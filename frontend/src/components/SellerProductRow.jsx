
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

function SellerProductRow({ product, token, onUpdated, catalogFilters }) {

  // Bu satir duzenleme modunda mi?
  const [editing, setEditing] = useState(false)

  // Inputlara yazilan fiyat ve stok degerleri.
  const [price, setPrice] = useState(String(product.price))
  const [stock, setStock] = useState(String(product.stock))
  const [imageUrl,setImageUrl] = useState(String(product.image_url || ''))
  const [name,setName] =useState(String(product.name))
  const [categoryId, setCategoryId] = useState(String(product.category_id || ''))
  const [modelIds, setModelIds] = useState(product.model_ids || [])
  const [brandId, setBrandId] = useState('')


  // API istegi devam ederken butonlari kilitleyecegiz.
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const selectedBrand = catalogFilters.brands.find((brand) => String(brand.id) === brandId)
  const modelNames = (product.model_ids || []).flatMap((id) =>
    catalogFilters.brands.flatMap((brand) =>
      brand.models.filter((model) => model.id === id).map((model) => `${brand.name} ${model.name}`)
    )
  )

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
    setName(product.name )
    setImageUrl(product.image_url || '')
    setCategoryId(String(product.category_id || ''))
    setModelIds(product.model_ids || [])
    const firstBrand = catalogFilters.brands.find((brand) =>
      brand.models.some((model) => (product.model_ids || []).includes(model.id))
    )
    setBrandId(String(firstBrand?.id || ''))
  }

  // Fiyat ve stok bilgilerini backend'e kaydet.
  async function saveProduct() {
    const newPrice = Number(price)
    const newStock = Number(stock)
    const newImageUrl = imageUrl.trim()
    const newName = name.trim()
    const originalModelIds = product.model_ids || []
    const compatibilityChanged = categoryId !== String(product.category_id || '') ||
      modelIds.length !== originalModelIds.length ||
      modelIds.some((id) => !originalModelIds.includes(id))

    if (
      newName.length < 3 ||
      price.trim() === '' ||
      stock.trim() === '' ||
      !Number.isFinite(newPrice) ||
      newPrice <= 0 ||
      !Number.isInteger(newStock) ||
      newStock < 0 ||
      (compatibilityChanged && (!categoryId || modelIds.length === 0))
    ) {
      setError('Ürün bilgilerini, kılıf türünü ve en az bir telefon modelini seç.')
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
            name: newName,
            image_url: newImageUrl || null,
            ...(compatibilityChanged ? {
              category_id: Number(categoryId),
              model_ids: modelIds,
            } : {}),
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
          {editing ?(
              <input

              className="seller-edit-name"
              type="text"
              value={name}
              onChange={(event)=> setName(event.target.value)}
              minLength={3}
              maxLength={200}
              aria-label="Ürün Adı"
              placeholder="Yeni Ürün Adını Giriniz:"
              />
          ):( <strong>{product.name}</strong>) }




        <small>Ürün #{product.id}</small>
        {!editing && modelNames.length > 0 && <small className="seller-row-models">{modelNames.join(' · ')}</small>}

         {/* Düzenle butonuna basılınca görsel alanını göster. */}
          {editing && (
              <label className='seller-row-image-field'>
                  Görsel Adres

                  <input
                  type="text"
                  value={imageUrl}
                  onChange={(event)=>setImageUrl(event.target.value)}
                  placeholder="görsel adresi"
                  maxLength={500}

                  />
              </label>
          )
          }

          {editing && (
            <div className="seller-row-compatibility">
              <label>
                Kılıf türü
                <select value={categoryId} onChange={(event) => setCategoryId(event.target.value)}>
                  <option value="">Tür seç</option>
                  {catalogFilters.categories.map((category) => (
                    <option key={category.id} value={category.id}>{category.name}</option>
                  ))}
                </select>
              </label>
              <label>
                Telefon markası
                <select value={brandId} onChange={(event) => setBrandId(event.target.value)}>
                  <option value="">Marka seç</option>
                  {catalogFilters.brands.map((brand) => (
                    <option key={brand.id} value={brand.id}>{brand.name}</option>
                  ))}
                </select>
              </label>
              {selectedBrand && (
                <fieldset>
                  <legend>Uyumlu modeller</legend>
                  {selectedBrand.models.map((model) => (
                    <label key={model.id}>
                      <input
                        type="checkbox"
                        checked={modelIds.includes(model.id)}
                        onChange={(event) => setModelIds((ids) => event.target.checked
                          ? [...ids, model.id]
                          : ids.filter((id) => id !== model.id))}
                      />
                      {model.name}
                    </label>
                  ))}
                </fieldset>
              )}
              <small>{modelIds.length} model seçili. Farklı markaya geçerek ek model seçebilirsin.</small>
            </div>
          )}



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
