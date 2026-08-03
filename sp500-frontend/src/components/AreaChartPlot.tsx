'use client'

import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Bar,
} from 'recharts'
import type { HistoryPoint, VolumePoint } from '@/store/useAnalyzerStore'

interface AreaChartPlotProps {
  history: HistoryPoint[]
  volume?: VolumePoint[]
  supportLevel?: number
  resistanceLevel?: number
  trend?: 'UP' | 'DOWN'
}

const tooltipStyle = {
  backgroundColor: '#1e222d',
  border: '1px solid #2a2e39',
  borderRadius: 8,
  color: '#d1d4dc',
  fontSize: 12,
  fontFamily: 'ui-monospace, monospace',
}

export default function AreaChartPlot({
  history,
  volume = [],
  supportLevel,
  resistanceLevel,
  trend = 'UP',
}: AreaChartPlotProps) {
  if (!history.length) {
    return (
      <div className="h-full flex items-center justify-center text-[#787b86] text-xs font-mono">
        Awaiting price history...
      </div>
    )
  }

  const volumeByDate = new Map(volume.map((v) => [v.date, v.volume]))
  const chartData = history.map((point) => ({
    ...point,
    volume: volumeByDate.get(point.date) ?? 0,
  }))

  const stroke = trend === 'UP' ? '#089981' : '#f23645'
  const fillId = trend === 'UP' ? 'tvFillUp' : 'tvFillDown'

  return (
    <div className="h-full w-full min-h-[280px]">
      <ResponsiveContainer width="100%" height="72%">
        <ComposedChart data={chartData} margin={{ top: 10, right: 12, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="tvFillUp" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#089981" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#089981" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="tvFillDown" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#f23645" stopOpacity={0.35} />
              <stop offset="100%" stopColor="#f23645" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid stroke="#2a2e39" strokeDasharray="3 3" vertical={false} />
          <XAxis
            dataKey="date"
            tick={{ fill: '#787b86', fontSize: 10, fontFamily: 'ui-monospace, monospace' }}
            axisLine={{ stroke: '#2a2e39' }}
            tickLine={false}
            minTickGap={40}
          />
          <YAxis
            domain={['auto', 'auto']}
            tick={{ fill: '#787b86', fontSize: 10, fontFamily: 'ui-monospace, monospace' }}
            axisLine={false}
            tickLine={false}
            width={56}
            tickFormatter={(v: number) => v.toFixed(0)}
          />
          <Tooltip
            contentStyle={tooltipStyle}
            labelStyle={{ color: '#787b86' }}
            formatter={(value, name) => {
              const num = typeof value === 'number' ? value : Number(value)
              if (name === 'price') return [`$${num.toFixed(2)}`, 'Price']
              if (name === 'sma50') return [`$${num.toFixed(2)}`, 'SMA 50']
              return [value, name]
            }}
          />
          {typeof supportLevel === 'number' && (
            <ReferenceLine
              y={supportLevel}
              stroke="#089981"
              strokeDasharray="4 4"
              label={{
                value: 'Support',
                fill: '#089981',
                fontSize: 10,
                position: 'insideTopLeft',
              }}
            />
          )}
          {typeof resistanceLevel === 'number' && (
            <ReferenceLine
              y={resistanceLevel}
              stroke="#f23645"
              strokeDasharray="4 4"
              label={{
                value: 'Resistance',
                fill: '#f23645',
                fontSize: 10,
                position: 'insideBottomLeft',
              }}
            />
          )}
          <Area
            type="monotone"
            dataKey="price"
            stroke={stroke}
            fill={`url(#${fillId})`}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 3, fill: stroke }}
          />
          <Line
            type="monotone"
            dataKey="sma50"
            stroke="#2962ff"
            strokeWidth={1.5}
            dot={false}
            connectNulls
          />
        </ComposedChart>
      </ResponsiveContainer>

      <ResponsiveContainer width="100%" height="28%">
        <ComposedChart data={chartData} margin={{ top: 4, right: 12, left: 0, bottom: 0 }}>
          <CartesianGrid stroke="#2a2e39" strokeDasharray="3 3" vertical={false} />
          <XAxis dataKey="date" hide />
          <YAxis
            tick={{ fill: '#787b86', fontSize: 9, fontFamily: 'ui-monospace, monospace' }}
            axisLine={false}
            tickLine={false}
            width={56}
            tickFormatter={(v: number) =>
              v >= 1_000_000 ? `${(v / 1_000_000).toFixed(1)}M` : `${(v / 1000).toFixed(0)}K`
            }
          />
          <Tooltip
            contentStyle={tooltipStyle}
            formatter={(value) => {
              const num = typeof value === 'number' ? value : Number(value)
              return [num.toLocaleString(), 'Volume']
            }}
          />
          <Bar dataKey="volume" fill="#363a45" radius={[1, 1, 0, 0]} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  )
}
