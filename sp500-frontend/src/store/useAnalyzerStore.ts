import { create } from 'zustand'

export interface NewsItem {
  title: string
  link: string
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  score: number
}

export interface HistoryPoint {
  date: string
  price: number
  sma50?: number | null
}

export interface VolumePoint {
  date: string
  volume: number
}

export interface AnalysisData {
  ticker: string
  current_price: number
  sma50?: number
  trend: 'UP' | 'DOWN'
  score: number
  pattern: string
  sentiment: 'BULLISH' | 'BEARISH' | 'NEUTRAL'
  supportLevel: number
  resistanceLevel: number
  history: HistoryPoint[]
  volume: VolumePoint[]
  news: NewsItem[]
  breakoutPoints: unknown[]
}

interface AnalyzerState {
  analysisData: AnalysisData | null
  loading: boolean
  error: string | null
  fetchAnalysis: (ticker: string) => Promise<void>
}

export const useAnalyzerStore = create<AnalyzerState>((set) => ({
  analysisData: null,
  loading: false,
  error: null,
  fetchAnalysis: async (ticker) => {
    set({ loading: true, error: null })
    try {
      const res = await fetch('/api/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ticker }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to fetch')
      set({ analysisData: data, loading: false })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to fetch'
      set({ error: message, loading: false })
    }
  },
}))
