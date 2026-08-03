'use client'

import { useAgentStore } from '@/store/useAgentStore'

function fmt(ts?: string) {
  if (!ts) return '—'
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ts
  }
}

export default function TradeReportsPanel() {
  const { reports, loading } = useAgentStore()

  if (loading && !reports.length) {
    return <div className="text-[#787b86] text-xs font-mono p-2">Loading reports…</div>
  }

  if (!reports.length) {
    return (
      <div className="text-[#787b86] text-xs font-mono p-2">
        No agent cycles yet. Start the agent or click Run once.
      </div>
    )
  }

  return (
    <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
      {reports.map((report) => (
        <article
          key={report.id}
          className="rounded-lg border border-[#2a2e39] bg-[#131722] p-3 space-y-2"
        >
          <div className="flex items-center justify-between gap-2 text-[10px] font-mono text-[#787b86]">
            <span>{fmt(report.timestamp)}</span>
            <span>
              {report.skipped
                ? 'SKIPPED'
                : report.error
                  ? 'ERROR'
                  : `${report.executed_count ?? 0} trades`}
            </span>
          </div>

          {report.reason && (
            <p className="text-xs text-[#d1d4dc] font-mono">{report.reason}</p>
          )}
          {report.error && (
            <p className="text-xs text-[#f23645] font-mono">{report.error}</p>
          )}

          {(report.decisions || []).map((d, i) => (
            <div
              key={`${report.id}-${d.ticker}-${i}`}
              className="border-t border-[#2a2e39] pt-2 space-y-1"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="text-sm font-mono text-white">
                  {d.ticker}{' '}
                  <span
                    className={
                      d.action === 'BUY'
                        ? 'text-[#089981]'
                        : d.action === 'SELL'
                          ? 'text-[#f23645]'
                          : 'text-[#787b86]'
                    }
                  >
                    {d.action}
                  </span>
                  {d.executed ? (
                    <span className="ml-2 text-[10px] text-[#2962ff]">EXECUTED</span>
                  ) : null}
                </div>
                <div className="text-[10px] font-mono text-[#787b86]">
                  conf {(d.confidence ?? 0).toFixed(2)}
                  {d.shares ? ` · ${d.shares} sh` : ''}
                </div>
              </div>
              <p className="text-xs text-[#d1d4dc] leading-relaxed">{d.reasoning}</p>
              {d.skip_reason && (
                <p className="text-[10px] font-mono text-[#787b86]">
                  Skip: {d.skip_reason}
                </p>
              )}
              {d.error && (
                <p className="text-[10px] font-mono text-[#f23645]">{d.error}</p>
              )}
            </div>
          ))}
        </article>
      ))}
    </div>
  )
}
