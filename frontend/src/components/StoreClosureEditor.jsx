import { useState } from 'react'
import AdminActionDialog from './AdminActionDialog'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export default function StoreClosureEditor({ store, token, onUnauthorized, onClosureSaved }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  if (store.approval_status !== 'approved') return <span className="admin-dashboard__muted">Onay sonrası yönetilir</span>
  async function save(event) {
    event.preventDefault()
    if (busy || reason.trim().length < 5) return
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/stores/${store.id}/temporary-closure`, {
        method: 'PATCH', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_temporarily_closed: !store.is_temporarily_closed, reason: reason.trim() }),
      })
      if (response.status === 401) { onUnauthorized?.(token); return }
      const result = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof result?.detail === 'string' ? result.detail : 'Mağaza durumu değiştirilemedi.')
      onClosureSaved(store.id, result)
      setOpen(false)
      setReason('')
    } catch (saveError) { setError(saveError.message) }
    finally { setBusy(false) }
  }
  return <div className="store-closure-editor">
    {store.is_temporarily_closed && <small>{store.closure_reason}</small>}
    <button type="button" className="admin-dashboard__thread-button" onClick={() => { setError(''); setOpen(true) }}>
      {store.is_temporarily_closed ? 'Yeniden aç' : 'Geçici kapat'}
    </button>
    {open && <AdminActionDialog title={`${store.store_name} · ${store.is_temporarily_closed ? 'Yeniden aç' : 'Geçici kapat'}`} busy={busy} onClose={() => setOpen(false)}>
      <form className="admin-dashboard__remove-form" onSubmit={save}>
      <p>{store.is_temporarily_closed ? 'Mağazanın yayındaki ürünleri tekrar vitrinde görünecek.' : 'Ürünler vitrinden gizlenecek, yeni sipariş alınmayacak. Satıcı mevcut siparişlerini ve mesajlarını yönetebilir.'}</p>
      <label>{store.is_temporarily_closed ? 'Yeniden açma gerekçesi' : 'Geçici kapatma gerekçesi'}
        <textarea value={reason} onChange={(event) => setReason(event.target.value)} rows="3" minLength="5" maxLength="500" required disabled={busy} /></label>
      <div><button type="submit" disabled={busy || reason.trim().length < 5}>{busy ? 'Kaydediliyor…' : store.is_temporarily_closed ? 'Yeniden aç' : 'Geçici kapat'}</button>
        <button type="button" disabled={busy} onClick={() => setOpen(false)}>Vazgeç</button></div>
        {error && <small role="alert">{error}</small>}
      </form>
    </AdminActionDialog>}
  </div>
}
