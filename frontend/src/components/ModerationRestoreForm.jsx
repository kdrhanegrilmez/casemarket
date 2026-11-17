import { useState } from 'react'

export default function ModerationRestoreForm({ productId, onRestore, busy }) {
  const [message, setMessage] = useState('Ürün incelendi ve yeniden yayına alındı.')
  return <form className="thread-center__restore" onSubmit={(event) => { event.preventDefault(); onRestore(message.trim()) }}>
    <label>Satıcıya yeniden yayınlama mesajı
      <textarea value={message} onChange={(event) => setMessage(event.target.value)} minLength="5" maxLength="500" rows="2" required disabled={busy} />
    </label>
    <button type="submit" disabled={busy || message.trim().length < 5}>Ürün #{productId} yeniden yayına al</button>
  </form>
}
