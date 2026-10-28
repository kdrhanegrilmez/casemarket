import {useEffect,useRef} from "react";
import './SiteDialog.css'

//CaseMarket için ortak onay ve bilgilendirme penceresi

export default function SiteDialog({
    open,
    variant ='confirm',
    title,
    message,
    confirmText = 'Onayla',
    onConfirm,
    onClose,
    busy =false,
    danger =false,
                                   }){
    const primaryButtonRef = useRef(null)

    // Pencere acildiginda butona odaklan.
    // Escape tusuna basilirsa pencereyi kapat.
    useEffect(()=>{
        if (!open) return

        primaryButtonRef.current?.focus()

        function handleKeyDown(event){
            if (event.key ==='Escape' && !busy){
                onClose()
            }
        }

        window.addEventListener('keydown',handleKeyDown)
        return ()=>{
            window.removeEventListener('keydown',handleKeyDown)

        }

    }, [open,busy,onClose]
    )

    if (!open) return null
    const isConfirm = variant ==='confirm'

    return(
        <div className="cm-dialog-layer">
        <button
            type="button"
            className="cm-dialog-backdrop"
            aria-label="Pencereyi kapat"
            onClick={onClose}
            disabled={busy}
        />

 <section
        className={`cm-dialog cm-dialog--${variant}`}
        role={isConfirm ? 'alertdialog' : 'dialog'}
        aria-modal="true"
        aria-labelledby="cm-dialog-title"
        aria-describedby="cm-dialog-description"
      >
        <span className="cm-dialog__eyebrow">
          CASEMARKET / BİLDİRİM
        </span>

        <div className="cm-dialog__symbol" aria-hidden="true">
          {variant === 'success'
            ? '✓'
            : variant === 'error'
              ? '!'
              : '◇'}
        </div>

        <h2 id="cm-dialog-title">{title}</h2>
        <p id="cm-dialog-description">{message}</p>

        <div className="cm-dialog__actions">
          {isConfirm && (
            <button
              type="button"
              className="cm-dialog__secondary"
              onClick={onClose}
              disabled={busy}
            >
              Vazgeç
            </button>
          )}

          <button
            ref={primaryButtonRef}
            type="button"
            className={`cm-dialog__primary ${
              danger ? 'cm-dialog__primary--danger' : ''
            }`}
            onClick={isConfirm ? onConfirm : onClose}
            disabled={busy}
          >
            {busy
              ? 'İşlem sürüyor...'
              : isConfirm
                ? confirmText
                : 'Tamam'}
          </button>
        </div>
      </section>
        </div>
    )

}