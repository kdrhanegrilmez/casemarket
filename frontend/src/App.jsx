
import { useEffect, useMemo, useState } from 'react'
import './App.css'
import AuthPage from './components/AuthPage'
import SellerDashboard from './components/SellerDashboard'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '')

const formatPrice = (value) =>
  Number(value).toLocaleString('tr-TR', {
    style: 'currency',
    currency: 'TRY',
  })

function productIdFromPath() {
  const match = window.location.pathname.match(
    /^\/products\/([1-9]\d*)\/?$/
  )

  return match ? Number(match[1]) : null
}

function ProductImage({ product, priority = false }) {
  const [failed, setFailed] = useState(false)

  return (
    <div className="case-image">
      {product?.image_url && !failed ? (
        <img
          src={product.image_url}
          alt={product.name}
          loading={priority ? 'eager' : 'lazy'}
          onError={() => setFailed(true)}
        />
      ) : (
        <div
          className="case-image__fallback"
          aria-label="Ürün görseli bulunamadı"
        >
          <span>CM</span>
        </div>
      )}
    </div>
  )
}

function readSavedCart() {
  try {
    const saved = JSON.parse(
      localStorage.getItem('casemarket-cart-v1') || '[]'
    )

    if (!Array.isArray(saved)) {
      return []
    }

    return saved.filter(
      (item) =>
        Number.isInteger(item.id) &&
        Number.isInteger(item.quantity) &&
        item.quantity > 0 &&
        typeof item.name === 'string' &&
        Number.isFinite(Number(item.price))
    )
  } catch {
    return []
  }
}

