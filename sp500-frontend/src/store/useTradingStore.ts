import { create } from 'zustand'

export interface Trade {
  id: string
  ticker: string
  type: 'BUY' | 'SELL'
  price: number
  shares: number
  date: string
  pattern: string
}

interface TradingState {
  balance: number
  positions: Record<string, number>
  trades: Trade[]
  executeTrade: (
    ticker: string,
    type: 'BUY' | 'SELL',
    price: number,
    shares: number,
    pattern: string
  ) => void
}

export const useTradingStore = create<TradingState>((set) => ({
  balance: 100000,
  positions: {},
  trades: [],
  executeTrade: (ticker, type, price, shares, pattern) =>
    set((state) => {
      const cost = price * shares
      if (type === 'BUY' && state.balance < cost) return state
      if (type === 'SELL' && (state.positions[ticker] || 0) < shares) return state

      const newBalance = type === 'BUY' ? state.balance - cost : state.balance + cost
      const currentShares = state.positions[ticker] || 0
      const newShares = type === 'BUY' ? currentShares + shares : currentShares - shares

      const newPositions = { ...state.positions }
      if (newShares === 0) delete newPositions[ticker]
      else newPositions[ticker] = newShares

      const newTrade: Trade = {
        id: Math.random().toString(36).substring(7),
        ticker,
        type,
        price,
        shares,
        pattern,
        date: new Date().toISOString(),
      }

      return {
        balance: newBalance,
        positions: newPositions,
        trades: [newTrade, ...state.trades],
      }
    }),
}))
