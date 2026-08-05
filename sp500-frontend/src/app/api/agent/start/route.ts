import { NextResponse } from 'next/server'
import { proxyFlask } from '@/lib/agentData'

export async function POST() {
  const proxied = await proxyFlask('/api/agent/start', { method: 'POST' })
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  // On Vercel, "start" means the Actions schedule is already the always-on agent.
  return NextResponse.json({
    enabled: true,
    running: false,
    message:
      'Autonomous trading is already scheduled via GitHub Actions (Agent cron). Use Run once to dispatch a cycle now.',
    source: 'github-actions',
  })
}
