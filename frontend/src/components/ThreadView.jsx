import { useEffect, useRef } from 'react'
import { threadTitle } from './threadTitle'

export default function ThreadView({ detail, audience, userId, children }) {
  const messageListRef = useRef(null)
  const latestMessageId = detail.messages.at(-1)?.id
  useEffect(() => {
    if (messageListRef.current) messageListRef.current.scrollTop = messageListRef.current.scrollHeight
  }, [detail.thread.id, latestMessageId])
  return <>
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
    {children}
  </>
}
