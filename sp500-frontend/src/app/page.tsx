'use client'

import { FormEvent, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Activity, Search, TrendingDown, TrendingUp } from 'lucide-react'
import AreaChartPlot from '@/components/AreaChartPlot'
import NewsPanel from '@/components/NewsPanel'
import SimulationTradingPanel from '@/components/SimulationTradingPanel'
import { useAnalyzerStore } from '@/store/useAnalyzerStore'

export default function Home() {
  const [ticker, setTicker] = useState('SPY')
  const { analysisData, loading, error, fetchAnalysis } = useAnalyzerStore()

  useEffect(() => {
    fetchAnalysis('SPY')
  }, [fetchAnalysis])

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (ticker.trim()) fetchAnalysis(ticker.trim().toUpperCase())
  }

  const price = analysisData?.current_price
  const trend = analysisData?.trend
  const isUp = trend === 'UP'

  return (
    <main className="min-h-screen bg-[#131722] text-[#d1d4dc]">
      <header className="border-b border-[#2a2e39] bg-[#131722]/95 backdrop-blur sticky top-0 z-20">
        <div className="max-w-[1600px] mx-auto px-4 py-3 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-[#2962ff]/15 border border-[#2962ff]/40 flex items-center justify-center">
              <Activity className="h-5 w-5 text-[#2962ff]" />
            </div>
            <div>
              <h1 className="text-white font-semibold tracking-tight text-lg leading-none">
                S&amp;P 500 Simulator
              </h1>
              <p className="text-[11px] font-mono text-[#787b86] mt-1">
                TradingView theme · paper trading · live Yahoo data
              </p>
            </div>
          </div>

          <form onSubmit={onSubmit} className="flex gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-56">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#787b86]" />
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="TICKER"
                className="w-full bg-[#1e222d] border border-[#2a2e39] rounded-lg pl-9 pr-3 py-2 text-sm font-mono text-white focus:outline-none focus:border-[#2962ff]"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 rounded-lg bg-[#2962ff] hover:bg-[#1e53e5] disabled:opacity-60 text-white text-sm font-semibold transition-colors"
            >
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </form>
        </div>
      </header>

      <div className="max-w-[1600px] mx-auto px-4 py-4 space-y-4">
        {error && (
          <div className="rounded-lg border border-[#f23645]/40 bg-[#f23645]/10 text-[#f23645] text-sm font-mono px-4 py-3">
            {error}
          </div>
        )}

        <section className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            {
              label: 'Ticker',
              value: analysisData?.ticker ?? '—',
              accent: 'text-white',
            },
            {
              label: 'Price',
              value: price != null ? `$${price.toFixed(2)}` : '—',
              accent: isUp ? 'text-[#089981]' : 'text-[#f23645]',
            },
            {
              label: 'Trend',
              value: trend ?? '—',
              accent: isUp ? 'text-[#089981]' : 'text-[#f23645]',
              icon: trend ? (
                isUp ? (
                  <TrendingUp className="h-3.5 w-3.5" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5" />
                )
              ) : null,
            },
            {
              label: 'Score',
              value: analysisData?.score != null ? `${analysisData.score}/10` : '—',
              accent: 'text-[#2962ff]',
            },
            {
              label: 'Sentiment',
              value: analysisData?.sentiment ?? '—',
              accent:
                analysisData?.sentiment === 'BULLISH'
                  ? 'text-[#089981]'
                  : analysisData?.sentiment === 'BEARISH'
                    ? 'text-[#f23645]'
                    : 'text-[#787b86]',
            },
          ].map((stat) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="rounded-xl border border-[#2a2e39] bg-[#1e222d] px-4 py-3"
            >
              <div className="text-[10px] uppercase tracking-wider font-mono text-[#787b86]">
                {stat.label}
              </div>
              <div className={`mt-1 text-lg font-semibold font-mono flex items-center gap-1.5 ${stat.accent}`}>
                {stat.icon}
                {stat.value}
              </div>
            </motion.div>
          ))}
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <div className="xl:col-span-2 rounded-xl border border-[#2a2e39] bg-[#1e222d] p-4">
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">
                Price Action
                {analysisData?.pattern ? (
                  <span className="ml-2 text-[11px] font-mono text-[#787b86]">
                    · {analysisData.pattern}
                  </span>
                ) : null}
              </h2>
              <div className="text-[10px] font-mono text-[#787b86] flex gap-3">
                <span className="text-[#089981]">Support {analysisData?.supportLevel?.toFixed(2) ?? '—'}</span>
                <span className="text-[#f23645]">
                  Resistance {analysisData?.resistanceLevel?.toFixed(2) ?? '—'}
                </span>
              </div>
            </div>
            <div className="h-[420px]">
              <AreaChartPlot
                history={analysisData?.history ?? []}
                volume={analysisData?.volume ?? []}
                supportLevel={analysisData?.supportLevel}
                resistanceLevel={analysisData?.resistanceLevel}
                trend={analysisData?.trend}
              />
            </div>
          </div>

          <div className="rounded-xl border border-[#2a2e39] bg-[#1e222d] p-4 flex flex-col min-h-[420px]">
            <h2 className="text-sm font-semibold text-white mb-3">Market News NLP</h2>
            <div className="flex-1 overflow-y-auto pr-1">
              <NewsPanel />
            </div>
          </div>
        </section>

        <section className="rounded-xl border border-[#2a2e39] bg-[#1e222d] p-4">
          <h2 className="text-sm font-semibold text-white mb-4">Paper Trading Desk</h2>
          <SimulationTradingPanel
            currentTicker={analysisData?.ticker}
            currentPrice={analysisData?.current_price}
            pattern={analysisData?.pattern}
          />
        </section>
      </div>
    </main>
  )
}
