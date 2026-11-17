import { useEffect, useState } from 'react'
import './AccountPage.css'
import './AdminDashboard.css'
import ThreadCenter from './ThreadCenter'
import useSupportUnread from './useSupportUnread'
import UnreadBadge from './UnreadBadge'

const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '')

const PAGE_SIZE = 25
const price = new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY' })
const date = new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeStyle: 'short' })
const roleLabel = { customer: 'Müşteri', seller: 'Satıcı', admin: 'Yönetici' }
const storeLabel = { pending: 'Onay bekliyor', approved: 'Onaylandı', rejected: 'Reddedildi' }
const shippingLabel = { pending: 'Bekliyor', preparing: 'Hazırlanıyor', shipped: 'Kargoda', delivered: 'Teslim edildi' }
const shortDate = new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'short' })

const iconPaths = {
  support: <path d="M21 11a8 8 0 0 1-8 8H7l-5 3V11a9 9 0 0 1 19 0ZM7 10h10M7 14h6" />,
  overview: <><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /></>,
  sales: <><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M8 7V5a4 4 0 0 1 8 0v2" /></>,
  stores: <><path d="M3 10h18l-2-6H5l-2 6Z" /><path d="M5 10v10h14V10M9 20v-6h6v6" /></>,
  sellers: <><circle cx="9" cy="8" r="3" /><path d="M3 20v-2a6 6 0 0 1 12 0v2M17 11a3 3 0 1 0 0-6M17 14a5 5 0 0 1 4 5v1" /></>,
  users: <><circle cx="12" cy="8" r="4" /><path d="M4 21v-2a8 8 0 0 1 16 0v2" /></>,
  products: <><path d="m12 2 9 5-9 5-9-5 9-5ZM3 7v10l9 5 9-5V7M12 12v10" /></>,
  phones: <><rect x="6" y="2" width="12" height="20" rx="2" /><path d="M11 18h2" /></>,
  revenue: <><rect x="2" y="5" width="20" height="14" rx="2" /><path d="M2 9h20M16 15h3" /></>,
}

function Icon({ name, size = 18 }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{iconPaths[name]}</svg>
}

const users = {
  path: 'users',
  columns: ['ID', 'Ad soyad', 'E-posta', 'Rol', 'Kayıt tarihi'],
  cells: (user) => [
    user.id, user.full_name, user.email, roleLabel[user.role],
    date.format(new Date(user.created_at)),
  ],
}

function CommissionEditor({ store, token, onUnauthorized, onSaved }) {
  const [value, setValue] = useState(store.commission_rate_percent ?? '')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState(false)

  if (store.approval_status !== 'approved') {
    return <span className="admin-dashboard__muted">Onay sonrası ayarlanır</span>
  }

  async function save(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    setSaved(false)
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/stores/${store.id}/commission`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ commission_rate_percent: Number(value) }),
      })
      if (response.status === 401) {
        onUnauthorized(token)
        return
      }
      const result = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof result?.detail === 'string' ? result.detail : 'Komisyon oranı kaydedilemedi.')
      onSaved(store.id, result.commission_rate_percent)
      setSaved(true)
    } catch (saveError) {
      setError(saveError.message)
    } finally {
      setSaving(false)
    }
  }

  return <form className="admin-dashboard__commission" onSubmit={save}>
    <label><span className="sr-only">{store.store_name} komisyon oranı</span>
      <input type="number" min="0" max="100" step="0.01" required value={value}
        onChange={(event) => { setValue(event.target.value); setSaved(false); setError('') }} />
      <span aria-hidden="true">%</span>
    </label>
    <button type="submit" disabled={saving || value === '' || (store.commission_rate_percent !== null && Number(value) === Number(store.commission_rate_percent))}>
      {saving ? 'Kaydediliyor' : 'Kaydet'}
    </button>
    {saved && <small className="admin-dashboard__commission-success" role="status">Kaydedildi</small>}
    {error && <small className="admin-dashboard__commission-error" role="alert">{error}</small>}
  </form>
}

function ProductRemovalEditor({ product, token, onUnauthorized, onRemoved, onOpenThread }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  if (product.admin_hidden_at) {
    return <button type="button" className="admin-dashboard__thread-button" disabled={!product.moderation_thread_id}
      onClick={() => onOpenThread(product.moderation_thread_id)}>Destekte aç ↗</button>
  }

  async function remove(event) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/products/${product.id}/remove`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ reason: reason.trim() }),
      })
      if (response.status === 401) {
        onUnauthorized(token)
        return
      }
      const result = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof result?.detail === 'string' ? result.detail : 'Ürün yayından kaldırılamadı.')
      onRemoved(product.id, result.thread_id)
    } catch (removeError) {
      setError(removeError.message)
    } finally {
      setSaving(false)
    }
  }

  if (!open) {
    return <button type="button" className="admin-dashboard__remove-button" onClick={() => setOpen(true)}>Yayından kaldır</button>
  }

  return <form className="admin-dashboard__remove-form" onSubmit={remove}>
    <label>Satıcıya iletilecek gerekçe
      <textarea value={reason} onChange={(event) => setReason(event.target.value)}
        minLength="5" maxLength="500" required rows="3" placeholder="Ürün neden kaldırılıyor?" />
    </label>
    <div>
      <button type="submit" disabled={saving || reason.trim().length < 5}>{saving ? 'Gönderiliyor' : 'Kaldır ve bildir'}</button>
      <button type="button" disabled={saving} onClick={() => { setOpen(false); setError(''); setReason('') }}>Vazgeç</button>
    </div>
    {error && <small role="alert">{error}</small>}
  </form>
}

