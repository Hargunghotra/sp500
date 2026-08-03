import { create } from 'zustand'

export interface AgentDecision {
  ticker: string
  action: 'BUY' | 'SELL' | 'HOLD' | string
  shares: number
  confidence: number
  reasoning: string
  executed?: boolean
  trade_id?: string | null
  skip_reason?: string | null
  error?: string | null
  price?: number
  pattern?: string
}

export interface AiTradeReport {
  headline: string
  summary: string
  market_read: string
  risk_notes: string
  outlook: string
  model?: string
  error?: string
}

export interface AgentReport {
  id: string
  timestamp: string
  type?: string
  skipped?: boolean
  reason?: string
  error?: string
  executed_count?: number
  decisions?: AgentDecision[]
  ai_report?: AiTradeReport | null
  ok?: boolean
}

export interface AgentStatus {
  enabled: boolean
  running: boolean
  last_run: string | null
  next_run: string | null
  last_error: string | null
  watchlist: string[]
  model: string
  has_api_key: boolean
  interval_minutes: number
  scheduler_running: boolean
  min_confidence?: number
  max_cash_pct_per_buy?: number
  max_open_tickers?: number
  allow_after_hours?: boolean
  last_cycle_summary?: {
    executed_count?: number
    skipped?: boolean
    reason?: string
  } | null
}

interface AgentState {
  status: AgentStatus | null
  reports: AgentReport[]
  loading: boolean
  acting: boolean
  error: string | null
  fetchStatus: () => Promise<void>
  fetchReports: () => Promise<void>
  startAgent: () => Promise<void>
  stopAgent: () => Promise<void>
  runOnce: () => Promise<void>
}

export const useAgentStore = create<AgentState>((set) => ({
  status: null,
  reports: [],
  loading: false,
  acting: false,
  error: null,
  fetchStatus: async () => {
    try {
      const res = await fetch('/api/agent/status')
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to load agent status')
      set({ status: data, error: null })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load agent status'
      set({ error: message })
    }
  },
  fetchReports: async () => {
    set({ loading: true })
    try {
      const res = await fetch('/api/agent/reports?limit=40')
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to load reports')
      set({ reports: data.reports || [], loading: false, error: null })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load reports'
      set({ error: message, loading: false })
    }
  },
  startAgent: async () => {
    set({ acting: true, error: null })
    try {
      const res = await fetch('/api/agent/start', { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to start agent')
      set({ status: data, acting: false })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start agent'
      set({ error: message, acting: false })
    }
  },
  stopAgent: async () => {
    set({ acting: true, error: null })
    try {
      const res = await fetch('/api/agent/stop', { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to stop agent')
      set({ status: data, acting: false })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to stop agent'
      set({ error: message, acting: false })
    }
  },
  runOnce: async () => {
    set({ acting: true, error: null })
    try {
      const res = await fetch('/api/agent/run-once', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ force: true }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || data.result?.error || 'Run failed')
      if (data.status) set({ status: data.status })
      const reportsRes = await fetch('/api/agent/reports?limit=40')
      const reportsData = await reportsRes.json()
      set({
        reports: reportsData.reports || [],
        acting: false,
        error: data.result?.ok === false ? data.result?.error || 'Cycle failed' : null,
      })
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Run failed'
      set({ error: message, acting: false })
    }
  },
}))
