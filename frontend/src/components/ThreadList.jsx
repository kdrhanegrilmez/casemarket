import { threadTitle } from './threadTitle'

export default function ThreadList({ threads, selectedId, audience, onSelect }) {
  return <div className="thread-center__list" aria-label="Konuşmalar">
    {threads.length === 0 && <p>Henüz konuşma yok.</p>}
    {threads.map((thread) => <button type="button" key={thread.id}
      className={selectedId === thread.id ? 'active' : ''} onClick={() => onSelect(thread.id)}>
      <strong>{threadTitle(thread, audience)}</strong>
      <small>{thread.status === 'closed' ? 'Kapalı' : 'Açık'}</small>
      {thread.unread_count > 0 && <b className="thread-center__badge" aria-label={`${thread.unread_count} okunmamış mesaj`}>{thread.unread_count}</b>}
      {audience === 'admin' && thread.kind === 'product_moderation' && <small>{thread.seller_name}</small>}
      {thread.kind === 'product_question' && <small>{audience === 'seller' ? thread.customer_name : thread.store_name || thread.seller_name}</small>}
      <span>{thread.last_message}</span>
    </button>)}
  </div>
}

