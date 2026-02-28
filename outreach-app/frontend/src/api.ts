/**
 * Shared fetch wrapper with consistent error handling.
 *
 * - Throws on non-2xx responses (with status + body detail).
 * - Returns parsed JSON.
 */
export async function apiFetch<T = unknown>(
  url: string,
  init?: RequestInit,
): Promise<T> {
  const res = await fetch(url, init)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || body.message || JSON.stringify(body)
    } catch {
      // response wasn't JSON — keep statusText
    }
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json() as Promise<T>
}
