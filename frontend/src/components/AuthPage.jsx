
import { useEffect, useState } from 'react'
import './AuthPage.css'

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'

function getErrorMessage(data) {
  if (typeof data?.detail === 'string') {
    return data.detail
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item.msg)
      .join(', ')
  }

  return 'İşlem gerçekleştirilemedi.'
}

function AuthPage({ mode, onModeChange, onAuthenticated }) {
  const isRegister = mode === 'register'

  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  useEffect(() => {
    setError('')
    setSuccess('')
    setPassword('')
  }, [mode])

  async function handleSubmit(event) {
    event.preventDefault()

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      const endpoint = isRegister ? 'register' : 'login'

      const requestBody = isRegister
        ? {
            full_name: fullName.trim(),
            email: email.trim().toLowerCase(),
            password,
          }
        : {
            email: email.trim().toLowerCase(),
            password,
          }

      const response = await fetch(
        `${API_BASE_URL}/api/auth/${endpoint}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(requestBody),
        }
      )

      const data = await response.json()

      if (!response.ok) {
        throw new Error(getErrorMessage(data))
      }

      // Kayit API'si token vermez.
      if (isRegister) {
        setSuccess(
          'Hesabın oluşturuldu. Şimdi giriş yapabilirsin.'
        )
        setPassword('')
        return
      }

      // Login API'sinden gelen JWT'yi kullan.
      const token = data.access_token

      if (!token) {
        throw new Error('Giriş tokenı alınamadı.')
      }

      const meResponse = await fetch(
        `${API_BASE_URL}/api/auth/me`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      if (!meResponse.ok) {
        throw new Error('Kullanıcı bilgileri alınamadı.')
      }

      const user = await meResponse.json()

      onAuthenticated(token, user)
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : 'Bağlantı sırasında hata oluştu.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="auth-page">
      <div className="auth-panel">

        <div className="auth-panel__intro">
          <span className="auth-eyebrow">
            CASEMARKET / ÜYELİK
          </span>

          <h1>
            {isRegister
              ? 'Aramıza katıl.'
              : 'Yeniden hoş geldin.'}
          </h1>

          <p>
            {isRegister
              ? 'Yeni hesabını oluştur, seçkin tasarımları keşfet.'
              : 'Hesabına giriş yap ve alışverişe devam et.'}
          </p>
        </div>

        <div className="auth-tabs">
          <button
            type="button"
            className={!isRegister ? 'active' : ''}
            onClick={() => onModeChange('login')}
          >
            Giriş Yap
          </button>

          <button
            type="button"
            className={isRegister ? 'active' : ''}
            onClick={() => onModeChange('register')}
          >
            Kayıt Ol
          </button>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>

          {isRegister && (
            <label htmlFor="auth-full-name">
              Ad Soyad
              <input
                id="auth-full-name"
                type="text"
                value={fullName}
                onChange={(event) =>
                  setFullName(event.target.value)
                }
                placeholder="Adınız Soyadınız"
                autoComplete="name"
                minLength={2}
                maxLength={120}
                required
              />
            </label>
          )}

          <label htmlFor="auth-email">
            E-posta
            <input
              id="auth-email"
              type="email"
              value={email}
              onChange={(event) =>
                setEmail(event.target.value)
              }
              placeholder="ornek@email.com"
              autoComplete="email"
              required
            />
          </label>

          <label htmlFor="auth-password">
            Şifre
            <input
              id="auth-password"
              type="password"
              value={password}
              onChange={(event) =>
                setPassword(event.target.value)
              }
              placeholder="Şifrenizi girin"
              autoComplete={
                isRegister
                  ? 'new-password'
                  : 'current-password'
              }
              minLength={isRegister ? 8 : 1}
              maxLength={128}
              required
            />
          </label>

          {error && (
            <p className="auth-error" role="alert">
              {error}
            </p>
          )}

          {success && (
            <p className="auth-success" role="status">
              {success}
            </p>
          )}

          <button
            className="auth-submit"
            type="submit"
            disabled={loading || Boolean(success)}
          >
            {loading
              ? 'Lütfen bekleyin...'
              : isRegister
                ? 'Hesap Oluştur ↗'
                : 'Giriş Yap ↗'}
          </button>

        </form>

        <p className="auth-switch">
          {isRegister
            ? 'Zaten hesabın var mı?'
            : 'Henüz hesabın yok mu?'}

          <button
            type="button"
            onClick={() =>
              onModeChange(isRegister ? 'login' : 'register')
            }
          >
            {isRegister ? 'Giriş yap' : 'Kayıt ol'}
          </button>
        </p>

      </div>

      <div className="auth-showcase">
        <span className="auth-showcase__label">
          THE CASEMARKET EXPERIENCE
        </span>

        <div className="auth-showcase__symbol">
          CM
        </div>

        <h2>
          Küçük detaylar.
          <br />
          <em>Büyük farklar.</em>
        </h2>

        <p>
          Stilini tamamlayan tasarımlar,
          tek bir yerde.
        </p>
      </div>
    </section>
  )
}

export default AuthPage
