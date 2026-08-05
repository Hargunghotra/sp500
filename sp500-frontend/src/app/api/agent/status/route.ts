import { NextResponse } from 'next/server'
import {
  fetchAgentJson,
  fetchAgentJsonl,
  proxyFlask,
} from '@/lib/agentData'

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
  }>
  const last = reports[reports.length - 1] || null

  return NextResponse.json({
    enabled: true,
    running: false,
    last_run: last?.timestamp ?? null,
    next_run: null,
    last_error: null,
    model: strategy?.model ?? 'gemini-flash-latest',
    has_api_key: true,
    interval_minutes: 15,
    scheduler_running: true,
    universe_size: 500,
    strategy,
    allow_after_hours: false,
    trading_session: 'extended',
    session_label: 'extended 4:00–20:00 ET (GitHub Actions)',
    in_session: null,
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
