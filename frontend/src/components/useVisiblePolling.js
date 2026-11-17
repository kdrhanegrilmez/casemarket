import { useEffect, useRef } from 'react'

// Tek istek; tamamlandıktan sonra bekle. Gizlenince timer ve istek iptal edilir.
export default function useVisiblePolling(load, { enabled = true, interval = 15000, requestKey = '' } = {}) {
  const latestLoad = useRef(load)
  useEffect(() => { latestLoad.current = load }, [load])
  useEffect(() => {
    if (!enabled) return undefined
    let active = true
    let timer
    let controller = null
    function stop() {
      window.clearTimeout(timer)
      controller?.abort()
      controller = null
    }
    async function tick() {
      if (!active || controller || document.visibilityState !== 'visible') return
      const request = new AbortController()
      controller = request
      try { await latestLoad.current(request.signal) }
      finally {
        if (controller === request) {
          controller = null
          if (active && interval !== null && document.visibilityState === 'visible') timer = window.setTimeout(tick, interval)
        }
      }
    }
    function visibilityChanged() {
      stop()
      if (document.visibilityState === 'visible') tick()
    }
    tick()
    document.addEventListener('visibilitychange', visibilityChanged)
    return () => { active = false; stop(); document.removeEventListener('visibilitychange', visibilityChanged) }
  }, [enabled, interval, requestKey])
}
