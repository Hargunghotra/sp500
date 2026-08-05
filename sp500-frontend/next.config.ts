import type { NextConfig } from 'next'
import path from 'path'

/**
 * Local Flask proxy is optional. Prefer App Router `/api/*` handlers which:
 * - proxy to BACKEND_URL or localhost:5000 when available
 * - otherwise read the GitHub `agent-data` ledger (phone / Vercel / PC off)
 */
const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname),
  },
}

export default nextConfig