const sections = {
  overview: { title: 'Genel Bakış', path: 'overview' },
  sales: {
    title: 'Siparişler',
    path: 'sales',
    columns: ['Sipariş', 'Alıcı', 'Tarih', 'Sipariş kalemleri', 'Toplam'],
    cells: (order) => [
      `#${order.id}`, order.customer_name, date.format(new Date(order.created_at)),
      <ul className="admin-dashboard__items">
        {order.items.map((item) => (
          <li key={item.id}>
            <strong>{item.product_name}</strong>
            <small>
              {item.store_name} · {item.quantity} × {price.format(item.unit_price)} · {shippingLabel[item.shipping_status]}
            </small>
          </li>
        ))}
      </ul>,
      price.format(order.total_amount),
    ],
  },
  products: {
    title: 'Ürünler',
    path: 'products',
    columns: ['ID', 'Ürün', 'Mağaza', 'Satıcı', 'Kategori', 'Fiyat', 'Stok', 'Durum', 'İşlem'],
    cells: (product, context) => [
      product.id, product.name, product.store_name,
      <span className="admin-dashboard__seller"><strong>{product.seller_name}</strong><small>{product.seller_email}</small></span>,
      product.category_name || 'Belirlenmedi',
      price.format(product.price), product.stock,
      product.admin_hidden_at ? 'Admin kaldırdı' : product.is_active ? 'Yayında' : 'Gizli',
      <ProductRemovalEditor product={product} {...context} />,
    ],
  },
  sellers: { title: 'Satıcılar', ...users, role: 'seller' },
  stores: {
    title: 'Mağazalar',
    path: 'stores',
    columns: ['ID', 'Mağaza', 'Sahibi', 'Durum', 'Ürün', 'Komisyon oranı'],
    cells: (store, context) => [
      store.id, store.store_name, `${store.owner_name} · ${store.owner_email}`,
      storeLabel[store.approval_status], store.product_count,
      <CommissionEditor store={store} {...context} />,
    ],
  },
  phones: {
    title: 'Telefonlar',
    path: 'phones',
    columns: ['ID', 'Marka', 'Model', 'Uyumlu ürün'],
    cells: (phone) => [phone.id, phone.brand_name, phone.model_name, phone.compatible_products],
  },
  users: { title: 'Müşteriler', ...users, role: 'customer' },
  support: { title: 'Destek' },
}

