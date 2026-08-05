/** Safely parse JSON API responses; HTML (Flask/Next errors) gets a clear message. */
export async function parseJsonResponse<T = unknown>(res: Response): Promise<T> {
  const text = await res.text()
  const trimmed = text.trim()
  const contentType = res.headers.get('content-type') || ''
  const looksHtml =
    trimmed.startsWith('<!') ||
    trimmed.toLowerCase().startsWith('<html') ||
    (contentType.includes('text/html') && !contentType.includes('json'))

  if (looksHtml || (trimmed && !trimmed.startsWith('{') && !trimmed.startsWith('['))) {
    if (looksHtml || trimmed.startsWith('<')) {
      throw new Error(
        `Backend returned HTML instead of JSON (HTTP ${res.status}). Is Flask running on :5000?`
      )
    }
  }

  if (!trimmed) {
    throw new Error(`Empty response from backend (HTTP ${res.status})`)
  }

  try {
    return JSON.parse(trimmed) as T
  } catch {
    throw new Error(
      `Invalid JSON from backend (HTTP ${res.status}). Is Flask running on :5000?`
    )
  }
}
