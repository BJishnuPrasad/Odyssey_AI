import { useEffect, useRef, useState } from 'react'
import { request } from '../api'

export default function ApiStatus({ onReconnect }) {
  const [status, setStatus] = useState('checking')
  const reconnect = useRef(onReconnect)
  useEffect(() => { reconnect.current = onReconnect }, [onReconnect])
  useEffect(() => {
    let stopped = false, timer, previous = null
    const controller = new AbortController()
    async function check() {
      let healthy = false
      try {
        const result = await request('/health', { timeoutMs: 4000, signal: controller.signal })
        healthy = result.status === 'ok'
      } catch { /* Visible state and read-only retry below. */ }
      if (stopped) return
      setStatus(healthy ? 'connected' : 'offline')
      if (healthy && previous === false) reconnect.current?.()
      previous = healthy
      timer = setTimeout(check, 5000)
    }
    check()
    return () => { stopped = true; clearTimeout(timer); controller.abort() }
  }, [])
  return <span role="status" data-testid="api-status"><span className={`dot ${status === 'offline' ? 'warning' : ''}`} />{' '}{status === 'checking' ? 'Checking local API…' : status === 'offline' ? 'Local API offline · retrying' : 'Local API connected'}</span>
}
