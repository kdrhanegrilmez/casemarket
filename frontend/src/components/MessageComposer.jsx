import { useId } from 'react'

export default function MessageComposer({ value, onChange, onSend, busy }) {
  const id = useId()
  return <form className="thread-center__reply" onSubmit={(event) => { event.preventDefault(); onSend() }}>
    <label className="sr-only" htmlFor={id}>Mesaj</label>
    <textarea id={id} value={value} onChange={(event) => onChange(event.target.value)}
      maxLength="2000" rows="2" placeholder="Mesajını yaz..." required disabled={busy} />
    <button type="submit" disabled={busy || !value.trim()}>{busy ? 'Gönderiliyor...' : 'Gönder ↗'}</button>
  </form>
}
