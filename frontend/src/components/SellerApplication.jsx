import { useEffect, useState } from 'react'
import RefreshButton from './RefreshButton'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const labels = { pending: 'İnceleniyor', approved: 'Onaylandı', rejected: 'Reddedildi' }

export default function SellerApplication({ token, user, onUserChange, onSellerOpen }) {
  const [application, setApplication] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function request(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}/api/sellers${path}`, {
      ...options,
      headers: { Authorization: `Bearer ${token}`, ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
    })
    const data = await response.json().catch(() => null)
    if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Başvuru işlemi tamamlanamadı.')
    return data
  }

  async function load() {
    setLoading(true)
    setError('')
    try {
      const data = await request('/my-application')
      setApplication(data)
      if (user.role === 'seller' || data?.approval_status === 'approved') {
        const response = await fetch(`${API_BASE_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
        if (response.ok) onUserChange(await response.json())
      }
    } catch (loadError) { setError(loadError.message) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    let active = true
    fetch(`${API_BASE_URL}/api/sellers/my-application`, { headers: { Authorization: `Bearer ${token}` } })
      .then(async (response) => {
        const data = await response.json().catch(() => null)
        if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Başvuru yüklenemedi.')
        if (active) { setApplication(data); setLoading(false) }
        if (active && (user.role === 'seller' || data?.approval_status === 'approved')) {
          const profileResponse = await fetch(`${API_BASE_URL}/api/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
          if (active && profileResponse.ok) onUserChange(await profileResponse.json())
        }
      })
      .catch((loadError) => { if (active) { setError(loadError.message); setLoading(false) } })
    return () => { active = false }
  }, [token, user.role, onUserChange])

  async function submit(event) {
    event.preventDefault()
    if (busy) return
    setBusy(true)
    setError('')
    const values = Object.fromEntries(new FormData(event.currentTarget).entries())
    try { setApplication(await request('', { method: 'POST', body: JSON.stringify(values) })) }
    catch (submitError) { setError(submitError.message) }
    finally { setBusy(false) }
  }

  return <div className="account-panel">
    <span className="overline">MAĞAZA BAŞVURUSU</span><h2>Mağazam</h2>
    {loading && <p role="status">Başvuru yükleniyor...</p>}
    {error && <p role="alert">{error}</p>}
    {application && <div className="account-list__item">
      <div><strong>{application.store_name}</strong><p>Durum: {labels[application.approval_status]}</p>
        {application.description && <p>{application.description}</p>}
        {application.review_reason && <p>Admin gerekçesi: {application.review_reason}</p>}
      </div>
    </div>}
    {application?.approval_status === 'pending' && <p>{application.reviewed_at ? 'Satıcı yetkin geri alındı. Mağazan yeniden incelemede.' : 'Başvurun inceleniyor. Sonucu görmek için durumu yenileyebilirsin.'}</p>}
    {application?.approval_status === 'rejected' && <p>Ret gerekçesine göre bilgilerini düzenleyip yeniden başvurabilirsin.</p>}
    {application?.approval_status === 'approved' && <button type="button" className="button button--dark" onClick={onSellerOpen}>Satıcı paneline gir ↗</button>}
    {!loading && (!application || application.approval_status === 'rejected') && user.role === 'customer' && <form key={application?.id || 'new'} className="account-form" onSubmit={submit}>
      <p>Mağaza açmak için başvuru gönder. Admin onayından sonra satıcı panelin açılır.</p>
      <label>Mağaza adı<input name="store_name" defaultValue={application?.store_name || ''} minLength="3" maxLength="120" required disabled={busy} /></label>
      <label>Mağaza açıklaması<textarea name="description" defaultValue={application?.description || ''} maxLength="1000" rows="3" disabled={busy} /></label>
      <button className="button button--dark" disabled={busy}>{busy ? 'Gönderiliyor...' : application ? 'Yeniden başvur' : 'Başvuru gönder'}</button>
    </form>}
    <div className="seller-application__actions"><RefreshButton onClick={load} busy={busy || loading} /></div>
  </div>
}
