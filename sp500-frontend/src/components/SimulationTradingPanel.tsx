'use client'

import { useEffect, useState } from 'react'
import { useTradingStore } from '@/store/useTradingStore'

interface SimulationTradingPanelProps {
  currentTicker?: string
  currentPrice?: number
  pattern?: string
}

export default function SimulationTradingPanel({
  currentTicker,
  currentPrice,
  pattern = 'Unknown',
}: SimulationTradingPanelProps) {
  const [shares, setShares] = useState(10)
  const [busy, setBusy] = useState(false)
  const { balance, positions, trades, error, executeTrade, fetchPortfolio } =
    useTradingStore()

  useEffect(() => {
    fetchPortfolio()
  }, [fetchPortfolio])

  if (!currentTicker || !currentPrice) {
    return (
      <div className="text-[#787b86] text-xs font-mono">
        Select a ticker to enable trading.
      </div>
    )
  }

  const handleTrade = async (type: 'BUY' | 'SELL') => {
    if (shares <= 0 || busy) return
    setBusy(true)
    await executeTrade(currentTicker, type, currentPrice, shares, pattern)
    setBusy(false)
  }

  const ownedShares = positions[currentTicker] || 0

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="space-y-4">
        <div className="flex justify-between text-sm font-mono text-[#d1d4dc]">
          <span>
            Buying Power:{' '}
            <span className="text-white">
              $
              {balance.toLocaleString(undefined, {
                minimumFractionDigits: 2,
              })}
            </span>
          </span>
          <span>
            Position: <span className="text-white">{ownedShares} shares</span>
          </span>
        </div>
        {error && (
          <div className="text-xs font-mono text-[#f23645]">{error}</div>
        )}
        <div className="flex gap-2">
          <input
            type="number"
            min="1"
            value={shares}
            onChange={(e) => setShares(Number(e.target.value))}
            className="w-24 glass-input rounded-xl px-3 text-white font-mono focus:outline-none"
          />
          <button
            onClick={() => handleTrade('BUY')}
            disabled={busy}
            className="flex-1 bg-[#089981]/90 hover:bg-[#089981] disabled:opacity-60 text-white py-2.5 rounded-xl font-bold transition-all"
          >
            BUY
          </button>
          <button
            onClick={() => handleTrade('SELL')}
            disabled={busy}
            className="flex-1 bg-[#f23645]/90 hover:bg-[#f23645] disabled:opacity-60 text-white py-2.5 rounded-xl font-bold transition-all"
          >
            SELL
          </button>
        </div>
      </div>

      <div className="h-32 overflow-y-auto border border-white/10 rounded-xl bg-black/20 p-2 backdrop-blur">
        <table className="w-full text-xs font-mono text-left">
          <thead className="text-[#787b86] sticky top-0 bg-[#131722]/90 backdrop-blur">
            <tr>
              <th>ACTION</th>
              <th>TICKER</th>
              <th>PRICE</th>
              <th>SHARES</th>
              <th>SRC</th>
            </tr>
          </thead>
          <tbody>
            {trades.map((t) => (
              <tr key={t.id} className="border-t border-[#2a2e39]/50 text-[#d1d4dc]">
                <td className={t.type === 'BUY' ? 'text-[#089981]' : 'text-[#f23645]'}>
                  {t.type}
                </td>
                <td>{t.ticker}</td>
                <td>${t.price.toFixed(2)}</td>
                <td>{t.shares}</td>
                <td className="text-[#787b86]">{t.source || 'manual'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
