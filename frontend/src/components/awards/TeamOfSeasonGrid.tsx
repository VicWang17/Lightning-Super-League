import { PlayerAwardMini } from './PlayerAwardMini'
import type { PlayerAward } from '../../types/awards'

interface TeamOfSeasonGridProps {
  team: PlayerAward[]
  title?: string
  emptyText?: string
}

export function TeamOfSeasonGrid({ team, title, emptyText = '暂无最佳阵容数据' }: TeamOfSeasonGridProps) {
  if (team.length === 0) {
    return (
      <div className="text-center py-8 border border-[#1F5F43]/20 bg-white/70">
        <span className="text-2xl opacity-30 grayscale">⭐</span>
        <p className="text-sm text-[#8B5A2B]/40 mt-2">{emptyText}</p>
      </div>
    )
  }

  const byPosition: Record<string, PlayerAward[]> = {
    GK: [], DF: [], MF: [], FW: [],
  }
  team.forEach(a => {
    const pos = a.position || 'UNKNOWN'
    if (!byPosition[pos]) byPosition[pos] = []
    byPosition[pos].push(a)
  })

  const order = ['GK', 'DF', 'MF', 'FW']
  const posLabels: Record<string, string> = {
    GK: '门将', DF: '后卫', MF: '中场', FW: '前锋',
  }
  const posGradients: Record<string, string> = {
    GK: 'from-amber-500/10 to-transparent',
    DF: 'from-blue-500/10 to-transparent',
    MF: 'from-emerald-500/10 to-transparent',
    FW: 'from-red-500/10 to-transparent',
  }

  return (
    <div className="space-y-3">
      {title && (
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold text-[#173126]">{title}</span>
          <span className="text-xs text-[#8B5A2B]/40">({team.length}人)</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {order.map(pos => {
          const players = byPosition[pos] || []
          if (players.length === 0) return null
          return (
            <div key={pos} className={`bg-white/70 border border-[#1F5F43]/20 overflow-hidden`}>
              <div className={`px-3 py-2 bg-[linear-gradient(to_right,${posGradients[pos].replace('from-', '').replace(' to-transparent', '')},transparent)] border-b border-[#1F5F43]/20`}>
                <span className="text-xs font-bold text-[#466353]">
                  {posLabels[pos]} × {players.length}
                </span>
              </div>
              <div className="p-2 space-y-1.5">
                {players.map((award, idx) => (
                  <PlayerAwardMini key={award.id} award={award} showRank rank={idx + 1} />
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
