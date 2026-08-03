'use client'

import { useState } from 'react'
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
  const { balance, positions, trades, executeTrade } = useTradingStore()

  if (!currentTicker || !currentPrice) {
    return (
      <div className="text-[#787b86] text-xs font-mono">
        Select a ticker to enable trading.
      </div>
    )
  }

  const handleTrade = (type: 'BUY' | 'SELL') => {
    if (shares > 0) executeTrade(currentTicker, type, currentPrice, shares, pattern)
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
        <div className="flex gap-2">
          <input
            type="number"
            min="1"
            value={shares}
            onChange={(e) => setShares(Number(e.target.value))}
            className="w-24 bg-[#1e222d] border border-[#2a2e39] rounded px-3 text-white font-mono focus:outline-none"
          />
          <button
            onClick={() => handleTrade('BUY')}
            className="flex-1 bg-[#089981] hover:bg-[#067c69] text-white py-2 rounded font-bold transition-colors"
          >
            BUY
          </button>
          <button
            onClick={() => handleTrade('SELL')}
            className="flex-1 bg-[#f23645] hover:bg-[#c92a38] text-white py-2 rounded font-bold transition-colors"
          >
            SELL
          </button>
        </div>
      </div>

      <div className="h-32 overflow-y-auto border border-[#2a2e39] rounded bg-[#1e222d] p-2">
        <table className="w-full text-xs font-mono text-left">
          <thead className="text-[#787b86] sticky top-0 bg-[#1e222d]">
            <tr>
              <th>ACTION</th>
              <th>TICKER</th>
              <th>PRICE</th>
              <th>SHARES</th>
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
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
