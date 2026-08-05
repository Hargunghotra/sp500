import { NextRequest, NextResponse } from 'next/server'
import { proxyFlask } from '@/lib/agentData'
import { analyzeTickerServer } from '@/lib/marketData'

export async function POST(req: NextRequest) {
  const bodyText = await req.text()
  const proxied = await proxyFlask('/api/analyze', {
    method: 'POST',
    body: bodyText,
  })
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const data = JSON.parse(bodyText || '{}') as { ticker?: string }
    const ticker = String(data.ticker || 'SPY')
    const result = await analyzeTickerServer(ticker)
    return NextResponse.json(result)
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : 'Analyze failed'
    const status = /no data/i.test(message) ? 404 : 500
    return NextResponse.json({ error: message }, { status })
  }
}
