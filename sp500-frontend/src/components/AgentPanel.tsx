'use client'

import { Bot, Play, RotateCcw, Square, Zap } from 'lucide-react'
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
  const { balance, equity, fetchPortfolio, resetPortfolio } = useTradingStore()
  const enabled = status?.enabled
  const strategy = status?.strategy

  const onRunOnce = async () => {
    await runOnce()
    await Promise.all([fetchPortfolio(), fetchReports()])
  }

  const onReset = async () => {
    if (!confirm('Reset paper portfolio to $50,000 and clear trades/reports?')) return
    await resetPortfolio()
    await fetchReports()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-[#2962ff]/20 border border-white/10 flex items-center justify-center shadow-[0_0_24px_rgba(41,98,255,0.25)]">
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
          className={`text-[10px] font-mono px-2 py-1 rounded-full border backdrop-blur ${
            enabled
              ? 'border-[#089981]/50 text-[#089981] bg-[#089981]/15'
              : 'border-white/15 text-[#787b86] bg-white/5'
          }`}
        >
          {status?.running ? 'RUNNING CYCLE' : enabled ? 'ARMED' : 'STOPPED'}
        </span>
      </div>

      {!status?.has_api_key && (
        <div className="text-xs font-mono text-[#f23645] border border-[#f23645]/30 bg-[#f23645]/10 rounded-xl px-3 py-2">
          Set GEMINI_API_KEY in sp500-backend/.env to enable autonomous trades.
        </div>
      )}

      {error && (
        <div className="text-xs font-mono text-[#f23645] border border-[#f23645]/30 bg-[#f23645]/10 rounded-xl px-3 py-2">
          {error}
        </div>
      )}

      <div className="grid grid-cols-2 gap-2 text-[11px] font-mono text-[#787b86]">
        <div className="rounded-xl bg-white/[0.03] border border-white/5 p-2.5">
          Equity
          <div className="text-white mt-0.5 text-sm">
            ${equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="rounded-xl bg-white/[0.03] border border-white/5 p-2.5">
          Cash
          <div className="text-white mt-0.5 text-sm">
            ${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div>
          Last run
          <div className="text-[#d1d4dc] mt-0.5">{fmt(status?.last_run)}</div>
        </div>
        <div>
          Next run
          <div className="text-[#d1d4dc] mt-0.5">{fmt(status?.next_run)}</div>
        </div>
        <div className="col-span-2">
          Universe
          <div className="text-[#d1d4dc] mt-0.5">
            S&amp;P {status?.universe_size || 500} · shortlist {status?.screened_count ?? '—'}
          </div>
        </div>
      </div>

      {strategy?.thesis && (
        <div className="rounded-xl border border-[#2962ff]/25 bg-[#2962ff]/10 p-3 space-y-2">
          <div className="text-[10px] uppercase tracking-wider font-mono text-[#787b86]">
            Strategy thesis
          </div>
          <p className="text-xs text-[#d1d4dc] leading-relaxed">{strategy.thesis}</p>
          {(strategy.preferred_sectors?.length || strategy.styles?.length) ? (
            <div className="flex flex-wrap gap-1.5">
              {(strategy.preferred_sectors || []).map((s) => (
                <span
                  key={`sec-${s}`}
                  className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-[#d1d4dc]"
                >
                  {s}
                </span>
              ))}
              {(strategy.styles || []).map((s) => (
                <span
                  key={`style-${s}`}
                  className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-[#089981]/15 border border-[#089981]/30 text-[#089981]"
                >
                  {s}
                </span>
              ))}
            </div>
          ) : null}
          {strategy.risk_posture && (
            <div className="text-[10px] font-mono text-[#787b86]">
              Risk: <span className="text-[#d1d4dc]">{strategy.risk_posture}</span>
            </div>
          )}
        </div>
      )}

      <div className="flex gap-2">
        {enabled ? (
          <button
            onClick={() => stopAgent()}
            disabled={acting}
            className="flex-1 flex items-center justify-center gap-1.5 glass-btn disabled:opacity-60 text-white py-2.5 rounded-xl text-sm font-semibold"
          >
            <Square className="h-3.5 w-3.5" />
            Stop
          </button>
        ) : (
          <button
            onClick={() => startAgent()}
            disabled={acting || !status?.has_api_key}
            className="flex-1 flex items-center justify-center gap-1.5 bg-[#089981]/90 hover:bg-[#089981] disabled:opacity-60 text-white py-2.5 rounded-xl text-sm font-semibold transition-all"
          >
            <Play className="h-3.5 w-3.5" />
            Start 24/7
          </button>
        )}
        <button
          onClick={() => onRunOnce()}
          disabled={acting || !status?.has_api_key}
          className="flex-1 flex items-center justify-center gap-1.5 bg-[#2962ff]/90 hover:bg-[#2962ff] disabled:opacity-60 text-white py-2.5 rounded-xl text-sm font-semibold transition-all"
        >
          <Zap className="h-3.5 w-3.5" />
          Run once
        </button>
      </div>
      <button
        onClick={() => onReset()}
        disabled={acting}
        className="w-full flex items-center justify-center gap-1.5 text-[11px] font-mono text-[#787b86] hover:text-white transition-colors py-1"
      >
        <RotateCcw className="h-3 w-3" />
        Reset book to $50,000
      </button>
    </div>
  )
}