function Overview({ data }) {
  const stats = [
    { label: 'Toplam sipariş', value: data.paid_orders, icon: 'sales', note: 'Demo ödemesi tamamlanan' },
    { label: 'Toplam satış', value: price.format(data.gross_sales), icon: 'revenue', note: 'Brüt demo satış tutarı' },
    { label: 'Aktif satıcı', value: data.sellers, icon: 'sellers', note: `${data.pending_stores} başvuru bekliyor` },
    { label: 'Ürün sayısı', value: data.products, icon: 'products', note: `${data.approved_stores} onaylı mağazada` },
  ]
  const activity = data.daily_orders || []
  const maxOrders = Math.max(1, ...activity.map((day) => Number(day.orders)))
  const points = activity.map((day, index) => ({
    x: activity.length === 1 ? 300 : 20 + index * 560 / (activity.length - 1),
    y: 158 - Number(day.orders) / maxOrders * 125,
    day,
  }))

  return (
    <div className="admin-dashboard__overview">
      <dl className="admin-dashboard__stats">
        {stats.map(({ label, value, icon, note }) => (
          <div className="admin-dashboard__stat" key={label}>
            <span className="admin-dashboard__stat-icon"><Icon name={icon} /></span>
            <dd>{value}</dd><dt>{label}</dt><small>{note}</small>
          </div>
        ))}
      </dl>

      <div className="admin-dashboard__panel admin-dashboard__activity">
        <div className="admin-dashboard__panel-heading">
          <div><h3>Sipariş hareketleri</h3><p>Son 7 gün · tamamlanan demo siparişler</p></div>
          <span className="admin-dashboard__live"><span /> Gerçek veri</span>
        </div>
        <div className="admin-dashboard__chart" role="img" aria-label={`Son 7 günde günlük sipariş sayıları: ${activity.map(({ day, orders }) => `${shortDate.format(new Date(`${day}T12:00:00`))} ${orders}`).join(', ')}`}>
          <svg viewBox="0 0 600 180" preserveAspectRatio="none" aria-hidden="true">
            {[33, 95, 158].map((y) => <line key={y} x1="20" y1={y} x2="580" y2={y} className="admin-dashboard__grid-line" />)}
            <polyline points={points.map(({ x, y }) => `${x},${y}`).join(' ')} className="admin-dashboard__chart-line" />
            {points.map(({ x, y, day }) => <circle key={day.day} cx={x} cy={y} r="4" className="admin-dashboard__chart-dot" />)}
          </svg>
        </div>
        <div className="admin-dashboard__chart-labels">
          {activity.map(({ day }) => <span key={day}>{shortDate.format(new Date(`${day}T12:00:00`))}</span>)}
        </div>
      </div>

      <div className="admin-dashboard__panel">
        <div className="admin-dashboard__panel-heading">
          <div><h3>Son siparişler</h3><p>En son tamamlanan demo ödemeler</p></div>
        </div>
        {data.recent_orders?.length ? (
          <ul className="admin-dashboard__recent-orders">
            {data.recent_orders.map((order) => <li key={order.id}>
              <span className="admin-dashboard__order-symbol"><Icon name="sales" size={16} /></span>
              <span><strong>#{order.id} · {order.customer_name}</strong><small>{date.format(new Date(order.created_at))}</small></span>
              <b>{price.format(order.total_amount)}</b>
            </li>)}
          </ul>
        ) : <p className="admin-dashboard__empty">Henüz tamamlanan sipariş yok.</p>}
      </div>
    </div>
  )
}

