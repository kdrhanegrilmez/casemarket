import ThreadCenter from './ThreadCenter'
import './CustomerSupportWidget.css'

export default function CustomerSupportWidget({ token, user, open, channel, productId, onOpenChange, onChannelChange, onLogin, onUnauthorized }) {
  return <div className="customer-support-widget">
    {open && <section className="customer-support-widget__panel" aria-label="Müşteri destek sohbeti">
      <div className="customer-support-widget__heading">
        <div><small>CASEMARKET</small><strong>Yardım ve destek</strong></div>
        <button type="button" aria-label="Destek kutusunu kapat" onClick={() => onOpenChange(false)}>×</button>
      </div>
      {user?.role === 'customer' && token ? <>
        <div className="customer-support-widget__tabs" role="tablist" aria-label="Destek bölümleri">
          <button type="button" role="tab" aria-selected={channel === 'support'} className={channel === 'support' ? 'active' : ''}
            onClick={() => onChannelChange('support')}>Destek</button>
          <button type="button" role="tab" aria-selected={channel === 'questions'} className={channel === 'questions' ? 'active' : ''}
            onClick={() => onChannelChange('questions')}>Ürün sorularım</button>
        </div>
        <ThreadCenter key={channel} token={token} audience="customer" channel={channel} userId={user.id}
          productId={channel === 'questions' ? productId : null} onUnauthorized={onUnauthorized} />
      </> : <div className="customer-support-widget__login">
        <p>Destek mesajlarını hesabınla eşleştirmek için giriş yap.</p>
        <button type="button" onClick={onLogin}>Giriş yap</button>
      </div>}
    </section>}
    <button type="button" className="customer-support-widget__trigger" onClick={() => onOpenChange(!open)} aria-expanded={open}>
      <span aria-hidden="true">✦</span> Yardım
    </button>
  </div>
}
