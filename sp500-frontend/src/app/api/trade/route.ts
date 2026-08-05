import { NextRequest, NextResponse } from 'next/server'
import { proxyFlask } from '@/lib/agentData'

export async function POST(req: NextRequest) {
  const bodyText = await req.text()
  const proxied = await proxyFlask('/api/trade', {
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

  return NextResponse.json(
    {
      error:
        'Manual trades require local Flask. Autonomous trades run via GitHub Actions.',
    },
    { status: 501 }
  )
}
