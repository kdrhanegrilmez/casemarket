import { useRef, useState } from 'react'
import { getThread, listThreads, restoreProduct, sendThreadMessage, setThreadStatus, startThread } from '../api/support'
import ThreadList from './ThreadList'
import ThreadView from './ThreadView'
import MessageComposer from './MessageComposer'
import ModerationRestoreForm from './ModerationRestoreForm'
import RefreshButton from './RefreshButton'
import useVisiblePolling from './useVisiblePolling'
import './ThreadCenter.css'

export default function ThreadCenter({ token, audience, channel, userId, initialThreadId = null, productId = null, onUnauthorized, onRestored, onRead }) {
  const [threads, setThreads] = useState([])
  const [selectedId, setSelectedId] = useState(initialThreadId)
  const [detail, setDetail] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const busyRef = useRef(false)
  const seenMessages = useRef(new Map())
  const [error, setError] = useState('')
  const [loaded, setLoaded] = useState(false)
  const [refresh, setRefresh] = useState(0)
  const [status, setStatus] = useState('open')
  const [notice, setNotice] = useState('')
  const [creating, setCreating] = useState(false)
  const [newProductId, setNewProductId] = useState(null)
  const questionProductId = productId || newProductId
  const currentDetail = detail?.thread.id === selectedId ? detail : null
  const completed = currentDetail?.thread.status === 'closed'

  function showError(loadError) {
    if (loadError.status === 401) onUnauthorized?.(token)
    else setError(loadError.message)
  }

  useVisiblePolling(async (signal) => {
    try {
      const items = await listThreads(token, audience, channel, status, signal)
      if (signal.aborted) return
      const relevant = productId ? items.filter((item) => item.product_id === productId) : items
      setThreads(relevant)
      setLoaded(true)
      if (creating) {
        const existing = relevant.find((item) => channel === 'support'
          ? item.kind === `${audience}_support`
          : item.kind === 'product_question' && item.product_id === questionProductId)
        setSelectedId(existing?.id ?? null)
        if (existing) setCreating(false)
      } else setSelectedId((current) => current ?? relevant[0]?.id ?? null)
      // Başka bir ekrandan yeniden açılmış seçili görüşmenin polling'ini başlat.
      setDetail((current) => {
        const updated = relevant.find((item) => item.id === current?.thread.id)
        return updated && updated.status !== current.thread.status ? { ...current, thread: { ...current.thread, ...updated } } : current
      })
    } catch (loadError) { if (!signal.aborted) showError(loadError) }
  }, { requestKey: `${token}:${audience}:${channel}:${productId}:${status}:${refresh}`, interval: status === 'open' ? 15000 : null })

  useVisiblePolling(async (signal) => {
    try {
      const value = await getThread(token, selectedId, signal)
      if (signal.aborted) return
      setDetail(value)
      setThreads((current) => current.map((item) => item.id === selectedId ? { ...item, ...value.thread, unread_count: 0 } : item))
      const latestId = value.messages.at(-1)?.id ?? 0
      if (seenMessages.current.get(selectedId) !== latestId) {
        seenMessages.current.set(selectedId, latestId)
        onRead?.()
      }
    } catch (loadError) { if (!signal.aborted) showError(loadError) }
  }, { enabled: Boolean(selectedId) && !completed, interval: 8000, requestKey: `${token}:${selectedId}:${refresh}` })

  async function perform(action) {
    if (busyRef.current) return
    busyRef.current = true
    setBusy(true)
    setError('')
    try { await action(); setRefresh((value) => value + 1) }
    catch (actionError) {
      if (actionError.status === 409) setRefresh((value) => value + 1)
      showError(actionError)
    } finally { busyRef.current = false; setBusy(false) }
  }

  function send() {
    if (!draft.trim() || completed) return
    perform(async () => {
      if (selectedId) await sendThreadMessage(token, selectedId, draft.trim())
      else {
        const result = await startThread(token, audience, channel === 'questions' ? questionProductId : null, draft.trim())
        setSelectedId(result.thread_id)
        setCreating(false)
      }
      setDraft('')
    })
  }

  const newQuestionProductId = productId || currentDetail?.thread.product_id
  const canStart = audience !== 'admin' && (channel === 'support' || (audience === 'customer' && newQuestionProductId))
  const canCreate = loaded && status === 'open' && !selectedId && (audience === 'customer' || audience === 'seller') && (
    channel === 'support' || (audience === 'customer' && channel === 'questions' && questionProductId)
  )
  function changeFilter(value) {
    if (value === status) return
    setStatus(value); setSelectedId(null); setDetail(null); setThreads([]); setLoaded(false)
    setDraft(''); setNotice(''); setError(''); setCreating(false)
  }
  return <div className="thread-center">
    {error && <p className="thread-center__error" role="alert">{error}</p>}
    {notice && <p className="thread-center__completed" role="status">{notice}</p>}
    <div className="thread-center__toolbar">
      <div className="thread-center__filters" aria-label="Görüşme durumu">
        {[['open', 'Devam eden'], ['closed', 'Sonlandırılan']].map(([value, label]) => <button type="button" key={value}
          disabled={busy} aria-pressed={status === value} onClick={() => changeFilter(value)}>{label}</button>)}
      </div>
      {canStart && <button type="button" className="thread-center__start" disabled={busy} onClick={() => {
        setNewProductId(channel === 'questions' ? newQuestionProductId : null)
        setCreating(true); setStatus('open'); setSelectedId(null); setDetail(null); setLoaded(false)
        setDraft(''); setError(''); setNotice(''); setRefresh((value) => value + 1)
      }}>{channel === 'questions' ? 'Yeni soru sor' : 'Yeni destek talebi'}</button>}
      <RefreshButton busy={busy} label="Yenile" onClick={() => { setError(''); setRefresh((value) => value + 1) }} />
    </div>
    <div className="thread-center__layout">
      <ThreadList threads={threads} selectedId={selectedId} audience={audience} onSelect={(id) => {
        if (id === selectedId || busy) return
        setSelectedId(id); setDetail(null); setCreating(false); setDraft(''); setError(''); setNotice('')
      }} />
      <div className="thread-center__conversation">
        {currentDetail ? <ThreadView detail={currentDetail} audience={audience} userId={userId}>
          {(audience === 'admin' || (currentDetail.thread.kind === 'product_question' && !completed)) &&
            <button type="button" className="thread-center__status-button" disabled={busy} onClick={() => perform(async () => {
              const nextStatus = completed ? 'open' : 'closed'
              const result = await setThreadStatus(token, selectedId, nextStatus)
              setDetail((current) => ({ ...current, thread: { ...current.thread, ...result } }))
              setStatus(nextStatus); setThreads([]); setLoaded(false); setDraft('')
              setNotice(nextStatus === 'closed' ? 'Görüşme sonlandırıldı. İhtiyaç duyarsan yeni bir görüşme başlatabilirsin.' : 'Görüşme yeniden açıldı.')
            })}>{completed ? 'Desteği yeniden aç' : channel === 'questions' ? 'Görüşmeyi sonlandır' : 'Desteği sonlandır'}</button>}
          {audience === 'admin' && !completed && currentDetail.thread.kind === 'product_moderation' && currentDetail.thread.admin_hidden_at &&
            <ModerationRestoreForm productId={currentDetail.thread.product_id} busy={busy} onRestore={(message) => perform(async () => {
              await restoreProduct(token, currentDetail.thread.product_id, message)
              onRestored?.()
            })} />}
        </ThreadView> : <p className="thread-center__placeholder">{!loaded || selectedId ? 'Konuşma yükleniyor...' : canCreate ? (questionProductId ? `Ürün #${questionProductId} için ilk sorunu yaz.` : 'Yeni destek talebini yaz.') : status === 'closed' ? 'Henüz sonlandırılan görüşme yok.' : 'Bir konuşma seç.'}</p>}
        {completed && <p className="thread-center__completed" role="status">Bu görüşme sonlandırıldı. Geçmişi okuyabilir, yeni bir talep için ayrı görüşme başlatabilirsin.
          {currentDetail.thread.closed_at && <small>Sonlandırılma: {new Date(currentDetail.thread.closed_at).toLocaleString('tr-TR')}</small>}</p>}
        {((currentDetail && !completed) || canCreate) && <MessageComposer value={draft} onChange={setDraft} onSend={send} busy={busy} />}
      </div>
    </div>
  </div>
}
