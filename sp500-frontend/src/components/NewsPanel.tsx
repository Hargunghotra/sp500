'use client'

import { useAnalyzerStore } from '@/store/useAnalyzerStore'

export default function NewsPanel() {
  const { analysisData } = useAnalyzerStore()
  const news = analysisData?.news || []

  if (!news.length) {
    return (
      <div className="text-[#787b86] text-xs font-mono p-4">
        Awaiting news data...
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {news.map((item, i) => (
        <a
          key={i}
          href={item.link}
          target="_blank"
          rel="noreferrer"
          className="block p-3 bg-white/[0.03] hover:bg-white/[0.06] border border-white/10 rounded-xl transition-colors group"
        >
          <div className="flex items-start justify-between gap-2">
            <h3 className="text-sm text-[#d1d4dc] group-hover:text-white font-medium line-clamp-2 leading-snug">
              {item.title}
            </h3>
            <span
              className={`text-[10px] font-mono px-1.5 py-0.5 rounded border shrink-0 ${
                item.sentiment === 'BULLISH'
                  ? 'border-[#089981] text-[#089981] bg-[#089981]/10'
                  : item.sentiment === 'BEARISH'
                    ? 'border-[#f23645] text-[#f23645] bg-[#f23645]/10'
                    : 'border-[#787b86] text-[#787b86] bg-[#787b86]/10'
              }`}
            >
              {item.sentiment}
            </span>
          </div>
        </a>
      ))}
    </div>
  )
}
