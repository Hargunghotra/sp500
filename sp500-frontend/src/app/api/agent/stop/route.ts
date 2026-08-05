import { NextResponse } from 'next/server'
import { proxyFlask } from '@/lib/agentData'

export async function POST() {
  const proxied = await proxyFlask('/api/agent/stop', { method: 'POST' })
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  return NextResponse.json({
    enabled: false,
    running: false,
    message:
      'To fully stop cloud trading, disable the Agent cron workflow in GitHub Actions. Local stop only applies when Flask is running.',
    source: 'github-actions',
  })
}
