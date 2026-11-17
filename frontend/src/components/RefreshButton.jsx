import './RefreshButton.css'

export default function RefreshButton({ onClick, busy = false, label = 'Durumu yenile' }) {
  return <button type="button" className="refresh-button" onClick={onClick} disabled={busy} aria-busy={busy}>
    <svg className={busy ? 'refresh-button__icon is-spinning' : 'refresh-button__icon'} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 7v5h-5M4 17v-5h5" /><path d="M6.1 6.1A8 8 0 0 1 20 12M4 12a8 8 0 0 0 13.9 5.9" />
    </svg>
    {busy ? 'Yenileniyor…' : label}
  </button>
}