function App() {
  // KATALOG
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  // URUN DETAYI
  const [selectedId, setSelectedId] = useState(productIdFromPath)
  const [detail, setDetail] = useState(null)
  const [detailLoading, setDetailLoading] = useState(false)
  const [detailError, setDetailError] = useState('')

  // ARAMA VE FILTRELER
  const [search, setSearch] = useState('')
  const [sortBy, setSortBy] = useState('newest')
  const [onlyAvailable, setOnlyAvailable] = useState(false)

  // SEPET
  const [cart, setCart] = useState(readSavedCart)
  const [cartOpen, setCartOpen] = useState(false)

  // GIRIS VE KAYIT
  const [authMode, setAuthMode] = useState(null)
  const [currentUser, setCurrentUser] = useState(null)

  const [accessToken, setAccessToken] = useState(
    () => sessionStorage.getItem('casemarket-token')
  )

  // SATICI PANELI
  const [sellerPanelOpen, setSellerPanelOpen] = useState(false)

  // OTURUM KONTROLU
  useEffect(() => {
    if (!accessToken) {
      setCurrentUser(null)
      return
    }

    const controller = new AbortController()

    async function checkSession() {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/auth/me`,
          {
            headers: {
              Authorization: `Bearer ${accessToken}`,
            },
            signal: controller.signal,
          }
        )

        if (response.status === 401) {
          sessionStorage.removeItem('casemarket-token')
          setAccessToken(null)
          setCurrentUser(null)
          setSellerPanelOpen(false)
          return
        }

        if (!response.ok) {
          throw new Error('Oturum doğrulanamadı.')
        }

        const user = await response.json()

        if (!controller.signal.aborted) {
          setCurrentUser(user)
        }
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Oturum kontrol hatası:', err)
        }
      }
    }

    checkSession()

    return () => controller.abort()
  }, [accessToken])

  // URUN KATALOGUNU GETIR
  useEffect(() => {
    const controller = new AbortController()

    setLoading(true)
    setError('')

    fetch(`${API_BASE_URL}/api/catalog/products`, {
      signal: controller.signal,
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error('Katalog getirilemedi.')
        }

        return response.json()
      })
      .then((data) => {
        if (!Array.isArray(data)) {
          throw new Error('Geçersiz katalog verisi.')
        }

        setProducts(data)
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setError(
            'Ürünler yüklenemedi. Backend bağlantısını kontrol et.'
          )
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      })

    return () => controller.abort()
  }, [reloadKey])

  // URUN DETAYINI GETIR
  useEffect(() => {
    if (selectedId === null) {
      setDetail(null)
      return
    }

    const controller = new AbortController()

    setDetail(null)
    setDetailLoading(true)
    setDetailError('')

    fetch(
      `${API_BASE_URL}/api/catalog/products/${selectedId}`,
      { signal: controller.signal }
    )
      .then((response) => {
        if (response.status === 404) {
          throw new Error(
            'Bu ürün bulunamadı veya artık yayında değil.'
          )
        }

        if (!response.ok) {
          throw new Error('Ürün bilgileri yüklenemedi.')
        }

        return response.json()
      })
      .then((data) => {
        if (!controller.signal.aborted) {
          setDetail(data)
        }
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setDetailError(err.message)
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) {
          setDetailLoading(false)
        }
      })

    return () => controller.abort()
  }, [selectedId])

  // TARAYICI GERI / ILERI TUSLARI
  useEffect(() => {
    function handleHistory() {
      setSelectedId(productIdFromPath())
      setAuthMode(null)
      setSellerPanelOpen(false)
      setDetail(null)
      setCartOpen(false)
      window.scrollTo(0, 0)
    }

    window.addEventListener('popstate', handleHistory)

    return () => {
      window.removeEventListener('popstate', handleHistory)
    }
  }, [])

  // KOLEKSIYONA DONUS
  useEffect(() => {
    if (
      selectedId === null &&
      !sellerPanelOpen &&
      !authMode &&
      window.location.hash === '#koleksiyon'
    ) {
      document.getElementById('koleksiyon')?.scrollIntoView()
    }
  }, [selectedId, sellerPanelOpen, authMode])

  // SAYFA BASLIGI
  useEffect(() => {
    document.title = detail?.name
      ? `${detail.name} | CaseMarket`
      : 'CaseMarket | Premium Telefon Kılıfları'
  }, [detail])

  // SEPETI KAYDET
  useEffect(() => {
    try {
      localStorage.setItem(
        'casemarket-cart-v1',
        JSON.stringify(cart)
      )
    } catch {
      // Depolama kapaliysa uygulama calismaya devam eder.
    }
  }, [cart])

  // ESC ILE SEPETI KAPAT
  useEffect(() => {
    if (!cartOpen) return undefined

    function closeOnEscape(event) {
      if (event.key === 'Escape') {
        setCartOpen(false)
      }
    }

    document.addEventListener('keydown', closeOnEscape)
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', closeOnEscape)
      document.body.style.overflow = ''
    }
  }, [cartOpen])

  // ARAMA, FILTRELEME VE SIRALAMA
  const visibleProducts = useMemo(() => {
    const text = search.trim().toLocaleLowerCase('tr-TR')

    const filtered = products.filter((product) => {
      const searchable = [
        product.name,
        product.description,
        product.store_name,
      ]
        .filter(Boolean)
        .join(' ')
        .toLocaleLowerCase('tr-TR')

      return (
        (!text || searchable.includes(text)) &&
        (!onlyAvailable || Number(product.stock) > 0)
      )
    })

    return [...filtered].sort((a, b) => {
      if (sortBy === 'price-low') {
        return Number(a.price) - Number(b.price)
      }

      if (sortBy === 'price-high') {
        return Number(b.price) - Number(a.price)
      }

      if (sortBy === 'name') {
        return a.name.localeCompare(b.name, 'tr')
      }

      return Number(b.id) - Number(a.id)
    })
  }, [products, search, onlyAvailable, sortBy])

  // SEPET HESAPLAMALARI
  const cartCount = cart.reduce(
    (sum, item) => sum + item.quantity,
    0
  )

  const cartTotalCents = cart.reduce(
    (sum, item) =>
      sum +
      Math.round(Number(item.price) * 100) * item.quantity,
    0
  )

  // URUN DETAY SAYFASINI AC
  function openProduct(id) {
    setAuthMode(null)
    setSellerPanelOpen(false)
    setCartOpen(false)

    window.history.pushState({}, '', `/products/${id}`)

    setSelectedId(id)
    window.scrollTo(0, 0)
  }

  // ANA SAYFAYA DON
  function goHome(toCollection = false) {
    setAuthMode(null)
    setSellerPanelOpen(false)
    //ana sayfaya dönerken kataloğu backend'den yüklememiz greiyor
    setReloadKey((previousValue)=>previousValue+1)

    const url = toCollection ? '/#koleksiyon' : '/'

    window.history.pushState({}, '', url)

    setSelectedId(null)
    setDetail(null)

    if (toCollection) {
      window.requestAnimationFrame(() => {
        window.requestAnimationFrame(() => {
          document
            .getElementById('koleksiyon')
            ?.scrollIntoView({ behavior: 'smooth' })
        })
      })
    } else {
      window.scrollTo({
        top: 0,
        behavior: 'smooth',
      })
    }
  }

  // GIRIS VEYA KAYIT EKRANINI AC
  function openAuth(mode = 'login') {
    setAuthMode(mode)
    setSellerPanelOpen(false)
    setCartOpen(false)
    window.scrollTo(0, 0)
  }

  // BASARILI GIRIS
  function handleAuthenticated(token, user) {
    sessionStorage.setItem('casemarket-token', token)

    setAccessToken(token)
    setCurrentUser(user)

    goHome()
  }

  // CIKIS YAP
  function handleLogout() {
    sessionStorage.removeItem('casemarket-token')

    setAccessToken(null)
    setCurrentUser(null)
    setSellerPanelOpen(false)

    goHome()
  }

  // SATICI PANELINI AC
  function openSellerPanel() {
    if (
      currentUser?.role !== 'seller' ||
      !accessToken
    ) {
      return
    }

    setAuthMode(null)
    setSelectedId(null)
    setDetail(null)
    setCartOpen(false)
    setSellerPanelOpen(true)

    window.scrollTo(0, 0)
  }

  // SEPETE URUN EKLE
  function addToCart(product) {
    if (Number(product.stock) < 1) return

    setCart((current) => {
      const existing = current.find(
        (item) => item.id === product.id
      )

      if (
        existing &&
        existing.quantity >= Number(product.stock)
      ) {
        return current
      }

      const nextItem = {
        id: product.id,
        name: product.name,
        price: product.price,
        image_url: product.image_url,
        stock: Number(product.stock),
        quantity: existing ? existing.quantity + 1 : 1,
      }

      if (existing) {
        return current.map((item) =>
          item.id === product.id ? nextItem : item
        )
      }

      return [...current, nextItem]
    })

    setCartOpen(true)
  }

  // SEPETTEKI URUN ADEDI
  function changeQuantity(productId, change) {
    setCart((current) =>
      current
        .map((item) => {
          if (item.id !== productId) {
            return item
          }

          const quantity = Math.max(
            0,
            Math.min(
              item.stock || 0,
              item.quantity + change
            )
          )

          return {
            ...item,
            quantity,
          }
        })
        .filter((item) => item.quantity > 0)
    )
  }

  // SEPETTEN URUN CIKAR
  function removeFromCart(productId) {
    setCart((current) =>
      current.filter(
        (item) => item.id !== productId
      )
    )
  }

  const featuredProduct = products[0]

  return (
    <div className="site">

      {/* UST DUYURU */}
      <div className="announcement">
        <span
          className="announcement__dot"
          aria-hidden="true"
        />
        TARZININ DEVAMI · YENİ NESİL AKSESUAR PAZARYERİ
      </div>

      {/* UST MENU */}
      <header className="site-header">

        <a
          className="brand"
          href="/"
          onClick={(event) => {
            event.preventDefault()
            goHome()
          }}
          aria-label="CaseMarket ana sayfa"
        >
          <span className="brand__mark">
            C<span>M</span>
          </span>

          <span className="brand__text">
            CASE<span>MARKET</span>
            <small>STUDIO & ACCESSORIES</small>
          </span>
        </a>

        <nav
          className="site-nav"
          aria-label="Ana menü"
        >
          <a
            href="/#koleksiyon"
            onClick={(event) => {
              event.preventDefault()
              goHome(true)
            }}
          >
            Koleksiyon
          </a>

          <a href="#hakkimizda">
            Hakkımızda
          </a>
        </nav>

        <div className="header-actions">

          {/* GIRIS, CIKIS VE SATICI PANELI */}
          {currentUser ? (
            <>
              <span className="auth-welcome">
                Merhaba, {currentUser.full_name}
              </span>

              {currentUser.role === 'seller' && (
                <button
                  type="button"
                  className="auth-nav-button"
                  onClick={openSellerPanel}
                >
                  Satıcı Paneli
                </button>
              )}

              <button
                type="button"
                className="auth-nav-button"
                onClick={handleLogout}
              >
                Çıkış Yap
              </button>
            </>
          ) : (
            <button
              type="button"
              className="auth-nav-button"
              onClick={() => openAuth('login')}
            >
              Giriş Yap
            </button>
          )}

          <a
            href="/#koleksiyon"
            className="header-explore"
            onClick={(event) => {
              event.preventDefault()
              goHome(true)
            }}
          >
            Keşfet <span>↗</span>
          </a>

          <button
            className="cart-button"
            type="button"
            onClick={() => setCartOpen(true)}
          >
            <svg
              aria-hidden="true"
              width="21"
              height="21"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.6"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <path d="M5 8h14l1 12H4L5 8Z" />
              <path d="M9 9V6a3 3 0 0 1 6 0v3" />
            </svg>

            <span>Sepet</span>

            <span className="cart-button__count">
              {cartCount}
            </span>
          </button>

        </div>
      </header>

      <main>

        {/* GIRIS VE KAYIT EKRANI */}
        {authMode ? (

          <AuthPage
            mode={authMode}
            onModeChange={setAuthMode}
            onAuthenticated={handleAuthenticated}
          />

        ) : sellerPanelOpen &&
            currentUser?.role === 'seller' ? (

          /* SATICI PANELI */
          <SellerDashboard
            token={accessToken}
            user={currentUser}
            onBack={() => goHome(true)}
          />

        ) : selectedId !== null ? (

          /* URUN DETAY SAYFASI */
          <section className="detail-page">

            <div className="detail-page__breadcrumb">
              <button
                type="button"
                onClick={() => goHome(true)}
              >
                ← Koleksiyona dön
              </button>

              <span>
                CASEMARKET / ÜRÜN DETAYI
              </span>
            </div>

            {detailLoading && (
              <p className="status-message">
                Ürün yükleniyor...
              </p>
            )}

            {detailError && (
              <div
                className="status-message status-message--error"
                role="alert"
              >
                <p>{detailError}</p>

                <button
                  type="button"
                  className="button button--dark"
                  onClick={() => goHome(true)}
                >
                  Ürünlere dön
                </button>
              </div>
            )}

            {detail && !detailLoading && (

              <div className="detail-layout">

                <div className="detail-image-panel">

                  <ProductImage
                    key={detail.id}
                    product={detail}
                    priority
                  />

                  <span className="detail-image-panel__tag">
                    CASEMARKET SELECT
                  </span>

                </div>

                <div className="detail-content">

                  <span className="overline">
                    DETAYLAR / {String(detail.id).padStart(2, '0')}
                  </span>

                  <p className="detail-content__store">
                    {detail.store_name}
                  </p>

                  <h1>{detail.name}</h1>

                  <div className="detail-content__rule" />

                  <p className="detail-content__description">
                    {detail.description ||
                      'Bu ürün için henüz bir açıklama eklenmedi.'}
                  </p>

                  <strong className="detail-content__price">
                    {formatPrice(detail.price)}
                  </strong>

                  <p
                    className={`availability ${
                      Number(detail.stock) === 0
                        ? 'availability--empty'
                        : ''
                    }`}
                  >
                    <span className="availability__dot" />

                    {Number(detail.stock) === 0
                      ? 'Stokta yok'
                      : `Stokta ${detail.stock} adet mevcut`}
                  </p>

                  <button
                    type="button"
                    className="button button--dark detail-content__add"
                    disabled={
                      Number(detail.stock) === 0 ||
                      cart.some(
                        (item) =>
                          item.id === detail.id &&
                          item.quantity >= Number(detail.stock)
                      )
                    }
                    onClick={() => addToCart(detail)}
                  >
                    <span>Sepete ekle</span>
                    <span aria-hidden="true">↗</span>
                  </button>

                  <div className="detail-note">
                    <span>◈</span>

                    <p>
                      Özenle seçilmiş tasarımlar.
                      Gösterilen fiyatlar demo amaçlıdır.
                    </p>
                  </div>

                </div>
              </div>
            )}

          </section>

        ) : (

          /* ANA SAYFA */
          <>

            {/* HERO */}
            <section className="hero">

              <div className="hero__copy">

                <span className="hero__overline">
                  <span className="hero__star">✳</span>
                  2026 / YENİ KOLEKSİYON
                </span>

                <h1>
                  Her detayda
                  <br />
                  <em>bir duruş.</em>
                </h1>

                <p>
                  Günlük stilini tamamlayan özgün
                  tasarımlar. Birbirinden özel telefon
                  kılıflarını CaseMarket'te keşfet.
                </p>

                <button
                  className="button button--light"
                  type="button"
                  onClick={() => goHome(true)}
                >
                  Koleksiyonu keşfet
                  <span aria-hidden="true">↗</span>
                </button>

                <div className="hero__bottom">
                  <span className="hero__dash" />
                  FORM. FUNCTION. FEEL.
                </div>

              </div>

              <div className="hero__stage">

                <div className="hero__orbit hero__orbit--outer" />
                <div className="hero__orbit hero__orbit--inner" />

                <div className="hero__feature">

                  {featuredProduct ? (
                    <ProductImage
                      key={featuredProduct.id}
                      product={featuredProduct}
                      priority
                    />
                  ) : (
                    <div className="hero__placeholder">
                      CM
                    </div>
                  )}

                </div>

                <div className="hero__side-label">
                  THE EVERYDAY EDITION — CASEMARKET
                </div>

                <div className="hero__index">
                  <strong>01</strong>
                  <span>/ PREMIUM EDITION</span>
                </div>

              </div>
            </section>

            {/* OZELLIK SERIDI */}
            <div
              className="value-strip"
              aria-label="CaseMarket özellikleri"
            >
              <span>
                01 <strong>ÖZENLE SEÇİLEN ÜRÜNLER</strong>
              </span>

              <span className="value-strip__separator" />

              <span>
                02 <strong>BAĞIMSIZ MAĞAZALAR</strong>
              </span>

              <span className="value-strip__separator" />

              <span>
                03 <strong>ZAMANSIZ TASARIM</strong>
              </span>
            </div>

            {/* KATALOG */}
            <section
              className="collection"
              id="koleksiyon"
            >

              <div className="section-heading">

                <div>

                  <span className="overline">
                    <span className="overline__diamond">
                      ◆
                    </span>
                    CASEMARKET EDIT
                  </span>

                  <h2>
                    Tarzının <em>devamı.</em>
                  </h2>

                  <p>
                    Yeni favorini bul.
                    Her tarz için bir detay.
                  </p>

                </div>

                <span className="section-heading__count">
                  {products.length.toString().padStart(2, '0')} ÜRÜN
                </span>

              </div>

              {/* ARAMA VE FILTRE */}
              <div className="catalog-toolbar">

                <label className="catalog-search">

                  <svg
                    aria-hidden="true"
                    width="19"
                    height="19"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.7"
                    strokeLinecap="round"
                  >
                    <circle cx="11" cy="11" r="7" />
                    <path d="m16 16 5 5" />
                  </svg>

                  <span className="sr-only">
                    Ürün ara
                  </span>

                  <input
                    type="search"
                    value={search}
                    onChange={(event) =>
                      setSearch(event.target.value)
                    }
                    placeholder="Kılıf veya mağaza ara..."
                  />

                </label>

                <div className="catalog-toolbar__right">

                  <label className="stock-filter">

                    <input
                      type="checkbox"
                      checked={onlyAvailable}
                      onChange={(event) =>
                        setOnlyAvailable(event.target.checked)
                      }
                    />

                    <span>Yalnızca stoktakiler</span>

                  </label>

                  <label className="sort-select">

                    <span className="sr-only">
                      Sıralama
                    </span>

                    <select
                      value={sortBy}
                      onChange={(event) =>
                        setSortBy(event.target.value)
                      }
                    >
                      <option value="newest">
                        Yeniden eskiye
                      </option>

                      <option value="price-low">
                        Fiyat: Artan
                      </option>

                      <option value="price-high">
                        Fiyat: Azalan
                      </option>

                      <option value="name">
                        İsme göre A-Z
                      </option>
                    </select>

                  </label>

                </div>
              </div>

              <div className="catalog-results">

                <span>
                  {visibleProducts.length} ürün gösteriliyor
                </span>

                <span>
                  KAŞİFLERİN SEÇKİSİ — 2026
                </span>

              </div>

              {loading && (
                <p className="status-message">
                  Ürünler yükleniyor...
                </p>
              )}

              {error && (
                <div
                  className="status-message status-message--error"
                  role="alert"
                >
                  <p>{error}</p>

                  <button
                    className="button button--dark"
                    type="button"
                    onClick={() =>
                      setReloadKey((key) => key + 1)
                    }
                  >
                    Tekrar dene
                  </button>
                </div>
              )}

              {!loading &&
                !error &&
                visibleProducts.length === 0 && (
                  <div className="status-message">
                    Aradığın özelliklerde ürün bulunamadı.
                  </div>
                )}

              {/* URUN KARTLARI */}
              <div className="product-grid">

                {visibleProducts.map((product, index) => (

                  <article
                    className="product-card"
                    key={product.id}
                  >

                    <div className="product-card__visual">

                      <button
                        type="button"
                        className="product-card__image-button"
                        onClick={() =>
                          openProduct(product.id)
                        }
                        aria-label={`${product.name} ürün detayını aç`}
                      >
                        <ProductImage
                          key={product.id}
                          product={product}
                        />
                      </button>

                      <span className="product-card__number">
                        {String(index + 1).padStart(2, '0')}
                      </span>

                      {Number(product.stock) === 0 && (
                        <span className="product-card__soldout">
                          TÜKENDİ
                        </span>
                      )}

                    </div>

                    <div className="product-card__content">

                      <span className="product-card__store">
                        {product.store_name}
                      </span>

                      <h3>
                        <button
                          type="button"
                          onClick={() =>
                            openProduct(product.id)
                          }
                        >
                          {product.name}
                        </button>
                      </h3>

                      <p className="product-card__description">
                        {product.description ||
                          'Özenle seçilmiş tasarım.'}
                      </p>

                      <div className="product-card__bottom">

                        <strong>
                          {formatPrice(product.price)}
                        </strong>

                        <span
                          className={
                            Number(product.stock) === 0
                              ? 'product-card__stock product-card__stock--empty'
                              : 'product-card__stock'
                          }
                        >
                          {Number(product.stock) === 0
                            ? 'Tükendi'
                            : `${product.stock} adet`}
                        </span>

                      </div>

                    </div>

                    <button
                      className="product-card__add"
                      type="button"
                      disabled={
                        Number(product.stock) === 0 ||
                        cart.some(
                          (item) =>
                            item.id === product.id &&
                            item.quantity >= Number(product.stock)
                        )
                      }
                      onClick={() => addToCart(product)}
                    >
                      <span>
                        {Number(product.stock) === 0
                          ? 'Stokta yok'
                          : 'Sepete ekle'}
                      </span>

                      <span aria-hidden="true">↗</span>

                    </button>

                  </article>

                ))}

              </div>
            </section>

            {/* ALT TANITIM */}
            <section className="editorial">

              <div className="editorial__symbol">
                ✳
              </div>

              <div>
                <span className="overline">
                  LESS IS MORE
                </span>

                <h2>
                  Günlük olanı <em>özel kılan</em> detaylar.
                </h2>
              </div>

              <button
                type="button"
                className="editorial__link"
                onClick={() => goHome(true)}
              >
                Koleksiyonu incele ↗
              </button>

            </section>

          </>
        )}

      </main>

      {/* FOOTER */}
      <footer
        className="site-footer"
        id="hakkimizda"
      >

        <div>

          <span className="site-footer__brand">
            CASE<span>MARKET</span>
          </span>

          <p>
            Günlük yaşamın estetiği,
            küçük detaylarda saklı.
          </p>

        </div>

        <div className="site-footer__right">

          <span>
            © 2026 CASEMARKET · DEMO PROJE
          </span>

          <a
            href="https://amazon-berkeley-objects.s3.us-east-1.amazonaws.com/index.html"
            target="_blank"
            rel="noreferrer"
          >
            Ürün görselleri: Amazon Berkeley Objects
            (CC BY 4.0) ↗
          </a>

        </div>

      </footer>

      {/* SAGDAN ACILAN SEPET */}
      {cartOpen && (

        <div className="cart-layer">

          <button
            type="button"
            className="cart-backdrop"
            aria-label="Sepeti kapat"
            onClick={() => setCartOpen(false)}
          />

          <aside
            className="cart-drawer"
            role="dialog"
            aria-modal="true"
            aria-label="Alışveriş sepeti"
          >

            <div className="cart-drawer__heading">

              <div>

                <span className="overline">
                  CASEMARKET
                </span>

                <h2>
                  Sepetim <span>({cartCount})</span>
                </h2>

              </div>

              <button
                className="cart-drawer__close"
                type="button"
                aria-label="Sepeti kapat"
                onClick={() => setCartOpen(false)}
              >
                ✕
              </button>

            </div>

            {cart.length === 0 ? (

              <div className="cart-empty">

                <span aria-hidden="true">◇</span>

                <h3>
                  Sepetin henüz boş.
                </h3>

                <p>
                  Favori telefon kılıfını
                  koleksiyonda keşfet.
                </p>

                <button
                  type="button"
                  className="button button--dark"
                  onClick={() => {
                    setCartOpen(false)
                    goHome(true)
                  }}
                >
                  Ürünlere göz at ↗
                </button>

              </div>

            ) : (

              <>
                <div className="cart-drawer__items">

                  {cart.map((item) => (

                    <div
                      className="cart-item"
                      key={item.id}
                    >

                      <div className="cart-item__image">

                        <ProductImage
                          key={item.id}
                          product={item}
                        />

                      </div>

                      <div className="cart-item__body">

                        <h3>{item.name}</h3>

                        <strong>
                          {formatPrice(item.price)}
                        </strong>

                        <div className="cart-item__actions">

                          <div
                            className="quantity-control"
                            aria-label="Ürün adedi"
                          >

                            <button
                              type="button"
                              aria-label="Adedi azalt"
                              onClick={() =>
                                changeQuantity(item.id, -1)
                              }
                            >
                              −
                            </button>

                            <span>{item.quantity}</span>

                            <button
                              type="button"
                              aria-label="Adedi artır"
                              disabled={
                                item.quantity >= item.stock
                              }
                              onClick={() =>
                                changeQuantity(item.id, 1)
                              }
                            >
                              +
                            </button>

                          </div>

                          <button
                            type="button"
                            className="cart-item__remove"
                            onClick={() =>
                              removeFromCart(item.id)
                            }
                          >
                            Kaldır
                          </button>

                        </div>

                      </div>

                    </div>

                  ))}

                </div>

                <div className="cart-drawer__summary">

                  <div className="cart-drawer__subtotal">

                    <span>Ara toplam</span>

                    <strong>
                      {formatPrice(cartTotalCents / 100)}
                    </strong>

                  </div>

                  <p>
                    Sipariş ve ödeme adımı bir sonraki
                    geliştirmede eklenecek.
                  </p>

                  <button
                    className="button button--dark"
                    type="button"
                    onClick={() => setCartOpen(false)}
                  >
                    Alışverişe devam et
                    <span>↗</span>
                  </button>

                </div>

              </>
            )}

          </aside>

        </div>

      )}

    </div>
  )
}

export default App