function AdminTable({ section, rows, context }) {
  if (rows.length === 0) return <p>Bu bölümde kayıt yok.</p>

  return (
    <div className="admin-dashboard__table">
      <table aria-label={section.title}>
        <thead>
          <tr>
            {section.columns.map((heading) => <th key={heading} scope="col">{heading}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {section.cells(row, context).map((cell, index) => (
                <td key={section.columns[index]}>{cell}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function AdminSection({ section, token, onUnauthorized, onOpenThread }) {
  const [offset, setOffset] = useState(0)
  const [retry, setRetry] = useState(0)
  const [result, setResult] = useState(null)
  const current = result?.offset === offset && result?.retry === retry ? result : null

  useEffect(() => {
    const controller = new AbortController()
    const query = new URLSearchParams({ limit: PAGE_SIZE, offset })
    if (section.role) query.set('role', section.role)
    const path = section.path === 'overview' ? section.path : `${section.path}?${query}`

    async function load() {
      try {
        const response = await fetch(`${API_BASE_URL}/api/admin/${path}`, {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        })

        if (response.status === 401 && !controller.signal.aborted) {
          onUnauthorized(token)
          return
        }

        const data = await response.json().catch(() => null)
        if (!response.ok || data === null) {
          throw new Error(typeof data?.detail === 'string' ? data.detail : 'Veriler yüklenemedi.')
        }

        if (!controller.signal.aborted) setResult({ offset, retry, data })
      } catch (error) {
        if (!controller.signal.aborted) setResult({ offset, retry, error: error.message })
      }
    }

    load()
    return () => controller.abort()
  }, [section, token, offset, retry, onUnauthorized])

  if (!current) return <p role="status">Yükleniyor…</p>

  if (current.error) {
    return (
      <>
        <p role="alert">{current.error}</p>
        <button type="button" onClick={() => setRetry((value) => value + 1)}>Tekrar dene</button>
      </>
    )
  }

  if (section.path === 'overview') return <Overview data={current.data} />

  const onSaved = (sellerId, commissionRate) => {
    setResult((previous) => ({
      ...previous,
      data: {
        ...previous.data,
        items: previous.data.items.map((store) => store.id === sellerId
          ? { ...store, commission_rate_percent: commissionRate }
          : store),
      },
    }))
  }
  const onRemoved = (productId, threadId) => {
    setResult((previous) => ({
      ...previous,
      data: {
        ...previous.data,
        items: previous.data.items.map((product) => product.id === productId
          ? { ...product, is_active: false, admin_hidden_at: new Date().toISOString(), moderation_thread_id: threadId }
          : product),
      },
    }))
  }

  return (
    <>
      <AdminTable section={section} rows={current.data.items} context={{ token, onUnauthorized, onSaved, onRemoved, onOpenThread }} />
      {(offset > 0 || current.data.has_more) && (
        <div className="admin-dashboard__pagination">
          <button type="button" disabled={offset === 0} onClick={() => setOffset(offset - PAGE_SIZE)}>Önceki</button>
          <span>Sayfa {offset / PAGE_SIZE + 1}</span>
          <button type="button" disabled={!current.data.has_more} onClick={() => setOffset(offset + PAGE_SIZE)}>Sonraki</button>
        </div>
      )}
    </>
  )
}

export default function AdminDashboard({ token, userId, onBack, onLogout, onUnauthorized }) {
  const [unread, refreshUnread] = useSupportUnread(token, 'admin', onUnauthorized)
  const [tab, setTab] = useState('overview')
  const [supportChannel, setSupportChannel] = useState('customer')
  const [supportThreadId, setSupportThreadId] = useState(null)
  const section = sections[tab]
  const navigation = [
    { label: 'GENEL', items: ['overview'] },
    { label: 'PAZARYERİ', items: ['sales', 'products', 'stores', 'sellers', 'phones'] },
    { label: 'YÖNETİM', items: ['users', 'support'] },
  ]

  return (
    <section className="admin-dashboard">
      <div className="admin-dashboard__shell">
        <header className="admin-dashboard__topbar">
          <div className="admin-dashboard__brand"><span className="admin-dashboard__brand-mark"><Icon name="overview" size={20} /></span><span>CASEMARKET <strong>ADMIN</strong></span></div>
          <div className="admin-dashboard__top-actions">
            <span className="admin-dashboard__environment">YÖNETİM ALANI</span>
            <button type="button" onClick={onBack}>← Siteye dön</button>
          </div>
        </header>

        <div className="admin-dashboard__layout">
          <nav className="admin-dashboard__sidebar" aria-label="Admin bölümleri">
            <div className="admin-dashboard__sidebar-title">KONTROL MERKEZİ</div>
            {navigation.map((group) => <div className="admin-dashboard__nav-group" key={group.label}>
              <span className="admin-dashboard__nav-heading">{group.label}</span>
              {group.items.map((key) => <button
                key={key}
                type="button"
                className={tab === key ? 'active' : ''}
                aria-current={tab === key ? 'page' : undefined}
                onClick={() => setTab(key)}
              ><Icon name={key} size={17} /> {sections[key].title} {key === 'support' && <UnreadBadge count={unread} />}</button>)}
            </div>)}
            <button type="button" className="admin-dashboard__logout" onClick={onLogout}>Çıkış yap <span>↗</span></button>
          </nav>

          <main className="admin-dashboard__main">
            <div className="admin-dashboard__heading">
              <div><span className="admin-dashboard__eyebrow">CASEMARKET / ADMIN PANELİ</span><h1>{section.title}</h1>
                <p>{tab === 'overview' ? 'Pazaryerindeki güncel hareketleri buradan takip et.' : `${section.title} kayıtlarını incele.`}</p></div>
              {tab === 'overview' && <span className="admin-dashboard__date">{new Intl.DateTimeFormat('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' }).format(new Date())}</span>}
            </div>
            {tab === 'stores' && <p className="admin-dashboard__commission-note">Oran mağazaya kaydedilir. Sipariş komisyonu ve satıcı ödemeleri henüz otomatik hesaplanmaz.</p>}
            {tab === 'support' ? <>
              <div className="admin-dashboard__support-tabs" role="tablist" aria-label="Destek kanalları">
                <button type="button" role="tab" aria-selected={supportChannel === 'customer'} className={supportChannel === 'customer' ? 'active' : ''}
                  onClick={() => { setSupportChannel('customer'); setSupportThreadId(null) }}>Müşteri desteği</button>
                <button type="button" role="tab" aria-selected={supportChannel === 'seller'} className={supportChannel === 'seller' ? 'active' : ''}
                  onClick={() => { setSupportChannel('seller'); setSupportThreadId(null) }}>Satıcı desteği</button>
              </div>
              <ThreadCenter key={supportChannel} token={token} audience="admin" channel={supportChannel} userId={userId}
                initialThreadId={supportThreadId} onUnauthorized={onUnauthorized} onRead={refreshUnread} />
            </> : <AdminSection key={tab} section={section} token={token} onUnauthorized={onUnauthorized}
              onOpenThread={(threadId) => { setSupportChannel('seller'); setSupportThreadId(threadId); setTab('support') }} />}
          </main>
        </div>
      </div>
    </section>
  )
}
