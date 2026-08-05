import { create } from 'zustand'
import { parseJsonResponse } from '@/lib/parseJson'

export interface Trade {
  id: string
  ticker: string
  type: 'BUY' | 'SELL'
  price: number
  shares: number
  date: string
  pattern: string
  reasoning?: string
  confidence?: number | null
  source?: 'ai' | 'manual' | 'stop_loss' | 'take_profit' | string
  stop_loss?: number | null
  take_profit?: number | null
  realized_pnl?: number | null
  asset_class?: string
}

export interface PositionRow {
  symbol: string
  asset_class: string
  side: string
  quantity: number
  avg_price: number
  stop_loss: number | null
  take_profit: number | null
  last_price: number
  unrealized_pnl: number
  unrealized_pnl_pct: number
  trade_value: number
  market_value: number
  opened_at?: string | null
}

/** Rich position object or legacy share count */
export type PositionValue =
  | number
  | {
      symbol?: string
      quantity: number
      avg_price?: number
      stop_loss?: number | null
      take_profit?: number | null
      asset_class?: string
      side?: string
    }

export function positionQty(
  positions: Record<string, PositionValue>,
  symbol: string
): number {
  const p = positions[symbol]
  if (p == null) return 0
  if (typeof p === 'number') return p
  return Number(p.quantity) || 0
}

interface TradingState {
  balance: number
  equity: number
  positionsValue: number
  unrealizedPnl: number
  realizedPnl: number
  positions: Record<string, PositionValue>
  positionRows: PositionRow[]
  trades: Trade[]
  loading: boolean
  error: string | null
  fetchPortfolio: () => Promise<void>
  resetPortfolio: () => Promise<boolean>
  executeTrade: (
    ticker: string,
    type: 'BUY' | 'SELL',
    price: number,
    shares: number,
    pattern: string,
    levels?: { stop_loss?: number; take_profit?: number }
  ) => Promise<boolean>
  closePosition: (row: PositionRow) => Promise<boolean>
}

export const useTradingStore = create<TradingState>((set, get) => ({
  balance: 50000,
  equity: 50000,
  positionsValue: 0,
  unrealizedPnl: 0,
  realizedPnl: 0,
  positions: {},
  positionRows: [],
  trades: [],
  loading: false,
  error: null,
  fetchPortfolio: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/portfolio')
      const data = await parseJsonResponse<{
        balance: number
        equity?: number
        positions_value?: number
        unrealized_pnl?: number
        realized_pnl?: number
        positions?: Record<string, PositionValue>
        position_rows?: PositionRow[]
        mtm?: { position_rows?: PositionRow[] }
        trades?: Trade[]
        error?: string
      }>(res)
      if (!res.ok) throw new Error(data.error || 'Failed to load portfolio')
      set({
        balance: data.balance,
        equity: data.equity ?? data.balance,
        positionsValue: data.positions_value ?? 0,
        unrealizedPnl: data.unrealized_pnl ?? 0,
        realizedPnl: data.realized_pnl ?? 0,
        positions: data.positions || {},
        positionRows: data.position_rows || data.mtm?.position_rows || [],
        trades: data.trades || [],
        loading: false,
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load portfolio'
      set({ error: message, loading: false })
    }
  },
  resetPortfolio: async () => {
    set({ error: null })
    try {
      const res = await fetch('/api/portfolio/reset', { method: 'POST' })
      const data = await parseJsonResponse<{
        portfolio: {
          balance: number
        }
        error?: string
      }>(res)
      if (!res.ok) throw new Error(data.error || 'Reset failed')
      const portfolio = data.portfolio
      set({
        balance: portfolio.balance,
        equity: portfolio.balance,
        positionsValue: 0,
        unrealizedPnl: 0,
        realizedPnl: 0,
        positions: {},
        positionRows: [],
        trades: [],
      })
      return true
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Reset failed'
      set({ error: message })
      return false
    }
  },
  executeTrade: async (ticker, type, price, shares, pattern, levels) => {
    set({ error: null })
    try {
      const res = await fetch('/api/trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ticker,
          type,
          price,
          shares,
          pattern,
          stop_loss: levels?.stop_loss,
          take_profit: levels?.take_profit,
        }),
      })
      const data = await parseJsonResponse<{
        portfolio: {
          balance: number
          positions?: Record<string, PositionValue>
          trades?: Trade[]
          realized_pnl?: number
        }
        equity?: {
          equity?: number
          positions_value?: number
          unrealized_pnl?: number
          realized_pnl?: number
          position_rows?: PositionRow[]
        }
        error?: string
      }>(res)
      if (!res.ok) throw new Error(data.error || 'Trade failed')
      const portfolio = data.portfolio
      set({
        balance: portfolio.balance,
        equity: data.equity?.equity ?? portfolio.balance,
        positionsValue: data.equity?.positions_value ?? 0,
        unrealizedPnl: data.equity?.unrealized_pnl ?? 0,
        realizedPnl: data.equity?.realized_pnl ?? portfolio.realized_pnl ?? 0,
        positions: portfolio.positions || {},
        positionRows: data.equity?.position_rows || [],
        trades: portfolio.trades || [],
      })
      return true
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Trade failed'
      set({ error: message })
      return false
    }
  },
  closePosition: async (row) => {
    return get().executeTrade(
      row.symbol,
      'SELL',
      row.last_price,
      row.quantity,
      'Manual close'
    )
  },
}))
