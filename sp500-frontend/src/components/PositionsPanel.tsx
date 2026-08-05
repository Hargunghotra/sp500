'use client'

import { useTradingStore, type PositionRow } from '@/store/useTradingStore'

function fmtPrice(n: number | null | undefined, digits = 2) {
  if (n == null || Number.isNaN(n)) return '—'
  return n.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: Math.max(digits, n < 1 ? 5 : digits),
  })
}

function fmtQty(n: number) {
  if (Number.isInteger(n)) return String(n)
  return n.toLocaleString(undefined, { maximumFractionDigits: 6 })
}

function pnlClass(n: number) {
  if (n > 0) return 'text-[#089981]'
  if (n < 0) return 'text-[#f23645]'
  return 'text-[#787b86]'
}

export default function PositionsPanel() {
  const { positionRows, closePosition, error } = useTradingStore()

  const onClose = async (row: PositionRow) => {
    if (!confirm(`Close ${row.symbol} × ${fmtQty(row.quantity)} @ ${fmtPrice(row.last_price)}?`)) {
      return
    }
    await closePosition(row)
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">Positions</h2>
        <span className="text-[10px] font-mono text-[#787b86]">
          {positionRows.length} open · mark-to-market
        </span>
      </div>
      {error && (
        <div className="text-xs font-mono text-[#f23645]">{error}</div>
      )}
      <div className="overflow-x-auto border border-white/10 rounded-xl bg-black/25 backdrop-blur">
        <table className="w-full min-w-[960px] text-[11px] font-mono text-left">
          <thead className="text-[#787b86] sticky top-0 bg-[#131722]/95 backdrop-blur">
            <tr className="border-b border-white/10">
              <th className="px-3 py-2.5 font-medium">Symbol</th>
              <th className="px-2 py-2.5 font-medium">Side</th>
              <th className="px-2 py-2.5 font-medium text-right">Qty</th>
              <th className="px-2 py-2.5 font-medium text-right">Avg</th>
              <th className="px-2 py-2.5 font-medium text-right">Last</th>
              <th className="px-2 py-2.5 font-medium text-right">SL</th>
              <th className="px-2 py-2.5 font-medium text-right">TP</th>
              <th className="px-2 py-2.5 font-medium text-right">Unrealized $</th>
              <th className="px-2 py-2.5 font-medium text-right">Unrealized %</th>
              <th className="px-2 py-2.5 font-medium text-right">Trade val</th>
              <th className="px-2 py-2.5 font-medium text-right">Mkt val</th>
              <th className="px-3 py-2.5 font-medium text-right"> </th>
            </tr>
          </thead>
          <tbody>
            {positionRows.length === 0 ? (
              <tr>
                <td colSpan={12} className="px-3 py-8 text-center text-[#787b86]">
                  No open positions
                </td>
              </tr>
            ) : (
              positionRows.map((row) => (
                <tr
                  key={row.symbol}
                  className="border-t border-[#2a2e39]/60 text-[#d1d4dc] hover:bg-white/[0.03]"
                >
                  <td className="px-3 py-2.5">
                    <div className="text-white font-semibold">{row.symbol}</div>
                    <div className="text-[10px] text-[#787b86] uppercase">
                      {row.asset_class}
                    </div>
                  </td>
                  <td className="px-2 py-2.5 text-[#089981]">{row.side || 'LONG'}</td>
                  <td className="px-2 py-2.5 text-right">{fmtQty(row.quantity)}</td>
                  <td className="px-2 py-2.5 text-right">{fmtPrice(row.avg_price)}</td>
                  <td className="px-2 py-2.5 text-right text-white">
                    {fmtPrice(row.last_price)}
                  </td>
                  <td className="px-2 py-2.5 text-right text-[#f23645]/90">
                    {fmtPrice(row.stop_loss)}
                  </td>
                  <td className="px-2 py-2.5 text-right text-[#089981]/90">
                    {fmtPrice(row.take_profit)}
                  </td>
                  <td className={`px-2 py-2.5 text-right ${pnlClass(row.unrealized_pnl)}`}>
                    {row.unrealized_pnl >= 0 ? '+' : ''}
                    {fmtPrice(row.unrealized_pnl)}
                  </td>
                  <td
                    className={`px-2 py-2.5 text-right ${pnlClass(row.unrealized_pnl_pct)}`}
                  >
                    {row.unrealized_pnl_pct >= 0 ? '+' : ''}
                    {row.unrealized_pnl_pct.toFixed(2)}%
                  </td>
                  <td className="px-2 py-2.5 text-right">{fmtPrice(row.trade_value)}</td>
                  <td className="px-2 py-2.5 text-right text-white">
                    {fmtPrice(row.market_value)}
                  </td>
                  <td className="px-3 py-2.5 text-right">
                    <button
                      type="button"
                      onClick={() => onClose(row)}
                      className="px-2 py-1 rounded-lg border border-[#f23645]/40 text-[#f23645] hover:bg-[#f23645]/15 transition-colors"
                    >
                      Close
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
