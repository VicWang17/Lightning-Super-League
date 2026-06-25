import { AwardCard } from './AwardCard'
import type { PlayerAward } from '../../types/awards'

interface DataKingsRowProps {
  goldenBoot?: PlayerAward
  playmaker?: PlayerAward
  goldenGlove?: PlayerAward
  goldenWall?: PlayerAward
  size?: 'lg' | 'md'
  emptyText?: string
}

export function DataKingsRow({
  goldenBoot,
  playmaker,
  goldenGlove,
  goldenWall,
  size = 'md',
  emptyText = '暂无数据',
}: DataKingsRowProps) {
  const hasAny = goldenBoot || playmaker || goldenGlove || goldenWall

  if (!hasAny) {
    return (
      <div className="text-center py-8 border border-[#1F5F43]/20 bg-white/70">
        <span className="text-2xl opacity-30 grayscale">📊</span>
        <p className="text-sm text-[#8B5A2B]/40 mt-2">{emptyText}</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
      <AwardCard award={goldenBoot} size={size} />
      <AwardCard award={playmaker} size={size} />
      <AwardCard award={goldenGlove} size={size} />
      <AwardCard award={goldenWall} size={size} />
    </div>
  )
}
