
import {useEffect,useState} from "react";
//useState: Ürün listesini React'in hafızasınad tutacak
//useEffect: Sayfa açıldığında FastAPI'den ürünleri isteyecek.

import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000'

const formatPrice = (price) =>
  Number(price).toLocaleString('tr-TR', {
    style: 'currency',
    currency: 'TRY',
  })

function App() {

  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [cart,setCart]=useState([])//cart: sepete eklediğimiz ürünlerin listesi
  //useState([]): burada yaptığımız olay da şu sepetin başlangıçta boş olduğunu doğruluyoruz.
  const [cartOpen, setCartOpen] = useState(false) //Sepet panalinin açık olup olmadığını kontrol eder.
  //setCartOpen ile sepeti açıp kapatmamızı sağlar, false vermemizin ssebebi ise sayfa ilk açıldığında sepet kısmı kapalı gözükmeli




  //Sepete ekleme fonksiyonu yazalım:
function addToCart(product) {
  setCart((currentCart) => {
    const quantity = currentCart.filter(
      (item) => item.id === product.id
    ).length

    if (quantity >= product.stock) {
      return currentCart
    }

    return [...currentCart, product]
  })
}
function removeFromCart(indexToRemove) {
  setCart((currentCart) =>
    currentCart.filter(
      (item, index) => index !== indexToRemove
    )
  )
}



  useEffect(() => {
    fetch(`${API_BASE_URL}/api/catalog/products`)
      .then((response) => {
        if (!response.ok) {
          throw new Error('Urunler getirilemedi')
        }

        return response.json()
      })
      .then((data) => {
        setProducts(data)
      })
      .catch(() => {
        setError('Urunler yuklenirken bir hata olustu.')
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  const cartTotalKurus = cart.reduce(
      (total,item) => total +Math.round(Number(item.price)*100),
      0
  )

  const formattedCartTotal = (cartTotalKurus/100).toLocaleString(
      'tr-TR',{
        minimumFractionDigits:2,
        maximumFractionDigits:2
      }
  )


  return (
    <div className="site">

      <div className="top-strip">
        CASEMARKET — PREMIUM AKSESUAR DENEYİMİ
      </div>

      <header className="site-header">
        <a href="#" className="logo">
          CASE<span>MARKET</span>
        </a>

        <nav className="navigation">
          <a href="#koleksiyon">Koleksiyon</a>
          <a href="#hakkimizda">Hakkımızda</a>

        </nav>

        <div className="header-actions">
          <a className="header-action" href="#koleksiyon">
          Keşfet ↗
          </a>

         <button
           type="button"
           className="cart-count cart-toggle"
           onClick={() => setCartOpen((open) => !open)}
           aria-expanded={cartOpen}
           >
           Sepet ({cart.length})
         </button>

        </div>

      </header>

      {cartOpen && (
          <section className="cart-panel" aria-label="Sepetim">
            <div className="cart-panel-header">
              <h2>Sepetim</h2>

              <button
                type="button"
                className="cart-close"
                onClick={()=>setCartOpen(false)}
                >
                Kapat ✕
              </button>
            </div>

            {cart.length === 0 ?(
                <p>Sepetin henüz boş.</p>
            ) :(
                <ul className="cart-items">
                  {cart.map((item, index)=>(
                      <li
                        key={`${item.id}-${index}`}
                        className="cart-item"
                        >
                        <div>
                          <strong>{item.name}</strong>
                          <p>{formatPrice(item.price)}</p>
                        </div>

                        <button
                          type="button"
                          className="cart-remove"
                          onClick={()=> removeFromCart(index)}
                          >
                          Çıkar
                        </button>
                      </li>
                  ))}
                </ul>
            )}

            {cart.length >0 && (
                <div className="cart-summary">
                  <span>Toplam Tutar</span>
                  <strong>{formattedCartTotal} TL</strong>
                </div>
            )}


          </section>
      )
      }


      <main>
        <section className="hero">

          <div className="hero-content">
            <p className="eyebrow">
              ◆ YENİ NESİL AKSESUAR PAZARYERİ
            </p>

            <h1>
              Günlük tarzına
              <br />
              <em>premium dokunuş.</em>
            </h1>

            <p className="hero-description">
              Tarzını tamamlayan özel tasarımlar.
              Seçkin satıcıların ürünlerini tek bir
              yerde keşfet.
            </p>

            <a className="primary-button" href="#koleksiyon">
              Koleksiyonu keşfet <span>↗</span>
            </a>
          </div>

          <div className="hero-visual" aria-hidden="true">
            <div className="halo"></div>

            <div className="phone">
              <div className="camera">
                <i></i>
                <i></i>
                <i></i>
              </div>

              <div className="phone-logo">CM</div>
            </div>

            <p className="visual-label">
              DESIGNED FOR EVERYDAY
            </p>
          </div>

        </section>


<section id="koleksiyon" className="collection">
  <p className="section-label">ÖZENLE SEÇİLDİ</p>

  <h2>Tarzının devamı.</h2>

  <p>Seçkin satıcılarımızın öne çıkan ürünleri.</p>

  {loading && <p>Ürünler yükleniyor...</p>}
  {error && <p role="alert">{error}</p>}

  <div className="product-grid">
    {products.map((product) => (
      <article className="product-card" key={product.id}>

        <div className="product-visual">
          <img
            src={product.image_url}
            alt={product.name}
            loading="lazy"
            onError={(event) => {
              event.currentTarget.hidden = true
              event.currentTarget.nextElementSibling.hidden = false
            }}
          />
          <div className="product-image-fallback" hidden aria-hidden="true">
            CM
          </div>
        </div>

        <div className="product-info">
          <span className="product-seller">
            {product.store_name}
          </span>

          <h3>{product.name}</h3>
          <p className="product-description">{product.description}</p>

          <div className="product-bottom">
            <strong>{formatPrice(product.price)}</strong>
            <span className={product.stock === 0 ? 'out-of-stock' : ''}>
              {product.stock === 0 ? 'Tükendi' : `Stok: ${product.stock}`}
            </span>
          </div>
        </div>

        <button
          type="button"
          className="add-to-cart"
          disabled={product.stock === 0 }
          onClick={()=>addToCart(product)}
        >
          {product.stock === 0 ? 'Stokta Yok' : 'Sepete Ekle +'}
        </button>
      </article>
    ))}
  </div>
</section>

      </main>

      <footer id="hakkimizda">
        <strong>CASEMARKET</strong>
        <span>Modern aksesuar pazaryeri.</span>
      </footer>

    </div>
  )
}

export default App
