
import { useEffect, useState } from 'react'
import './SellerDashboard.css'
import './components.css'
import SellerProductRow from './SellerProductRow.jsx'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ||
  'http://127.0.0.1:8000'
).replace(/\/$/, '')

function SellerDashboard({ token, user, onBack }) {
  const [store, setStore] = useState(null)
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [refreshKey, setRefreshKey] = useState(0)
  const [saving,setSaving]=useState(false)
  const [createMessage, setCreateMessage] =useState('')

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

        const [storeResponse, productsResponse] =
          await Promise.all([
            fetch(`${API_BASE_URL}/api/sellers/me`, {
              headers,
              signal: controller.signal,
            }),
            fetch(`${API_BASE_URL}/api/sellers/me/products`, {
              headers,
              signal: controller.signal,
            }),
          ])

        if (
          storeResponse.status === 401 ||
          productsResponse.status === 401
        ) {
          throw new Error(
            'Oturum süren dolmuş. Çıkış yapıp yeniden giriş yap.'
          )
        }

        if (!storeResponse.ok || !productsResponse.ok) {
          throw new Error(
            'Mağaza bilgileri getirilemedi.'
          )
        }

        const [storeData, productData] =
          await Promise.all([
            storeResponse.json(),
            productsResponse.json(),
          ])

        if (!Array.isArray(productData)) {
          throw new Error('Ürün listesi geçersiz.')
        }

        if (!controller.signal.aborted) {
          setStore(storeData)
          setProducts(productData)
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
        name.length <2 ||
        !Number.isFinite(price) ||
        price <=0 ||
        !Number.isInteger(stock) ||
        stock <0
    ){
      setCreateMessage('Ürün adı,fiyat veya stok bilgisi geçersiz')
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
              category_id:null,
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

  const activeCount = products.filter(
    (product) => product.is_active
  ).length

  const totalStock = products.reduce(
    (total, product) =>
      total + Number(product.stock),
    0
  )

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
                     minLength={2}
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
                <label className="seller-created__field" style={{display:'flex',flexDirection:'column',gap:'8px'}}>
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
                  <input
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
                  placeholder="/products/case-001.webp"
                      maxLength={500}
                  />

                </label>


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
                disabled={saving}
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
        </>
      )}
    </section>
  )
}

export default SellerDashboard
