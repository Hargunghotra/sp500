'use client'

import { FormEvent, useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Activity, Search, TrendingDown, TrendingUp } from 'lucide-react'
import AreaChartPlot from '@/components/AreaChartPlot'
import AgentPanel from '@/components/AgentPanel'
import NewsPanel from '@/components/NewsPanel'
import PortfolioEquityChart from '@/components/PortfolioEquityChart'
import SimulationTradingPanel from '@/components/SimulationTradingPanel'
import TradeReportsPanel from '@/components/TradeReportsPanel'
import { useAgentStore } from '@/store/useAgentStore'
import { useAnalyzerStore } from '@/store/useAnalyzerStore'
import { useTradingStore } from '@/store/useTradingStore'

export default function Home() {
  const [ticker, setTicker] = useState('SPY')
  const { analysisData, loading, error, fetchAnalysis } = useAnalyzerStore()
  const { balance, equity, fetchPortfolio } = useTradingStore()
  const { fetchStatus, fetchReports, status } = useAgentStore()

  useEffect(() => {
    fetchAnalysis('SPY')
    fetchPortfolio()
    fetchStatus()
    fetchReports()
  }, [fetchAnalysis, fetchPortfolio, fetchStatus, fetchReports])

  useEffect(() => {
    const id = setInterval(() => {
      fetchStatus()
      fetchReports()
      fetchPortfolio()
    }, 20000)
    return () => clearInterval(id)
  }, [fetchStatus, fetchReports, fetchPortfolio])

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    if (ticker.trim()) fetchAnalysis(ticker.trim().toUpperCase())
  }

  const price = analysisData?.current_price
  const trend = analysisData?.trend
  const isUp = trend === 'UP'
  const bookUp = equity >= 50000

  return (
    <main className="app-shell text-[#d1d4dc]">
      <header className="glass-header sticky top-0 z-20">
        <div className="max-w-[1600px] mx-auto px-4 py-3 flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-[#2962ff]/20 border border-white/10 flex items-center justify-center shadow-[0_0_30px_rgba(41,98,255,0.35)]">
              <Activity className="h-5 w-5 text-[#2962ff]" />
            </div>
            <div>
              <h1 className="text-white font-semibold tracking-tight text-lg leading-none">
                S&amp;P 500 Simulator
              </h1>
              <p className="text-[11px] font-mono text-[#787b86] mt-1">
                Autonomous Gemini desk · glass terminal · $50k paper book
              </p>
            </div>
          </div>

          <form onSubmit={onSubmit} className="flex gap-2 w-full sm:w-auto">
            <div className="relative flex-1 sm:w-56">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-[#787b86]" />
              <input
                value={ticker}
                onChange={(e) => setTicker(e.target.value.toUpperCase())}
                placeholder="RESEARCH TICKER"
                className="w-full glass-input rounded-xl pl-9 pr-3 py-2.5 text-sm font-mono text-white focus:outline-none focus:border-[#2962ff]/60"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2.5 rounded-xl bg-[#2962ff]/90 hover:bg-[#2962ff] disabled:opacity-60 text-white text-sm font-semibold transition-all"
            >
              {loading ? 'Analyzing…' : 'Analyze'}
            </button>
          </form>
        </div>
      </header>

      <div className="max-w-[1600px] mx-auto px-4 py-5 space-y-4">
        {error && (
          <div className="rounded-2xl border border-[#f23645]/40 bg-[#f23645]/10 text-[#f23645] text-sm font-mono px-4 py-3">
            {error}
          </div>
        )}

        <section className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {[
            {
              label: 'Book Equity',
              value: `$${equity.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
              accent: bookUp ? 'text-[#089981]' : 'text-[#f23645]',
            },
            {
              label: 'Cash',
              value: `$${balance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
              accent: 'text-white',
            },
            {
              label: 'Universe',
              value: `S&P ${status?.universe_size || 500}`,
              accent: 'text-[#2962ff]',
            },
            {
              label: 'Research',
              value: analysisData?.ticker ?? '—',
              accent: 'text-white',
            },
            {
              label: 'Spot',
              value: price != null ? `$${price.toFixed(2)}` : '—',
              accent: isUp ? 'text-[#089981]' : 'text-[#f23645]',
              icon: trend ? (
                isUp ? (
                  <TrendingUp className="h-3.5 w-3.5" />
                ) : (
                  <TrendingDown className="h-3.5 w-3.5" />
                )
              ) : null,
            },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.35 }}
              className="glass-panel px-4 py-3"
            >
              <div className="text-[10px] uppercase tracking-wider font-mono text-[#787b86]">
                {stat.label}
              </div>
              <div
                className={`mt-1 text-lg font-semibold font-mono flex items-center gap-1.5 ${stat.accent}`}
              >
                {stat.icon}
                {stat.value}
              </div>
            </motion.div>
          ))}
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
            className="xl:col-span-2 glass-panel p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-sm font-semibold text-white">Portfolio Performance</h2>
              <span className="text-[10px] font-mono text-[#787b86]">
                AI paper book · mark-to-market
              </span>
            </div>
            <div className="h-[420px]">
              <PortfolioEquityChart />
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45, delay: 0.05 }}
            className="glass-panel p-4 flex flex-col min-h-[420px]"
          >
            <h2 className="text-sm font-semibold text-white mb-3">Market News NLP</h2>
            <div className="flex-1 overflow-y-auto pr-1">
              <NewsPanel />
            </div>
          </motion.div>
        </section>

        <section className="grid grid-cols-1 xl:grid-cols-3 gap-4">
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.08 }}
            className="glass-panel p-4"
          >
            <AgentPanel />
          </motion.div>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.1 }}
            className="xl:col-span-2 glass-panel p-4"
          >
            <h2 className="text-sm font-semibold text-white mb-3">AI Trade Reports</h2>
            <TradeReportsPanel />
          </motion.div>
        </section>

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.12 }}
          className="glass-panel p-4"
        >
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-sm font-semibold text-white">
              Research Chart
              {analysisData?.pattern ? (
                <span className="ml-2 text-[11px] font-mono text-[#787b86]">
                  · {analysisData.ticker} · {analysisData.pattern}
                </span>
              ) : null}
            </h2>
            <div className="text-[10px] font-mono text-[#787b86] flex gap-3">
              <span className="text-[#089981]">
                Support {analysisData?.supportLevel?.toFixed(2) ?? '—'}
              </span>
              <span className="text-[#f23645]">
                Resistance {analysisData?.resistanceLevel?.toFixed(2) ?? '—'}
              </span>
            </div>
          </div>
          <div className="h-[320px]">
            <AreaChartPlot
              history={analysisData?.history ?? []}
              volume={analysisData?.volume ?? []}
              supportLevel={analysisData?.supportLevel}
              resistanceLevel={analysisData?.resistanceLevel}
              trend={analysisData?.trend}
            />
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, delay: 0.14 }}
          className="glass-panel p-4"
        >
          <h2 className="text-sm font-semibold text-white mb-4">Paper Trading Desk</h2>
          <SimulationTradingPanel
            currentTicker={analysisData?.ticker}
            currentPrice={analysisData?.current_price}
            pattern={analysisData?.pattern}
          />
        </motion.section>
      </div>
    </main>
  )
}
