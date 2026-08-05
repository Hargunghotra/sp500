import { NextRequest, NextResponse } from 'next/server'
import { fetchAgentJsonl, proxyFlask } from '@/lib/agentData'

export async function GET(req: NextRequest) {
  const limit = Math.min(
    2000,
    Math.max(1, Number(req.nextUrl.searchParams.get('limit') || 500))
  )

  const proxied = await proxyFlask(`/api/portfolio/equity?limit=${limit}`)
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  const history = (await fetchAgentJsonl('data/equity.jsonl', limit)) as Array<{
    timestamp?: string
    equity?: number
    cash?: number
    positions_value?: number
    unrealized_pnl?: number
  }>

  const current = history[history.length - 1] || {
    timestamp: new Date().toISOString(),
    equity: 50000,
    cash: 50000,
    positions_value: 0,
    unrealized_pnl: 0,
  }

  return NextResponse.json({ history, current })
}
