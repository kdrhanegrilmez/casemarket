export default function UnreadBadge({ count }) {
  return count > 0 ? <b className="support-unread-badge" aria-label={`${count} okunmamış mesaj`}>{count}</b> : null
}
