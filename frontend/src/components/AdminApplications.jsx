import { useEffect, useState } from 'react'
import SellerAccessEditor from './SellerAccessEditor'
import RefreshButton from './RefreshButton'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')
const statuses = { pending: 'Bekleyen', approved: 'Onaylanan', rejected: 'Reddedilen' }

export default function AdminApplications({ token, onUnauthorized }) {
  const [status, setStatus] = useState('pending')
  const [applications, setApplications] = useState([])
  const [loadedStatus, setLoadedStatus] = useState(null)
  const [reason, setReason] = useState({})
  const [busyId, setBusyId] = useState(null)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      setLoading(true)
      setError('')
      try {
        const response = await fetch(`${API_BASE_URL}/api/admin/seller-application?status=${status}`, {
          headers: { Authorization: `Bearer ${token}` }, signal: controller.signal,
        })
        if (response.status === 401) { onUnauthorized(token); return }
        const data = await response.json().catch(() => null)
        if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Başvurular yüklenemedi.')
        if (!controller.signal.aborted) { setApplications(data); setLoadedStatus(status) }
      } catch (loadError) { if (!controller.signal.aborted) setError(loadError.message) }
      finally { if (!controller.signal.aborted) setLoading(false) }
    }
    load()
    return () => controller.abort()
  }, [token, status, refresh, onUnauthorized])

  async function review(application, decision) {
    if (decision === 'rejected' && !reason[application.seller_id]?.trim()) {
      setError('Ret gerekçesi yazılmalı.')
      return
    }
    setBusyId(application.seller_id)
    setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/seller-application/${application.seller_id}/review`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, reason: reason[application.seller_id]?.trim() || null }),
      })
      if (response.status === 401) { onUnauthorized(token); return }
      const data = await response.json().catch(() => null)
      if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'Başvuru sonuçlandırılamadı.')
      setRefresh((value) => value + 1)
    } catch (reviewError) { setError(reviewError.message) }
    finally { setBusyId(null) }
  }

  return <div className="admin-applications">
    <div className="admin-dashboard__support-tabs" role="tablist" aria-label="Başvuru durumları">
      {Object.entries(statuses).map(([key, label]) => <button type="button" role="tab" key={key}
        aria-selected={status === key} className={status === key ? 'active' : ''} onClick={() => setStatus(key)}>{label}</button>)}
    </div>
    <RefreshButton busy={loading || busyId !== null} onClick={() => setRefresh((value) => value + 1)} label="Listeyi yenile" />
    {error && <p role="alert">{error}</p>}
    {loadedStatus !== status && !error && <p role="status">Başvurular yükleniyor...</p>}
    {loadedStatus === status && applications.length === 0 && !error && <p>Bu durumda başvuru yok.</p>}
    {loadedStatus === status && applications.map((application) => <article className="admin-applications__card" key={application.seller_id}>
      <strong>#{application.seller_id} · {application.store_name}</strong>
      <p>{application.owner_name} · {application.owner_email}</p>
      {application.description && <p>{application.description}</p>}
      {application.review_reason && <p>{status === 'pending' && application.reviewed_at ? 'Yetki geri alma gerekçesi' : 'İnceleme gerekçesi'}: {application.review_reason}</p>}
      <small>{new Date(application.created_at).toLocaleString('tr-TR')}</small>
      {status === 'approved' && <div className="admin-applications__actions"><SellerAccessEditor
        sellerId={application.seller_id} storeName={application.store_name} token={token} onUnauthorized={onUnauthorized}
        onRevoked={() => { setApplications((current) => current.filter((item) => item.seller_id !== application.seller_id)); setRefresh((value) => value + 1) }} /></div>}
      {status === 'pending' && <div className="admin-applications__actions">
        <label>Ret gerekçesi<textarea value={reason[application.seller_id] || ''} maxLength="500" rows="2"
          onChange={(event) => setReason((current) => ({ ...current, [application.seller_id]: event.target.value }))} /></label>
        <div><button type="button" disabled={busyId !== null} onClick={() => review(application, 'approved')}>Onayla</button>
          <button type="button" disabled={busyId !== null} onClick={() => review(application, 'rejected')}>Reddet</button></div>
      </div>}
    </article>)}
  </div>
}
