
import { useEffect, useState } from 'react'
import './SellerDashboard.css'
import './components.css'
import SellerProductRow from './SellerProductRow.jsx'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000'
).replace(/\/$/, '')

const shippingLabels = { pending: 'Bekliyor', preparing: 'Hazırlanıyor', shipped: 'Kargoda', delivered: 'Teslim edildi' }
const nextShippingStatus = { pending: 'preparing', preparing: 'shipped', shipped: 'delivered' }
const formatPrice = (value) => Number(value).toLocaleString('tr-TR', { style: 'currency', currency: 'TRY' })

function SellerDashboard({ token, user, onBack }) {
  const [store, setStore] = useState(null)
  const [products, setProducts] = useState([])
  const [orders, setOrders] = useState([])
  const [shippingBusyId, setShippingBusyId] = useState(null)
  const [shippingError, setShippingError] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [saving,setSaving]=useState(false)
  const [createMessage, setCreateMessage] =useState('')
    // Kategori, telefon markasi ve model secenekleri.
  const [catalogFilters, setCatalogFilters] = useState({
      brands: [],
      categories: [],
    })
    const [filtersLoading, setFiltersLoading] = useState(true)
  const [filtersError, setFiltersError] = useState('')

  // Yeni urunun kategori ve uyumluluk bilgileri.
  const [categoryId, setCategoryId] = useState('')
  const [brandId, setBrandId] = useState('')
  const [modelIds, setModelIds] = useState([])



  // Saticinin magazasini ve urunlerini getir.
  useEffect(() => {
    const controller = new AbortController()

    async function loadDashboard() {
      setLoading(true)
      setError('')

      try {
        const headers = {
          Authorization: `Bearer ${token}`,
        }

        const [storeResponse, productsResponse, ordersResponse] =
          await Promise.all([
            fetch(`${API_BASE_URL}/api/sellers/me`, {
              headers,
              signal: controller.signal,
            }),
            fetch(`${API_BASE_URL}/api/sellers/me/products`, {
              headers,
              signal: controller.signal,
            }),
            fetch(`${API_BASE_URL}/api/sellers/me/orders`, {
              headers,
              signal: controller.signal,
            }),
          ])

        if (
          storeResponse.status === 401 ||
          productsResponse.status === 401 ||
          ordersResponse.status === 401
        ) {
          throw new Error(
            'Oturum süren dolmuş. Çıkış yapıp yeniden giriş yap.'
          )
        }

        if (!storeResponse.ok || !productsResponse.ok || !ordersResponse.ok) {
          throw new Error(
            'Mağaza bilgileri getirilemedi.'
          )
        }

        const [storeData, productData, orderData] =
          await Promise.all([
            storeResponse.json(),
            productsResponse.json(),
            ordersResponse.json(),
          ])

        if (!Array.isArray(productData) || !Array.isArray(orderData)) {
          throw new Error('Ürün listesi geçersiz.')
        }

        if (!controller.signal.aborted) {
          setStore(storeData)
          setProducts(productData)
          setOrders(orderData)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err instanceof Error
              ? err.message
              : 'Beklenmeyen bir hata oluştu.'
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadDashboard()

    return () => controller.abort()
  }, [token, refreshKey])


  // Telefon markalari, modelleri ve kilif turlerini getir.
  useEffect(() => {
    const controller = new AbortController()

    async function loadFilters() {
      setFiltersLoading(true)
      setFiltersError('')

      try {
        const response = await fetch(
          `${API_BASE_URL}/api/catalog/filters`,
          {
            signal: controller.signal,
          }
        )

        if (!response.ok) {
          throw new Error('Filtre seçenekleri yüklenemedi.')
        }

        const data = await response.json()

        if (
          !Array.isArray(data.brands) ||
          !Array.isArray(data.categories)
        ) {
          throw new Error('Filtre verileri geçersiz.')
        }

        if (!controller.signal.aborted) {
          setCatalogFilters(data)
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setFiltersError(
            err instanceof Error
              ? err.message
              : 'Beklenmeyen bir hata oluştu.'
          )
        }
      } finally {
        if (!controller.signal.aborted) {
          setFiltersLoading(false)
        }
      }
    }

    loadFilters()

    return () => controller.abort()
  }, [])






  async function handleCreateProduct(event){
    event.preventDefault() //html formatının sayfayı yeniden yüklemesini engeller

    const form = event.currentTarget
    const formData =new FormData(form)//formdata ile form içindeki inputları oku
    const name =String(formData.get('name')).trim()//name bilgisi alıyrouz
    const description = String(formData.get('description')).trim()
    const price = Number(formData.get('price'))
    const stock = Number(formData.get('stock'))
    //formdan gelen görsel adresii oku
    const image_url =String(formData.get('image_url')|| '').trim()

    /*
   * FRONTEND DOGRULAMASI
   *
   * Hatali bilgileri sunucuya gondermeden once kontrol
   * ediyoruz. Backend de kendi dogrulamasini yapacak.
   */

    if (
        name.length < 3 ||
        !Number.isFinite(price) ||
        price <=0 ||
        !Number.isInteger(stock) ||
        stock <0 ||
        !categoryId ||
        !brandId ||
        modelIds.length === 0
    ){
      setCreateMessage('Ürün bilgilerini, kılıf türünü ve en az bir telefon modelini seç.')
      return
    }

    //Kaydet butounu geçici olarak devre dışı bırak
    setSaving(true)
    //Önceki mesaj varsa temizle
    setCreateMessage('')

    try{
      const response =await fetch(
          `${API_BASE_URL}/api/sellers/me/products`,{
              method:'POST',

            headers: {
                'Content-Type': 'application/json',
              Authorization: `Bearer ${token}`,

            },

            body: JSON.stringify({
              name:name,
              description:description,
              price:price,
              stock:stock,
              category_id:Number(categoryId),
              model_ids:modelIds,
              image_url: image_url || null,
            }),
          }
      )

      const result =await response.json()

      if (!response.ok){
        const errorMessage =
            typeof result.detail ==='string'
              ? result.detail
              : 'Ürün Kaydedilemedi. Bilgileri kontrol et.'

        throw new Error(errorMessage)
      }
      setCreateMessage('Ürün başarıyla kaydedildi.')
      form.reset()
      setCategoryId('')
      setBrandId('')
      setModelIds([])

    /*
     * refreshKey degisince, yukaridaki useEffect tekrar
     * calisir ve saticinin urunlerini backend'den getirir.
     *
     * Boylece yeni urun ve istatistikler guncellenir.
    */
      setRefreshKey((previousValue)=>previousValue+1)


    }catch (error){
      //HTTP veya bağlantı hatasın kullanıcıya gösterelim
      setCreateMessage(
          error instanceof Error
          ? error.message
              : 'Beklenmeyen bir hata oluştu'
      )
    } finally{
      setSaving(false)//böylece Kaydet butonu tekrar kullanılabilir
    }

  }

  async function updateShipping(orderId, itemId, status) {
    setShippingBusyId(itemId)
    setShippingError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/sellers/me/orders/${orderId}/items/${itemId}/shipping`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status }),
      })
      const data = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Kargo durumu güncellenemedi.')
      setRefreshKey((key) => key + 1)
    } catch (err) {
      setShippingError(err instanceof Error ? err.message : 'Bağlantı hatası oluştu.')
    } finally {
      setShippingBusyId(null)
    }
  }

  const activeCount = products.filter(
    (product) => product.is_active
  ).length

  const totalStock = products.reduce(
    (total, product) =>
      total + Number(product.stock),
    0
  )


    // Seçilen markanın bilgilerini bul.
    const selectedBrand = catalogFilters.brands.find(
      (brand) => brand.id === Number(brandId)
    )

    // Marka seçilmediyse boş liste kullan.
    const availableModels = selectedBrand?.models ?? []

  return (
    <section className="seller-dashboard">

      <div className="seller-dashboard__navigation">
        <button type="button" onClick={onBack}>
          ← Mağazaya dön
        </button>

        <span>CASEMARKET / SATICI MERKEZİ</span>
      </div>

      <div className="seller-dashboard__heading">
        <p>SATICI YÖNETİM PANELİ</p>

        <h1>Mağazanı yönet.</h1>

        <span>
          Hoş geldin, {user.full_name}.
          Mağazanı ve ürünlerini buradan takip edebilirsin.
        </span>
      </div>

      {loading && (
        <p className="seller-dashboard__message">
          Mağaza bilgileri yükleniyor...
        </p>
      )}

      {error && !loading && (
        <div
          className="seller-dashboard__error"
          role="alert"
        >
          <p>{error}</p>

          <button
            type="button"
            onClick={() =>
              setRefreshKey((value) => value + 1)
            }
          >
            Tekrar dene
          </button>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="seller-dashboard__store">
            <div>
              <span>MAĞAZAM</span>
              <h2>{store?.store_name}</h2>
              <p>
                {store?.description ||
                  'Mağazan için henüz bir açıklama eklenmedi.'}
              </p>
            </div>

            <span className="seller-dashboard__store-icon">
              CM
            </span>
          </div>

          <div className="seller-dashboard__stats">
            <div>
              <span>Toplam Ürün</span>
              <strong>{products.length}</strong>
            </div>

            <div>
              <span>Yayındaki Ürünler</span>
              <strong>{activeCount}</strong>
            </div>

            <div>
              <span>Toplam Stok</span>
              <strong>{totalStock}</strong>
            </div>
          </div>

          {/*yeni ürün ekleme formu*/}

          <section className="seller-create">
            <div className="seller-create__heading">
              <span>ÜRÜN YÖNETİMİ / YENİ KAYIT</span>
              <h2>Yeni Ürün Ekle</h2>
              <p>
                Ürün bilgilerini doldur
                Kaydettiğinde Mağzana Yeni bir Ürün Eklenecek
              </p>
            </div>

            <form onSubmit={handleCreateProduct}>
              <div className="seller-create__grid">
                 {/* URUN ADI */}
                 <label className="seller-create__field">
                   Ürün Adı

                   <input
                     type="text"
                     name="name"
                     placeholder="Örn: Mat siyah/beyaz elefon kılıfı"
                     minLength={3}
                     required
                   />
                 </label>
                {/* FIYAT */}
                <label className="seller-create__field">
                  Fiyat (TL)

                  <input
                  type="number"
                  name="price"
                  placeholder="449.90"
                  min="0.01"
                  step="0.01"
                  required
                  />
                </label>

                {/*STOK MİKTARI*/}
                <label className="seller-create__field">
                  Stok Adedi

                  <input
                  type="number"
                  name="stock"
                  placeholder="15"
                  min="0"
                  step="1"
                  required
                  />
                </label>

                {/*Ürün Açıklaması*/}

                <label className="seller-create__field seller-create__field--wide">
                  Ürün Açıklaması
                  <textarea
                    name="description"
                    rows={4}
                    placeholder="Ürün özellikleri hakkında bir açıklama yapın..."
                    required
                  />
                </label>

                {/*Ürün Görseli*/}
                <label className="seller-create__field seller-create__field--wide">
                  Ürün Görseli

                  <input
                  type="text"
                  name="image_url"
                  placeholder="Ürün Görselinin Adresini Ekleyiniz"
                      maxLength={500}
                  />

                </label>

                <label className="seller-create__field">
                  Kılıf Türü

                  <select
                    value={categoryId}
                    onChange={(event) => {
                      setCategoryId(event.target.value)
                    }}
                    required
                    disabled={filtersLoading || Boolean(filtersError)}
                  >
                    <option value="">Kılıf türünü seç</option>

                    {catalogFilters.categories.map((category) => (
                      <option key={category.id} value={category.id}>
                        {category.name}
                      </option>
                    ))}
                  </select>
                </label>

                <label className="seller-create__field">
                  Telefon Markası

                  <select
                    value={brandId}
                    onChange={(event) => {
                      setBrandId(event.target.value)
                      setModelIds([])
                    }}
                    required
                    disabled={filtersLoading || Boolean(filtersError)}
                  >
                    <option value="">Telefon markasını seç</option>

                    {catalogFilters.brands.map((brand) => (
                      <option key={brand.id} value={brand.id}>
                        {brand.name}
                      </option>
                    ))}
                  </select>
                </label>

                <fieldset className="seller-create__models">
                  <legend>Uyumlu Telefon Modelleri</legend>

                  {!brandId && <p>Önce telefon markasını seç.</p>}

                  {brandId && availableModels.length === 0 && (
                    <p>Bu markaya ait model bulunamadı.</p>
                  )}

                  {availableModels.map((model) => (
                    <label
                      key={model.id}
                      className="seller-create__model-option"
                    >
                      <input
                        type="checkbox"
                        checked={modelIds.includes(model.id)}
                        onChange={(event) => {
                          setModelIds((previous) =>
                            event.target.checked
                              ? [...previous, model.id]
                              : previous.filter((id) => id !== model.id)
                          )
                        }}
                      />

                      <span>{model.name}</span>
                    </label>
                  ))}

                  {modelIds.length > 0 && (
                    <p>{modelIds.length} model seçildi.</p>
                  )}
                </fieldset>

                {filtersLoading && (
                  <p className="seller-create__filter-message">
                    Telefon modelleri yükleniyor...
                  </p>
                )}

                {filtersError && (
                  <p className="seller-create__filter-message" role="alert">
                    {filtersError}
                  </p>
                )}


              </div>
            {/* BACKEND'DEN GELEN SONUCU GOSTER */}
              {createMessage &&(
                  <p className="seller-create__message" role="status">
                    {createMessage}
                  </p>
                  )}
              {/* saving TRUE OLUNCA BUTON KILITLENIR */}
              <button
                type="submit"
                className="seller-create__submit"
                disabled={saving || filtersLoading || Boolean(filtersError)}
                >
                {saving ? 'Kaydediliyor...' : 'Ürünü Kaydet ↗'}
              </button>
            </form>

   </section>




          <div className="seller-dashboard__products">
            <div className="seller-dashboard__section-heading">
              <div>
                <span>ÜRÜN YÖNETİMİ</span>
                <h2>Ürünlerim</h2>
              </div>

              <button
                type="button"
                onClick={() =>
                  setRefreshKey((value) => value + 1)
                }
              >
                ↻ Yenile
              </button>
            </div>

            {products.length === 0 ? (
              <p className="seller-dashboard__message">
                Henüz mağazana ürün eklemedin.
              </p>
            ) : (
              <div className="seller-dashboard__table-wrap">
                <table className="seller-dashboard__table">
                  <thead>
                    <tr>
                      <th>Ürün</th>
                      <th>Fiyat</th>
                      <th>Stok</th>
                      <th>Durum</th>
                      <th>İşlemler</th>
                    </tr>
                  </thead>

                  <tbody>
                    {products.map((product) => (
                      <SellerProductRow
                        key={product.id}
                        product={product}
                        catalogFilters={catalogFilters}
                        token={token}
                        onUpdated={() =>
                          setRefreshKey((value) => value + 1)
                        }
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <section className="seller-orders" aria-label="Satıcı siparişleri">
            <div className="seller-dashboard__section-heading">
              <div><span>SİPARİŞ YÖNETİMİ</span><h2>Siparişlerim</h2></div>
            </div>
            {shippingError && <p className="seller-orders__error" role="alert">{shippingError}</p>}
            {orders.length === 0 ? <p className="seller-dashboard__message">Mağazana ait sipariş bulunmuyor.</p> : orders.map((order) => (
              <article className="seller-orders__card" key={order.id}>
                <div className="seller-orders__heading">
                  <div><strong>Sipariş #{order.id}</strong><small>{new Date(order.created_at).toLocaleString('tr-TR')}</small></div>
                  <span>{order.status === 'paid' ? 'Ödendi' : order.status === 'canceled' ? 'İptal edildi' : 'Ödeme bekliyor'}</span>
                </div>
                <p><strong>Teslimat:</strong> {order.shipping_address || 'Adres bilgisi yok'}</p>
                <div className="seller-orders__items">
                  {order.items.map((item) => {
                    const next = nextShippingStatus[item.shipping_status]
                    return <div className="seller-orders__item" key={item.id}>
                      <div><strong>{item.product_name}</strong><small>{item.quantity} adet · {formatPrice(item.unit_price)} · {shippingLabels[item.shipping_status] || item.shipping_status}</small></div>
                      {order.status === 'paid' && next && <button
                        type="button"
                        disabled={shippingBusyId !== null || (next === 'shipped' && !order.shipping_address)}
                        onClick={() => updateShipping(order.id, item.id, next)}
                      >{shippingBusyId === item.id ? 'Kaydediliyor...' : next === 'preparing' ? 'Hazırlamaya başla' : next === 'shipped' ? 'Kargoya ver' : 'Teslim edildi'}</button>}
                    </div>
                  })}
                </div>
                <div className="seller-orders__total">Mağaza tutarı <strong>{formatPrice(order.seller_total)}</strong></div>
              </article>
            ))}
          </section>
        </>
      )}
    </section>
  )
}

export default SellerDashboard
