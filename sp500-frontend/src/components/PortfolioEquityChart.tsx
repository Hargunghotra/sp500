'use client'

import { useEffect, useState } from 'react'
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { parseJsonResponse } from '@/lib/parseJson'

interface EquityPoint {
  timestamp: string
  equity: number
  cash: number
  positions_value: number
}

interface EquityResponse {
  history: EquityPoint[]
  current: EquityPoint
  error?: string
}

const tooltipStyle = {
  backgroundColor: 'rgba(30, 34, 45, 0.92)',
  border: '1px solid rgba(255,255,255,0.08)',
  borderRadius: 12,
  color: '#d1d4dc',
  fontSize: 12,
  fontFamily: 'ui-monospace, monospace',
  backdropFilter: 'blur(12px)',
}

export default function PortfolioEquityChart() {
  const [history, setHistory] = useState<EquityPoint[]>([])
  const [current, setCurrent] = useState<EquityPoint | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    try {
      const res = await fetch('/api/portfolio/equity?limit=500')
      const data = await parseJsonResponse<EquityResponse>(res)
      if (!res.ok) throw new Error(data.error || 'Failed')
      setHistory(data.history || [])
      setCurrent(data.current || null)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load equity')
    }
  }

  useEffect(() => {
    load()
    const id = setInterval(load, 20000)
    return () => clearInterval(id)
  }, [])

  const chartData = (history.length ? history : current ? [current] : []).map((p) => ({
    ...p,
    label: new Date(p.timestamp).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }),
  }))

  const start = chartData[0]?.equity
  const end = chartData[chartData.length - 1]?.equity
  const up = start != null && end != null ? end >= start : true
  const stroke = up ? '#089981' : '#f23645'
  const fillId = up ? 'eqUp' : 'eqDown'

  if (error) {
    return (
      <div className="h-full flex items-center justify-center text-[#f23645] text-xs font-mono">
        {error}
      </div>
    )
  }

  if (!chartData.length) {
    return (
      <div className="h-full flex items-center justify-center text-[#787b86] text-xs font-mono">
        Awaiting portfolio equity…
      </div>
    )
  }

  return (
    <div className="h-full w-full min-h-[280px] flex flex-col">
      <div className="flex items-end justify-between mb-2 px-1">
        <div>
          <div className="text-[10px] uppercase tracking-wider font-mono text-[#787b86]">
            AI book equity
          </div>
          <div className={`text-2xl font-semibold font-mono ${up ? 'text-[#089981]' : 'text-[#f23645]'}`}>
            ${(current?.equity ?? end ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
        </div>
        <div className="text-[11px] font-mono text-[#787b86] text-right">
          <div>Cash ${(current?.cash ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</div>
          <div>
            Positions $
            {(current?.positions_value ?? 0).toLocaleString(undefined, {
              minimumFractionDigits: 2,
            })}
          </div>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <defs>
              <linearGradient id="eqUp" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#089981" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#089981" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="eqDown" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#f23645" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#f23645" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="rgba(255,255,255,0.06)" strokeDasharray="3 3" vertical={false} />
            <XAxis
              dataKey="label"
              tick={{ fill: '#787b86', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              minTickGap={40}
            />
            <YAxis
              domain={['auto', 'auto']}
              tick={{ fill: '#787b86', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              width={64}
              tickFormatter={(v: number) => `$${Math.round(v).toLocaleString()}`}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value) => {
                const num = typeof value === 'number' ? value : Number(value)
                return [`$${num.toLocaleString(undefined, { minimumFractionDigits: 2 })}`, 'Equity']
              }}
            />
            <Area
              type="monotone"
              dataKey="equity"
              stroke={stroke}
              fill={`url(#${fillId})`}
              strokeWidth={2.5}
              dot={false}
              activeDot={{ r: 4, fill: stroke }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
