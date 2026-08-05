/** Load paper-trading ledger files from the GitHub `agent-data` branch. */

const DEFAULT_REPO = 'Hargunghotra/sp500'
const DEFAULT_BRANCH = 'agent-data'

function repo(): string {
  return process.env.GITHUB_DATA_REPO || process.env.GITHUB_REPOSITORY || DEFAULT_REPO
}

function branch(): string {
  return process.env.GITHUB_DATA_BRANCH || DEFAULT_BRANCH
}

function githubHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    Accept: 'application/vnd.github.raw+json',
    'User-Agent': 'sp500-simulator-vercel',
  }
  const token = process.env.GITHUB_TOKEN || process.env.GH_TOKEN
  if (token) headers.Authorization = `Bearer ${token}`
  return headers
}

export async function fetchAgentDataFile(relativePath: string): Promise<string | null> {
  const path = relativePath.replace(/^\/+/, '')
  const apiUrl = `https://api.github.com/repos/${repo()}/contents/${path}?ref=${encodeURIComponent(branch())}`
  const rawUrl = `https://raw.githubusercontent.com/${repo()}/${branch()}/${path}`

  try {
    const res = await fetch(apiUrl, {
      headers: githubHeaders(),
      next: { revalidate: 60 },
    })
    if (res.ok) return await res.text()
  } catch {
    // fall through to raw
  }

  try {
    const res = await fetch(rawUrl, {
      headers: { 'User-Agent': 'sp500-simulator-vercel' },
      next: { revalidate: 60 },
    })
    if (!res.ok) return null
    return await res.text()
  } catch {
    return null
  }
}

export async function fetchAgentJson<T>(relativePath: string): Promise<T | null> {
  const text = await fetchAgentDataFile(relativePath)
  if (!text) return null
  try {
    return JSON.parse(text) as T
  } catch {
    return null
  }
}

export async function fetchAgentJsonl(relativePath: string, limit = 500): Promise<unknown[]> {
  const text = await fetchAgentDataFile(relativePath)
  if (!text) return []
  const rows: unknown[] = []
  for (const line of text.split('\n')) {
    const trimmed = line.trim()
    if (!trimmed) continue
    try {
      rows.push(JSON.parse(trimmed))
    } catch {
      continue
    }
  }
  if (limit && rows.length > limit) return rows.slice(-limit)
  return rows
}

/** Prefer live Flask when BACKEND_URL is set, or localhost Flask off Vercel. */
export function flaskBaseUrl(): string | null {
  if (process.env.BACKEND_URL) return process.env.BACKEND_URL.replace(/\/$/, '')
  if (process.env.VERCEL) return null
  return 'http://127.0.0.1:5000'
}

export async function proxyFlask(
  path: string,
  init?: RequestInit
): Promise<Response | null> {
  const base = flaskBaseUrl()
  if (!base) return null
  try {
    const res = await fetch(`${base}${path.startsWith('/') ? path : `/${path}`}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers || {}),
      },
      cache: 'no-store',
    })
    return res
  } catch {
    return null
  }
}
