import { useEffect, useState } from 'react'
import { accountRequest } from '../api/account'
import OrderHistory from './OrderHistory'
import './AccountPage.css'

const tabs = [
  ['profile', 'Bilgilerim'],
  ['addresses', 'Adreslerim'],
  ['payments', 'Ödeme yöntemlerim'],
  ['active', 'Aktif siparişler'],
  ['history', 'Sipariş geçmişi'],
]

export default function AccountPage({ token, user, onUserChange, onBack, onSellerOpen, onLogout, initialTab = 'profile' }) {
  const [tab, setTab] = useState(initialTab)
  const [addresses, setAddresses] = useState([])
  const [methods, setMethods] = useState([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let active = true
    Promise.all([
      accountRequest(token, '/addresses'),
      accountRequest(token, '/payment-methods'),
    ]).then(([addressData, methodData]) => {
      if (active) { setAddresses(addressData); setMethods(methodData) }
    }).catch((err) => { if (active) setError(err.message) })
    return () => { active = false }
  }, [token])

  async function submit(event, path, onSuccess) {
    event.preventDefault()
    setBusy(true)
    setError('')
    setMessage('')
    const form = event.currentTarget
    const values = Object.fromEntries(new FormData(form).entries())
    try {
      const result = await accountRequest(token, path, path === '/profile' ? 'PATCH' : 'POST', values)
      onSuccess(result)
      if (path !== '/profile') form.reset()
      setMessage('Bilgilerin kaydedildi.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function remove(path, id, setter) {
    setBusy(true)
    setError('')
    try {
      await accountRequest(token, `${path}/${id}`, 'DELETE')
      setter((current) => current.filter((item) => item.id !== id))
      setMessage('Kayıt kaldırıldı.')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const visibleTabs = user.role === 'seller' ? [...tabs, ['seller', 'Satıcı paneli']] : tabs

  return (
    <section className="account-page">
      <div className="account-page__hero">
        <div><span className="overline">CASEMARKET / HESABIM</span><h1>Merhaba, {user.full_name.split(' ')[0]}.</h1>
          <p>Bilgilerini, teslimat adreslerini ve siparişlerini buradan yönet.</p></div>
        <button type="button" className="account-page__back" onClick={onBack}>← Alışverişe dön</button>
      </div>
      <div className="account-page__layout">
        <nav className="account-page__nav" aria-label="Hesap bölümleri">
          {visibleTabs.map(([key, label]) => (
            <button key={key} type="button" className={tab === key ? 'active' : ''}
              onClick={() => { setTab(key); setError(''); setMessage('') }}>{label}<span>↗</span></button>
          ))}
          <button type="button" className="account-page__logout" onClick={onLogout}>Çıkış yap <span>↗</span></button>
        </nav>
        <div className="account-page__content">
          {error && <p className="account-page__notice account-page__notice--error" role="alert">{error}</p>}
          {message && <p className="account-page__notice" role="status">{message}</p>}
          {tab === 'profile' && <div className="account-panel">
            <span className="overline">HESAP BİLGİLERİ</span><h2>Bilgilerim</h2>
            <form key={user.id} onSubmit={(event) => submit(event, '/profile', onUserChange)} className="account-form">
              <label>Ad soyad<input name="full_name" defaultValue={user.full_name} minLength="2" required /></label>
              <label>E-posta<input name="email" type="email" defaultValue={user.email} required /></label>
              <label>Hesap türü<input value={user.role === 'seller' ? 'Satıcı' : 'Müşteri'} disabled readOnly /></label>
              <button className="button button--dark" disabled={busy}>Bilgileri kaydet</button>
            </form>
          </div>}
          {tab === 'addresses' && <div className="account-panel">
            <span className="overline">TESLİMAT</span><h2>Adreslerim</h2>
            <div className="account-list">{addresses.map((address) => <article key={address.id} className="account-list__item">
              <div><strong>{address.label}</strong><p>{address.recipient} · {address.phone}</p>
                <p>{address.address_line}, {address.district} / {address.city} {address.postal_code}</p></div>
              <button type="button" disabled={busy} onClick={() => remove('/addresses', address.id, setAddresses)}>Kaldır</button>
            </article>)}{addresses.length === 0 && <p>Henüz kayıtlı adresin yok.</p>}</div>
            <h3>Yeni adres ekle</h3>
            <form className="account-form account-form--grid" onSubmit={(event) => submit(event, '/addresses', (item) => setAddresses((current) => [item, ...current]))}>
              <label>Adres adı<input name="label" placeholder="Ev, iş..." required minLength="2" /></label>
              <label>Alıcı<input name="recipient" required minLength="2" /></label>
              <label>Telefon<input name="phone" type="tel" required minLength="7" /></label>
              <label>İl<input name="city" required minLength="2" /></label>
              <label>İlçe<input name="district" required minLength="2" /></label>
              <label>Posta kodu<input name="postal_code" /></label>
              <label className="account-form__wide">Açık adres<textarea name="address_line" required minLength="10" rows="3" /></label>
              <button className="button button--dark" disabled={busy}>Adresi kaydet</button>
            </form>
          </div>}
          {tab === 'payments' && <div className="account-panel">
            <span className="overline">DEMO ÖDEME</span><h2>Ödeme yöntemlerim</h2>
            <p>Bu projede gerçek ödeme alınmaz. Tam kart numarası ve güvenlik kodu girme; yalnızca kartın görünen bilgileri saklanır.</p>
            <div className="account-list">{methods.map((method) => <article key={method.id} className="account-list__item">
              <div><strong>{method.label}</strong><p>{method.brand} ···· {method.last_four} · {String(method.expiry_month).padStart(2, '0')}/{method.expiry_year}</p></div>
              <button type="button" disabled={busy} onClick={() => remove('/payment-methods', method.id, setMethods)}>Kaldır</button>
            </article>)}{methods.length === 0 && <p>Henüz demo ödeme yöntemin yok.</p>}</div>
            <h3>Demo kart bilgisi ekle</h3>
            <form className="account-form account-form--grid" onSubmit={(event) => submit(event, '/payment-methods', (item) => setMethods((current) => [item, ...current]))}>
              <label>Kart adı<input name="label" placeholder="Kişisel kartım" minLength="2" required /></label>
              <label>Kart türü<input name="brand" placeholder="Visa, Mastercard..." minLength="2" required /></label>
              <label>Son dört hane<input name="last_four" inputMode="numeric" pattern="[0-9]{4}" maxLength="4" required /></label>
              <label>Son kullanma ayı<input name="expiry_month" type="number" min="1" max="12" required /></label>
              <label>Son kullanma yılı<input name="expiry_year" type="number" min="2026" max="2100" required /></label>
              <button className="button button--dark" disabled={busy}>Demo kartı kaydet</button>
            </form>
          </div>}
          {(tab === 'active' || tab === 'history') && <OrderHistory token={token} filter={tab} onBack={onBack} />}
          {tab === 'seller' && user.role === 'seller' && <div className="account-panel">
            <span className="overline">MAĞAZAM</span><h2>Satıcı paneli</h2>
            <p>Ürünlerini ekle, stoklarını güncelle ve yayındaki ürünlerini yönet.</p>
            <button type="button" className="button button--dark" onClick={onSellerOpen}>Satıcı paneline gir ↗</button>
          </div>}
        </div>
      </div>
    </section>
  )
}
