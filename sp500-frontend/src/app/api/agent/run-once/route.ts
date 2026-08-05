import { NextResponse } from 'next/server'
import { proxyFlask } from '@/lib/agentData'
import { dispatchWorkflow } from '@/lib/dispatchWorkflow'
import { isExtendedSessionNow, nextAgentCronRun } from '@/lib/sessionSchedule'

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
    return NextResponse.json(
      {
        error: result.error,
        result: { ok: false, error: result.error },
        status: {
          enabled: true,
          running: false,
          next_run: nextAgentCronRun(),
          in_session: isExtendedSessionNow(),
          can_dispatch: false,
          source: 'github-actions',
        },
      },
      { status: 503 }
    )
  }

  return NextResponse.json({
    result: {
      ok: true,
      message:
        'Dispatched GitHub Actions Agent cron (force=true). Check Actions in 1–2 minutes; a trade email will send if it fills.',
    },
    status: {
      enabled: true,
      running: true,
      next_run: nextAgentCronRun(),
      in_session: isExtendedSessionNow(),
      can_dispatch: true,
      last_run: new Date().toISOString(),
      source: 'github-actions-dispatch',
    },
  })
}
