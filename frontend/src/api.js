export const apiBase = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/$/, '')
export async function request(path, options = {}) {
  const { timeoutMs = 30000, ...fetchOptions } = options
  const timeout = AbortSignal.timeout(timeoutMs)
  const signal = fetchOptions.signal ? AbortSignal.any([fetchOptions.signal, timeout]) : timeout
  let response
  try {
    response = await fetch(`${apiBase}/api${path}`, { ...fetchOptions, signal })
  } catch (error) {
    if (timeout.aborted) throw new Error('The API took too long to respond. Check the local server and retry.')
    if (error.name === 'AbortError') throw error
    throw new Error('Cannot reach the local API. Start GeoDyssey and retry.')
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    const detail = Array.isArray(error.detail) ? error.detail.map(item => `${(item.loc || []).filter(p => p !== 'body').join('.')}: ${item.msg}`).join('; ') : error.detail
    throw new Error(typeof detail === 'string' ? detail : `Request failed (${response.status})`)
  }
  return response.json()
}
export const artifactUrl = (id, name) => `${apiBase}/api/runs/${id}/artifacts/${name}`
