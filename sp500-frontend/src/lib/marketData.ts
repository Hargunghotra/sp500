import YahooFinance from 'yahoo-finance2'

const yf = new YahooFinance({ suppressNotices: ['yahooSurvey'] })

function sentimentFromTitle(title: string): {
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  score: number
} {
  const t = title.toLowerCase()
  const bull = (
    t.match(
      /\b(surge|rally|gain|jump|soar|beat|record|upgrade|bullish|growth|rise|higher)\b/g
    ) || []
  ).length
  const bear = (
    t.match(
      /\b(fall|drop|plunge|miss|cut|downgrade|bearish|loss|slump|lower|weak)\b/g
    ) || []
  ).length
  const score = (bull - bear) * 0.2
  if (score > 0.05) return { sentiment: 'BULLISH', score }
  if (score < -0.05) return { sentiment: 'BEARISH', score }
  return { sentiment: 'NEUTRAL', score: 0 }
}

export async function fetchQuotes(
  symbols: string[]
): Promise<Record<string, number>> {
  const unique = [...new Set(symbols.filter(Boolean))]
  const out: Record<string, number> = {}
  if (!unique.length) return out

  try {
    const quotes = await yf.quote(unique.length === 1 ? unique[0] : unique)
    const list = Array.isArray(quotes) ? quotes : [quotes]
    for (const q of list) {
      const sym = String(q.symbol || '').toUpperCase()
      const price = Number(q.regularMarketPrice)
      if (sym && Number.isFinite(price) && price > 0) out[sym] = price
    }
  } catch {
    for (const sym of unique) {
      try {
        const q = await yf.quote(sym)
        const price = Number(q.regularMarketPrice)
        if (Number.isFinite(price) && price > 0) out[sym.toUpperCase()] = price
      } catch {
        continue
      }
    }
  }
  return out
}

export async function analyzeTickerServer(ticker: string) {
  const symbol = ticker.trim().toUpperCase()
  if (!symbol) throw new Error('ticker required')

  const period1 = new Date()
  period1.setMonth(period1.getMonth() - 6)

  const chart = await yf.chart(symbol, {
    period1,
    interval: '1d',
  })

  const quotes = (chart.quotes || []).filter(
    (q) => q.close != null && Number.isFinite(Number(q.close))
  )
  if (!quotes.length) throw new Error(`No data found for ${symbol}`)

  const closes = quotes.map((q) => Number(q.close))
  const highs = quotes.map((q) => Number(q.high ?? q.close))
  const lows = quotes.map((q) => Number(q.low ?? q.close))
  const volumes = quotes.map((q) => Number(q.volume ?? 0))
  const dates = quotes.map((q) => {
    const d = q.date instanceof Date ? q.date : new Date(q.date as string)
    return d.toISOString().slice(0, 10)
  })

  const sma50: (number | null)[] = closes.map((_, i) => {
    if (i < 49) return null
    const slice = closes.slice(i - 49, i + 1)
    return slice.reduce((a, b) => a + b, 0) / 50
  })

  const current_price = closes[closes.length - 1]
  const sma_50 = sma50[sma50.length - 1] ?? current_price
  const trend = current_price > sma_50 ? 'UP' : 'DOWN'
  const high_6m = Math.max(...highs)
  const score = Math.round((current_price / high_6m) * 100) / 10

  const window = 20
  const support = Math.min(...lows.slice(-window))
  const resistance = Math.max(...highs.slice(-window))
  const pattern =
    Math.abs(resistance - support) / current_price < 0.05
      ? 'Consolidating'
      : 'Volatile'

  let news: Array<{
    title: string
    link: string
    sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
    score: number
  }> = []
  try {
    const search = await yf.search(symbol)
    news = (search.news || []).slice(0, 8).map((n) => {
      const title = String(n.title || '')
      const { sentiment, score: s } = sentimentFromTitle(title)
      return {
        title,
        link: String(n.link || `https://finance.yahoo.com/quote/${symbol}`),
        sentiment,
        score: s,
      }
    })
  } catch {
    news = []
  }

  const avg =
    news.length > 0
      ? news.reduce((a, n) => a + n.score, 0) / news.length
      : 0
  const sentiment =
    avg > 0.05 ? 'BULLISH' : avg < -0.05 ? 'BEARISH' : 'NEUTRAL'

  return {
    ticker: symbol,
    current_price,
    sma50: sma_50,
    trend,
    score,
    pattern,
    sentiment,
    supportLevel: support,
    resistanceLevel: resistance,
    news,
    breakoutPoints: [],
    history: dates.map((date, i) => ({
      date,
      price: closes[i],
      sma50: sma50[i],
    })),
    volume: dates.map((date, i) => ({
      date,
      volume: volumes[i],
    })),
    source: 'yahoo-finance2',
  }
}

export function avgCostFromTrades(
  trades: Array<{ ticker?: string; type?: string; price?: number; shares?: number }>,
  symbol: string
): number | null {
  let qty = 0
  let cost = 0
  // Replay oldest→newest
  const ordered = [...trades].reverse()
  for (const t of ordered) {
    if (String(t.ticker || '').toUpperCase() !== symbol.toUpperCase()) continue
    const side = String(t.type || '').toUpperCase()
    const shares = Number(t.shares) || 0
    const price = Number(t.price) || 0
    if (shares <= 0 || price <= 0) continue
    if (side === 'BUY') {
      cost += price * shares
      qty += shares
    } else if (side === 'SELL' && qty > 0) {
      const sellQty = Math.min(qty, shares)
      const avg = cost / qty
      cost -= avg * sellQty
      qty -= sellQty
    }
  }
  if (qty <= 0) return null
  return cost / qty
}
