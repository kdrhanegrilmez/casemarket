const API_BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000'
).replace(/\/$/, '')


// 1. SEPETTEN YENI SIPARIS OLUSTUR
export async function createOrder(token, items) {
  const response = await fetch(`${API_BASE_URL}/api/orders`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ items }),
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message =
      typeof data.detail === 'string'
        ? data.detail
        : 'Sipariş oluşturulamadı.'

    throw new Error(message)
  }

  return data
}


// 2. GIRIS YAPAN MUSTERININ SIPARIS GECMISINI GETIR
export async function getMyOrders(token) {
  const response = await fetch(`${API_BASE_URL}/api/orders/mine`, {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  })

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message =
      typeof data.detail === 'string'
        ? data.detail
        : 'Sipariş geçmişi yüklenemedi.'

    throw new Error(message)
  }

  return data
}


// 3. MUSTERININ BEKLEYEN SIPARISINI IPTAL ET
export async function cancelOrder(token, orderId) {
  const response = await fetch(
    `${API_BASE_URL}/api/orders/${orderId}/cancel`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    }
  )

  const data = await response.json().catch(() => ({}))

  if (!response.ok) {
    const message =
      typeof data.detail === 'string'
        ? data.detail
        : 'Sipariş iptal edilemedi.'

    throw new Error(message)
  }

  return data
}