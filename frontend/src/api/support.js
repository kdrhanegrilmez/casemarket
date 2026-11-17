const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export async function supportRequest(token, path, options = {}) {
  const response = await fetch(`${API_BASE_URL}/api${path}`, {
    ...options,
    headers: { Authorization: `Bearer ${token}`, ...(options.body ? { 'Content-Type': 'application/json' } : {}) },
  })
  const data = await response.json().catch(() => null)
  if (!response.ok) {
    const error = new Error(typeof data?.detail === 'string' ? data.detail : 'Destek isteği tamamlanamadı.')
    error.status = response.status
    throw error
  }
  return data
}

export const listThreads = (token, audience, channel, status = 'all') => supportRequest(token,
  `/support/${audience === 'admin' ? 'admin' : 'my'}/threads?${new URLSearchParams({ channel, status })}`)
export const getUnreadCount = (token, audience) => supportRequest(token, `/support/${audience === 'admin' ? 'admin' : 'my'}/unread-count`)
export const setThreadStatus = (token, id, status) => supportRequest(token, `/support/threads/${id}/status`, {
  method: 'PATCH', body: JSON.stringify({ status }),
})
export const getThread = (token, id) => supportRequest(token, `/support/threads/${id}`)
export const sendThreadMessage = (token, id, message) => supportRequest(token, `/support/threads/${id}/messages`, {
  method: 'POST', body: JSON.stringify({ message }),
})
export const startThread = (token, audience, productId, message) => supportRequest(token,
  productId ? `/support/products/${productId}/question` : `/support/${audience}`, {
    method: 'POST', body: JSON.stringify({ message }),
  })
export const restoreProduct = (token, productId, message) => supportRequest(token, `/admin/products/${productId}/restore`, {
  method: 'PATCH', body: JSON.stringify({ message }),
})
