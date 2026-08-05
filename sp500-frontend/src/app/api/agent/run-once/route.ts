import { NextResponse } from 'next/server'
import { proxyFlask } from '@/lib/agentData'
import { dispatchWorkflow } from '@/lib/dispatchWorkflow'

export async function POST() {
  const proxied = await proxyFlask('/api/agent/run-once', {
    method: 'POST',
    body: JSON.stringify({ force: true }),
  })
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  const result = await dispatchWorkflow('agent-cron.yml', { force: true })
  if (!result.ok) {
    return NextResponse.json({ error: result.error }, { status: 503 })
  }

  return NextResponse.json({
    result: {
      ok: true,
      message: 'Dispatched GitHub Actions Agent cron (force=true). Refresh in 1–2 minutes.',
    },
    status: {
      enabled: true,
      running: true,
      source: 'github-actions-dispatch',
    },
  })
}
