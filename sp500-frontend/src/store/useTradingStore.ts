import { create } from 'zustand'

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
  source?: 'ai' | 'manual' | string
}

interface TradingState {
  balance: number
  positions: Record<string, number>
  trades: Trade[]
  loading: boolean
  error: string | null
  fetchPortfolio: () => Promise<void>
  executeTrade: (
    ticker: string,
    type: 'BUY' | 'SELL',
    price: number,
    shares: number,
    pattern: string
  ) => Promise<boolean>
}

export const useTradingStore = create<TradingState>((set) => ({
  balance: 100000,
  positions: {},
  trades: [],
  loading: false,
  error: null,
  fetchPortfolio: async () => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/portfolio')
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to load portfolio')
      set({
        balance: data.balance,
        positions: data.positions || {},
        trades: data.trades || [],
        loading: false,
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load portfolio'
      set({ error: message, loading: false })
    }
  },
  executeTrade: async (ticker, type, price, shares, pattern) => {
    set({ error: null })
    try {
      const res = await fetch('/api/trade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker, type, price, shares, pattern }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Trade failed')
      const portfolio = data.portfolio
      set({
        balance: portfolio.balance,
        positions: portfolio.positions || {},
        trades: portfolio.trades || [],
      })
      return true
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Trade failed'
      set({ error: message })
      return false
    }
  },
}))
