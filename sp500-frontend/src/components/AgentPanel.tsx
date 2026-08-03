'use client'

import { Bot, Play, Square, Zap } from 'lucide-react'
import { useAgentStore } from '@/store/useAgentStore'
import { useTradingStore } from '@/store/useTradingStore'

function fmt(ts?: string | null) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ts
  }
}

export default function AgentPanel() {
  const { status, acting, error, startAgent, stopAgent, runOnce, fetchReports } =
    useAgentStore()
  const { fetchPortfolio } = useTradingStore()
  const enabled = status?.enabled

  const onRunOnce = async () => {
    await runOnce()
    await Promise.all([fetchPortfolio(), fetchReports()])
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-[#2962ff]/15 border border-[#2962ff]/40 flex items-center justify-center">
            <Bot className="h-4 w-4 text-[#2962ff]" />
          </div>
          <div>
            <div className="text-sm font-semibold text-white">AI Trade Agent</div>
            <div className="text-[11px] font-mono text-[#787b86]">
              {status?.model ?? '—'} · every {status?.interval_minutes ?? '—'}m
            </div>
          </div>
        </div>
        <span
          className={`text-[10px] font-mono px-2 py-1 rounded border ${
            enabled
              ? 'border-[#089981] text-[#089981] bg-[#089981]/10'
              : 'border-[#787b86] text-[#787b86] bg-[#787b86]/10'
          }`}
        >
          {status?.running ? 'RUNNING CYCLE' : enabled ? 'ARMED' : 'STOPPED'}
        </span>
      </div>

      {!status?.has_api_key && (
        <div className="text-xs font-mono text-[#f23645] border border-[#f23645]/30 bg-[#f23645]/10 rounded px-3 py-2">
          Set GEMINI_API_KEY in sp500-backend/.env to enable autonomous trades.
        </div>
      )}

      {error && (
        <div className="text-xs font-mono text-[#f23645] border border-[#f23645]/30 bg-[#f23645]/10 rounded px-3 py-2">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-[#787b86]">
        <div>
          Last run
          <div className="text-[#d1d4dc] mt-0.5">{fmt(status?.last_run)}</div>
        </div>
        <div>
          Next run
          <div className="text-[#d1d4dc] mt-0.5">{fmt(status?.next_run)}</div>
        </div>
        <div className="col-span-2">
          Watchlist
          <div className="text-[#d1d4dc] mt-0.5 break-all">
            {(status?.watchlist || []).join(', ') || '—'}
          </div>
        </div>
      </div>

      <div className="flex gap-2">
        {enabled ? (
          <button
            onClick={() => stopAgent()}
            disabled={acting}
            className="flex-1 flex items-center justify-center gap-1.5 bg-[#2a2e39] hover:bg-[#363a45] disabled:opacity-60 text-white py-2 rounded text-sm font-semibold transition-colors"
          >
            <Square className="h-3.5 w-3.5" />
            Stop
          </button>
        ) : (
          <button
            onClick={() => startAgent()}
            disabled={acting || !status?.has_api_key}
            className="flex-1 flex items-center justify-center gap-1.5 bg-[#089981] hover:bg-[#067c69] disabled:opacity-60 text-white py-2 rounded text-sm font-semibold transition-colors"
          >
            <Play className="h-3.5 w-3.5" />
            Start 24/7
          </button>
        )}
        <button
          onClick={() => onRunOnce()}
          disabled={acting || !status?.has_api_key}
          className="flex-1 flex items-center justify-center gap-1.5 bg-[#2962ff] hover:bg-[#1e53e5] disabled:opacity-60 text-white py-2 rounded text-sm font-semibold transition-colors"
        >
          <Zap className="h-3.5 w-3.5" />
          Run once
        </button>
      </div>
    </div>
  )
}
