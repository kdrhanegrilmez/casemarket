import { useEffect, useRef, useState } from 'react'
import './ThreadCenter.css'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

async function supportRequest(token, path, options = {}) {
  const response = await fetch(`${API_BASE_URL}/api/support${path}`, {
    ...options,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(options.body ? { 'Content-Type': 'application/json' } : {}),
    },
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error(typeof data?.detail === 'string' ? data.detail : 'Destek isteği tamamlanamadı.')
    error.status = response.status
    throw error
  }
  return data
}

function threadTitle(thread, audience) {
  if (thread.kind === 'product_moderation') return `Ürün #${thread.product_id} · Yayın incelemesi`
  if (thread.kind === 'product_question') return `Ürün #${thread.product_id} · ${thread.product_name || 'Ürün sorusu'}`
  if (audience === 'admin') return thread.customer_name || thread.seller_name || 'Destek talebi'
  return thread.kind === 'customer_support' ? 'Müşteri desteği' : 'Satıcı desteği'
}

export default function ThreadCenter({ token, audience, channel, userId, initialThreadId = null, productId = null, onUnauthorized, onRestored }) {
  const [threads, setThreads] = useState([])
  const [selectedId, setSelectedId] = useState(initialThreadId)
  const [detail, setDetail] = useState(null)
  const [draft, setDraft] = useState('')
  const [newMessage, setNewMessage] = useState('')
  const [restoreMessage, setRestoreMessage] = useState('Ürün incelendi ve yeniden yayına alındı.')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [refresh, setRefresh] = useState(0)
  const messageListRef = useRef(null)
  const latestMessageId = detail?.messages.at(-1)?.id

  useEffect(() => {
    if (messageListRef.current) messageListRef.current.scrollTop = messageListRef.current.scrollHeight
  }, [selectedId, latestMessageId])

  const listPath = audience === 'admin'
    ? `/admin/threads?channel=${channel}`
    : `/my/threads?channel=${channel}`

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const items = await supportRequest(token, listPath)
        if (!active) return
        setThreads(items)
        setSelectedId((current) => current ?? initialThreadId ?? items[0]?.id ?? null)
      } catch (loadError) {
        if (active) {
          if (loadError.status === 401) onUnauthorized?.(token)
          else setError(loadError.message)
        }
      }
    }
    load()
    const interval = window.setInterval(load, 15000)
    return () => { active = false; window.clearInterval(interval) }
  }, [token, listPath, initialThreadId, refresh, onUnauthorized])

  useEffect(() => {
    if (!selectedId) return undefined
    let active = true
    const load = async () => {
      try {
        const value = await supportRequest(token, `/threads/${selectedId}`)
        if (active) setDetail(value)
      } catch (loadError) {
        if (active) {
          if (loadError.status === 401) onUnauthorized?.(token)
          else setError(loadError.message)
        }
      }
    }
    load()
    const interval = window.setInterval(load, 8000)
    return () => { active = false; window.clearInterval(interval) }
  }, [token, selectedId, refresh, onUnauthorized])

  async function create(event) {
    event.preventDefault()
    if (!newMessage.trim()) return
    setBusy(true)
    setError('')
    try {
      const path = channel === 'questions'
        ? `/products/${productId}/question`
        : audience === 'seller' ? '/seller' : '/customer'
      const result = await supportRequest(token, path, {
        method: 'POST', body: JSON.stringify({ message: newMessage.trim() }),
      })
      setNewMessage('')
      setSelectedId(result.thread_id)
      setRefresh((value) => value + 1)
    } catch (sendError) {
      if (sendError.status === 401) onUnauthorized?.(token)
      else setError(sendError.message)
    } finally { setBusy(false) }
  }

  async function send(event) {
    event.preventDefault()
    if (!draft.trim() || !selectedId) return
    setBusy(true)
    setError('')
    try {
      await supportRequest(token, `/threads/${selectedId}/messages`, {
        method: 'POST', body: JSON.stringify({ message: draft.trim() }),
      })
      setDraft('')
      setRefresh((value) => value + 1)
    } catch (sendError) {
      if (sendError.status === 401) onUnauthorized?.(token)
      else setError(sendError.message)
    } finally { setBusy(false) }
  }

  async function restore(event) {
    event.preventDefault()
    if (!detail?.thread?.product_id || !restoreMessage.trim()) return
    setBusy(true)
    setError('')
    try {
      const response = await fetch(`${API_BASE_URL}/api/admin/products/${detail.thread.product_id}/restore`, {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: restoreMessage.trim() }),
      })
      const result = await response.json().catch(() => null)
      if (!response.ok) {
        const restoreError = new Error(typeof result?.detail === 'string' ? result.detail : 'Ürün yayına alınamadı.')
        restoreError.status = response.status
        throw restoreError
      }
      setRefresh((value) => value + 1)
      onRestored?.()
    } catch (restoreError) {
      if (restoreError.status === 401) onUnauthorized?.(token)
      else setError(restoreError.message)
    } finally { setBusy(false) }
  }

  const canCreate = (audience === 'customer' || audience === 'seller') && (
    channel === 'support' || (audience === 'customer' && channel === 'questions' && productId)
  )

  return <div className="thread-center">
    {canCreate && <form className="thread-center__new" onSubmit={create}>
      <label>{channel === 'questions' ? `Ürün #${productId} için satıcıya soru sor` : 'Yeni destek mesajı'}
        <textarea value={newMessage} onChange={(event) => setNewMessage(event.target.value)}
          maxLength="2000" rows="2" placeholder="Mesajını yaz..." required />
      </label>
      <button type="submit" disabled={busy || !newMessage.trim()}>Gönder</button>
    </form>}
    {error && <p className="thread-center__error" role="alert">{error}</p>}
    <div className="thread-center__layout">
      <div className="thread-center__list" aria-label="Konuşmalar">
        {threads.length === 0 && <p>Henüz konuşma yok.</p>}
        {threads.map((thread) => <button type="button" key={thread.id}
          className={selectedId === thread.id ? 'active' : ''}
          onClick={() => { setSelectedId(thread.id); setDetail(null); setError('') }}>
          <strong>{threadTitle(thread, audience)}</strong>
          {audience === 'admin' && thread.kind === 'product_moderation' && <small>{thread.seller_name}</small>}
          {thread.kind === 'product_question' && <small>{audience === 'seller' ? thread.customer_name : thread.seller_name}</small>}
          <span>{thread.last_message}</span>
        </button>)}
      </div>
      <div className="thread-center__conversation">
        {!selectedId ? <p className="thread-center__placeholder">Bir konuşma seç veya yeni mesaj gönder.</p> : !detail || detail.thread.id !== selectedId ? <p className="thread-center__placeholder">Konuşma yükleniyor...</p> : <>
          <div className="thread-center__conversation-title">
            <strong>{threadTitle(detail.thread, audience)}</strong>
            {audience === 'admin' && <small>{detail.thread.customer_name || detail.thread.seller_name} · {detail.thread.customer_email || detail.thread.seller_email}</small>}
          </div>
          <div className="thread-center__messages" ref={messageListRef} aria-live="polite">
            {detail.messages.map((message) => <div key={message.id} className={`thread-center__message ${message.sender_user_id === userId ? 'mine' : ''}`}>
              <small>{message.sender_role === 'admin' ? 'Admin' : message.sender_name} · {new Date(message.created_at).toLocaleString('tr-TR')}</small>
              <p>{message.body}</p>
            </div>)}
          </div>
          {audience === 'admin' && detail.thread.kind === 'product_moderation' && detail.thread.admin_hidden_at && <form className="thread-center__restore" onSubmit={restore}>
            <label>Satıcıya yeniden yayınlama mesajı
              <textarea value={restoreMessage} onChange={(event) => setRestoreMessage(event.target.value)} minLength="5" maxLength="500" rows="2" required />
            </label>
            <button type="submit" disabled={busy || restoreMessage.trim().length < 5}>Ürün #{detail.thread.product_id} yeniden yayına al</button>
          </form>}
          <form className="thread-center__reply" onSubmit={send}>
            <label className="sr-only" htmlFor={`thread-reply-${audience}-${channel}`}>Mesaj</label>
            <textarea id={`thread-reply-${audience}-${channel}`} value={draft} onChange={(event) => setDraft(event.target.value)} maxLength="2000" rows="2" placeholder="Yanıtını yaz..." required />
            <button type="submit" disabled={busy || !draft.trim()}>Gönder ↗</button>
          </form>
        </>}
      </div>
    </div>
  </div>
}
