import { NextResponse } from 'next/server'
import {
  fetchAgentJson,
  fetchAgentJsonl,
  proxyFlask,
} from '@/lib/agentData'
import { isExtendedSessionNow, nextAgentCronRun } from '@/lib/sessionSchedule'

export async function GET() {
  const proxied = await proxyFlask('/api/agent/status')
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  const strategy = await fetchAgentJson<Record<string, unknown>>('data/strategy.json')
  const reports = (await fetchAgentJsonl('data/reports.jsonl', 5)) as Array<{
    timestamp?: string
    executed_count?: number
    skipped?: boolean
    reason?: string
    screened_count?: number
    universe_size?: number
  }>
  const last = reports[reports.length - 1] || null
  const inSession = isExtendedSessionNow()
  const nextRun = nextAgentCronRun()
  const canDispatch = Boolean(process.env.GITHUB_TOKEN || process.env.GH_TOKEN)

  return NextResponse.json({
    enabled: true,
    running: false,
    last_run: last?.timestamp ?? null,
    next_run: nextRun,
    last_error: null,
    model: strategy?.model ?? 'gemini-flash-latest',
    has_api_key: true,
    interval_minutes: 15,
    scheduler_running: true,
    screened_count: last?.screened_count,
    universe_size: last?.universe_size ?? 500,
    strategy,
    allow_after_hours: false,
    trading_session: 'extended',
    session_label: 'extended 4:00–20:00 ET (GitHub Actions)',
    in_session: inSession,
    can_dispatch: canDispatch,
    last_cycle_summary: last
      ? {
          executed_count: last.executed_count,
          skipped: last.skipped,
          reason: last.reason,
        }
      : null,
    source: 'github-agent-data',
  })
}
