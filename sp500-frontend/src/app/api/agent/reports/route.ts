import { NextRequest, NextResponse } from 'next/server'
import { fetchAgentJsonl, proxyFlask } from '@/lib/agentData'

export async function GET(req: NextRequest) {
  const limit = Math.min(
    200,
    Math.max(1, Number(req.nextUrl.searchParams.get('limit') || 40))
  )

  const proxied = await proxyFlask(`/api/agent/reports?limit=${limit}`)
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  const rows = (await fetchAgentJsonl('data/reports.jsonl', limit * 2)) as Array<
    Record<string, unknown> & { id?: string; timestamp?: string }
  >
  const reports = [...rows].reverse().slice(0, limit).map((r, i) => ({
    id: r.id || `r-${i}-${r.timestamp || i}`,
    ...r,
  }))

  return NextResponse.json({ reports })
}
