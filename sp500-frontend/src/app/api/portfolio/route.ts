import { NextResponse } from 'next/server'
import {
  fetchAgentJson,
  fetchAgentJsonl,
  proxyFlask,
} from '@/lib/agentData'
import { avgCostFromTrades, fetchQuotes } from '@/lib/marketData'

type PositionValue =
  | number
  | {
      symbol?: string
      quantity?: number
      avg_price?: number
      stop_loss?: number | null
      take_profit?: number | null
      asset_class?: string
      side?: string
      opened_at?: string
    }

type Trade = {
  ticker?: string
  type?: string
  price?: number
  shares?: number
}

async function buildPositionRows(
  positions: Record<string, PositionValue>,
  trades: Trade[]
) {
  const symbols: string[] = []
  const parsed: Array<{
    symbol: string
    quantity: number
    avg_price: number
    stop_loss: number | null
    take_profit: number | null
    asset_class: string
    side: string
    opened_at: string | null
  }> = []

  for (const [key, value] of Object.entries(positions || {})) {
    if (typeof value === 'number') {
      const symbol = key.toUpperCase()
      const fromTrades = avgCostFromTrades(trades, symbol)
      parsed.push({
        symbol,
        quantity: value,
        avg_price: fromTrades ?? 0,
        stop_loss: null,
        take_profit: null,
        asset_class: 'equity',
        side: 'LONG',
        opened_at: null,
      })
      symbols.push(symbol)
      continue
    }
    const symbol = String(value.symbol || key).toUpperCase()
    const qty = Number(value.quantity) || 0
    let avg = Number(value.avg_price) || 0
    if (!avg) avg = avgCostFromTrades(trades, symbol) ?? 0
    parsed.push({
      symbol,
      quantity: qty,
      avg_price: avg,
      stop_loss: value.stop_loss ?? null,
      take_profit: value.take_profit ?? null,
      asset_class: value.asset_class || 'equity',
      side: value.side || 'LONG',
      opened_at: value.opened_at ?? null,
    })
    symbols.push(symbol)
  }

  const prices = await fetchQuotes(symbols)
  let unrealizedTotal = 0
  let positionsValue = 0

  const rows = parsed.map((p) => {
    const last = prices[p.symbol] ?? p.avg_price
    const trade_value = Math.round(p.avg_price * p.quantity * 100) / 100
    const market_value = Math.round(last * p.quantity * 100) / 100
    const unrealized_pnl =
      p.avg_price > 0
        ? Math.round((last - p.avg_price) * p.quantity * 100) / 100
        : 0
    const unrealized_pnl_pct =
      p.avg_price > 0
        ? Math.round(((last / p.avg_price) - 1) * 10000) / 100
        : 0
    unrealizedTotal += unrealized_pnl
    positionsValue += market_value

    // Default SL/TP display if missing (3%/6% equity)
    let stop_loss = p.stop_loss
    let take_profit = p.take_profit
    if (p.avg_price > 0) {
      if (stop_loss == null) stop_loss = Math.round(p.avg_price * 0.97 * 100) / 100
      if (take_profit == null) take_profit = Math.round(p.avg_price * 1.06 * 100) / 100
    }

    return {
      symbol: p.symbol,
      asset_class: p.asset_class,
      side: p.side,
      quantity: p.quantity,
      avg_price: Math.round(p.avg_price * 100) / 100,
      stop_loss,
      take_profit,
      last_price: Math.round(last * 100) / 100,
      unrealized_pnl,
      unrealized_pnl_pct,
      trade_value,
      market_value,
      opened_at: p.opened_at,
    }
  })

  return { rows, unrealizedTotal, positionsValue }
}

export async function GET() {
  const proxied = await proxyFlask('/api/portfolio')
  if (proxied) {
    const body = await proxied.text()
    return new NextResponse(body, {
      status: proxied.status,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  const book = await fetchAgentJson<{
    balance?: number
    positions?: Record<string, PositionValue>
    trades?: Trade[]
    realized_pnl?: number
  }>('data/portfolio.json')

  if (!book) {
    return NextResponse.json(
      {
        error:
          'No agent-data ledger found. Run Agent cron on GitHub or start local Flask.',
      },
      { status: 503 }
    )
  }

  const equityRows = (await fetchAgentJsonl('data/equity.jsonl', 5)) as Array<{
    equity?: number
    positions_value?: number
    unrealized_pnl?: number
  }>
  const lastEq = equityRows[equityRows.length - 1] || {}
  const { rows, unrealizedTotal, positionsValue } = await buildPositionRows(
    book.positions || {},
    book.trades || []
  )
  const cash = Number(book.balance) || 0
  const liveEquity = Math.round((cash + positionsValue) * 100) / 100

  return NextResponse.json({
    ...book,
    equity: liveEquity || lastEq.equity || cash,
    positions_value: positionsValue || lastEq.positions_value || 0,
    unrealized_pnl: unrealizedTotal,
    realized_pnl: book.realized_pnl ?? 0,
    position_rows: rows,
    mtm: {
      equity: liveEquity,
      cash,
      positions_value: positionsValue,
      unrealized_pnl: unrealizedTotal,
      position_rows: rows,
      source: 'github-agent-data+yahoo',
    },
  })
}
