import { useCallback, useEffect, useState } from 'react'
import { getUnreadCount } from '../api/support'

export default function useSupportUnread(token, audience, onUnauthorized) {
  const [count, setCount] = useState(0)
  const [refresh, setRefresh] = useState(0)
  const refreshUnread = useCallback(() => setRefresh((value) => value + 1), [])
  useEffect(() => {
    if (!token) return undefined
    let active = true
    let pending = false
    async function load() {
      if (document.visibilityState !== 'visible' || pending) return
      pending = true
      try {
        const data = await getUnreadCount(token, audience)
        if (active) setCount(data.unread_count)
      } catch (error) {
        if (active && error.status === 401) onUnauthorized?.(token)
      } finally { pending = false }
    }
    load()
    const interval = window.setInterval(load, 15000)
    document.addEventListener('visibilitychange', load)
    return () => { active = false; window.clearInterval(interval); document.removeEventListener('visibilitychange', load) }
  }, [token, audience, onUnauthorized, refresh])
  return [token ? count : 0, refreshUnread]
}
