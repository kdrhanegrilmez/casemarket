import { useEffect, useRef, useState } from 'react'
import { getThread, listThreads, restoreProduct, sendThreadMessage, setThreadStatus, startThread } from '../api/support'
import ThreadList from './ThreadList'
import ThreadView from './ThreadView'
import MessageComposer from './MessageComposer'
import ModerationRestoreForm from './ModerationRestoreForm'
import './ThreadCenter.css'

export default function ThreadCenter({ token, audience, channel, userId, initialThreadId = null, productId = null, onUnauthorized, onRestored, onRead }) {
  const [threads, setThreads] = useState([])
  const [selectedId, setSelectedId] = useState(initialThreadId)
  const [detail, setDetail] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const [error, setError] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [refresh, setRefresh] = useState(0)
  const [status, setStatus] = useState('open')

  useEffect(() => {
    let active = true
    let pending = false
    async function load() {
      if (document.visibilityState !== 'visible' || pending) return
      pending = true
      try {
        const items = await listThreads(token, audience, channel, audience === 'admin' ? status : 'all')
        if (!active) return
        const relevant = productId ? items.filter((item) => item.product_id === productId) : items
        if (audience === 'seller' && channel === 'support' && relevant.length > 0 && !relevant.some((item) => item.kind === 'seller_support')) {
          relevant.unshift({ id: 'new-support', kind: 'seller_support', status: 'open', last_message: 'Admin desteğine ilk mesajını yaz.' })
        }
        setThreads(relevant)
        setLoaded(true)
        setSelectedId((current) => current ?? relevant[0]?.id ?? null)
      } catch (loadError) {
        if (active) {
          if (loadError.status === 401) onUnauthorized?.(token)
          else setError(loadError.message)
        }
      } finally { pending = false }
    }
    load()
    const interval = window.setInterval(load, 15000)
    document.addEventListener('visibilitychange', load)
    return () => { active = false; window.clearInterval(interval); document.removeEventListener('visibilitychange', load) }
  }, [token, audience, channel, productId, initialThreadId, refresh, status, onUnauthorized])

  useEffect(() => {
    if (!selectedId || selectedId === 'new-support') return undefined
    let active = true
    let pending = false
    async function load() {
      if (document.visibilityState !== 'visible' || pending) return
      pending = true
      try {
        const value = await getThread(token, selectedId)
        if (active) {
          setDetail(value)
          setThreads((current) => current.map((item) => item.id === selectedId ? { ...item, unread_count: 0 } : item))
          onRead?.()
        }
      } catch (loadError) {
        if (active) {
          if (loadError.status === 401) onUnauthorized?.(token)
          else setError(loadError.message)
        }
      } finally { pending = false }
    }
    load()
    const interval = window.setInterval(load, 8000)
    document.addEventListener('visibilitychange', load)
    return () => { active = false; window.clearInterval(interval); document.removeEventListener('visibilitychange', load) }
  }, [token, selectedId, refresh, onUnauthorized, onRead])

  async function perform(action) {
    if (busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setError('')
    try { await action(); setRefresh((value) => value + 1) }
    catch (actionError) {
      if (actionError.status === 401) onUnauthorized?.(token)
      else setError(actionError.message)
    } finally { busyRef.current = false; setBusy(false) }
  }

  function send() {
    if (!draft.trim()) return
    perform(async () => {
      if (selectedId && selectedId !== 'new-support') await sendThreadMessage(token, selectedId, draft.trim())
      else {
        const result = await startThread(token, audience, channel === 'questions' ? productId : null, draft.trim())
        setSelectedId(result.thread_id)
      }
      setDraft('')
    })
  }

  const canCreate = loaded && (!selectedId || selectedId === 'new-support') && (audience === 'customer' || audience === 'seller') && (
    channel === 'support' || (audience === 'customer' && channel === 'questions' && productId)
  )
  const currentDetail = detail?.thread.id === selectedId ? detail : null
  return <div className="thread-center">
    {error && <p className="thread-center__error" role="alert">{error}</p>}
    {audience === 'admin' && <div className="thread-center__filters" aria-label="Konuşma durumu">
      {[['open', 'Açık'], ['closed', 'Kapalı']].map(([value, label]) => <button type="button" key={value} disabled={busy}
        aria-pressed={status === value} onClick={() => {
          setStatus(value); setSelectedId(null); setDetail(null); setThreads([]); setLoaded(false); setDraft('')
        }}>{label}</button>)}
    </div>}
    <div className="thread-center__layout">
      <ThreadList threads={threads} selectedId={selectedId} audience={audience} onSelect={(id) => {
        if (id === selectedId || busy) return
        setSelectedId(id); setDraft(''); setError('')
      }} />
      <div className="thread-center__conversation">
        {currentDetail ? <ThreadView detail={currentDetail} audience={audience} userId={userId}>
          {audience === 'admin' && <button type="button" className="thread-center__status-button" disabled={busy} onClick={() => perform(async () => {
            const nextStatus = currentDetail.thread.status === 'closed' ? 'open' : 'closed'
            await setThreadStatus(token, selectedId, nextStatus)
            setSelectedId(null); setDetail(null)
          })}>{currentDetail.thread.status === 'closed' ? 'Konuşmayı yeniden aç' : 'Konuşmayı kapat'}</button>}
          {audience === 'admin' && currentDetail.thread.kind === 'product_moderation' && currentDetail.thread.admin_hidden_at &&
            <ModerationRestoreForm productId={currentDetail.thread.product_id} busy={busy} onRestore={(message) => perform(async () => {
              await restoreProduct(token, currentDetail.thread.product_id, message)
              onRestored?.()
            })} />}
        </ThreadView> : <p className="thread-center__placeholder">{!loaded || (selectedId && selectedId !== 'new-support') ? 'Konuşma yükleniyor...' : canCreate ? (productId ? `Ürün #${productId} için ilk sorunu yaz.` : 'Destek almak için ilk mesajını yaz.') : 'Bir konuşma seç.'}</p>}
        {(currentDetail || canCreate) && <MessageComposer value={draft} onChange={setDraft} onSend={send} busy={busy} />}
      </div>
    </div>
  </div>
}
