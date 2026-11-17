import { useEffect, useId, useRef } from 'react'

export default function AdminActionDialog({ title, onClose, busy, children }) {
  const ref = useRef(null)
  const titleId = useId()
  useEffect(() => {
    const dialog = ref.current
    dialog.showModal()
    return () => dialog.close()
  }, [])
  return <dialog ref={ref} className="admin-action-dialog" aria-labelledby={titleId}
    onCancel={(event) => { event.preventDefault(); if (!busy) onClose() }}>
    <header><h2 id={titleId}>{title}</h2><button type="button" disabled={busy} onClick={onClose} aria-label="Pencereyi kapat">×</button></header>
    {children}
  </dialog>
}
