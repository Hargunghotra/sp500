import { NextResponse } from 'next/server'
import { proxyFlask } from '@/lib/agentData'

export async function POST() {
  const proxied = await proxyFlask('/api/portfolio/reset', { method: 'POST' })
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  return NextResponse.json(
    {
      error:
        'Reset requires a live Flask backend. On Vercel the book is managed by GitHub Actions (agent-data).',
    },
    { status: 501 }
  )
}
