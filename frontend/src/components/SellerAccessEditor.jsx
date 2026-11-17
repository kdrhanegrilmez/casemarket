import { useState } from 'react'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export default function SellerAccessEditor({ sellerId, storeName, token, onUnauthorized, onRevoked }) {
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function revoke(event) {
    event.preventDefault()
    if (busy || reason.trim().length < 5) return
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/seller-application/${sellerId}/revoke`, {
        method: 'PATCH', headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason.trim() }),
      })
      if (response.status === 401) { onUnauthorized?.(token); return }
      const data = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Satıcı yetkisi geri alınamadı.')
      onRevoked(sellerId)
      setOpen(false)
    } catch (revokeError) { setError(revokeError.message) }
    finally { setBusy(false) }
  }
  if (!open) return <button type="button" className="admin-dashboard__remove-button" onClick={() => setOpen(true)}>Satıcı yetkisini geri al</button>
  return <form className="admin-dashboard__remove-form" onSubmit={revoke}>
    <p>{storeName} mağazası yeniden incelemeye alınacak. Satıcı paneli erişimi kapanacak ve ürünleri vitrinden kalkacak.</p>
    <label>Yetki geri alma gerekçesi<textarea value={reason} onChange={(event) => setReason(event.target.value)} minLength="5" maxLength="500" rows="3" required disabled={busy} /></label>
    <div><button type="submit" disabled={busy || reason.trim().length < 5}>{busy ? 'İşleniyor…' : 'Yetkiyi geri al'}</button>
      <button type="button" disabled={busy} onClick={() => setOpen(false)}>Vazgeç</button></div>
    {error && <small role="alert">{error}</small>}
  </form>
}
