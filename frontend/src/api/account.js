const BASE = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000').replace(/\/$/, '')

export async function accountRequest(token, path, method = 'GET', body) {
  const response = await fetch(`${BASE}/api/account${path}`, {
    method,
    headers: {
      Authorization: `Bearer ${token}`,
      ...(body ? { 'Content-Type': 'application/json' } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  })
  if (response.status === 204) return null
  const data = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new Error(typeof data.detail === 'string' ? data.detail : 'İşlem tamamlanamadı.')
  }
  return data
}
