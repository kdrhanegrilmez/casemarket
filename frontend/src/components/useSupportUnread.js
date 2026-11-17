import { useCallback, useState } from 'react'
import { getUnreadCount } from '../api/support'
import useVisiblePolling from './useVisiblePolling'

export default function useSupportUnread(token, audience, onUnauthorized) {
  const [count, setCount] = useState(0)
  const [refresh, setRefresh] = useState(0)
  const refreshUnread = useCallback(() => setRefresh((value) => value + 1), [])
  useVisiblePolling(async (signal) => {
    try {
      const data = await getUnreadCount(token, audience, signal)
      if (!signal.aborted) setCount(data.unread_count)
    } catch (error) {
      if (!signal.aborted && error.status === 401) onUnauthorized?.(token)
    }
  }, { enabled: Boolean(token), interval: 15000, requestKey: `${token}:${audience}:${refresh}` })
  return [token ? count : 0, refreshUnread]
}
