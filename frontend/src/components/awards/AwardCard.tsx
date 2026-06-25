import { Link } from 'react-router-dom'
import { AWARD_LABELS, AWARD_ICONS } from '../../types/awards'
import type { PlayerAward } from '../../types/awards'

interface AwardCardProps {
  award?: PlayerAward
  size?: 'xl' | 'lg' | 'md' | 'sm'
  showMetadata?: boolean
}

const SIZE_CLASSES = {
  xl: 'min-h-[220px] p-6',
  lg: 'min-h-[160px] p-5',
  md: 'min-h-[120px] p-4',
  sm: 'min-h-[80px] p-3',
}

const ICON_SIZES = {
  xl: 'text-5xl mb-4',
  lg: 'text-4xl mb-3',
  md: 'text-3xl mb-2',
  sm: 'text-xl mb-1',
}

const NAME_SIZES = {
  xl: 'text-xl',
  lg: 'text-lg',
  md: 'text-base',
  sm: 'text-sm',
}

export function AwardCard({ award, size = 'md', showMetadata = true }: AwardCardProps) {
  if (!award) {
    return (
      <div className={`bg-white/70 border-2 border-[#1F5F43]/20 flex flex-col items-center justify-center ${SIZE_CLASSES[size]}`}>
        <span className={`${ICON_SIZES[size]} opacity-30 grayscale`}>🏆</span>
        <span className="text-xs text-[#8B5A2B]/40">待定</span>
      </div>
    )
  }

  const label = AWARD_LABELS[award.award_type]
  const icon = AWARD_ICONS[award.award_type]
  const isMVP = award.award_type === 'season_best_player'

  return (
    <div
      className={`relative bg-white/70 border-2 ${
        isMVP ? 'border-[#B9EF3F]/40' : 'border-[#1F5F43]/20'
      } hover:border-[#1F5F43] transition-all overflow-hidden group ${SIZE_CLASSES[size]}`}
    >
      {/* 背景装饰 */}
      <div className="absolute inset-0 opacity-[0.03] bg-[radial-gradient(circle_at_50%_0%,_#B9EF3F,_transparent_70%)]" />
      {isMVP && (
        <div className="absolute top-0 left-0 right-0 h-px bg-[linear-gradient(90deg,transparent,#B9EF3F,transparent)]" />
      )}

      <div className="relative flex flex-col items-center text-center h-full">
        <span className={`${ICON_SIZES[size]} drop-shadow-sm group-hover:scale-110 transition-transform`}>
          {icon}
        </span>

        <h4 className={`font-bold text-[#173126] mb-1 ${size === 'xl' ? 'text-lg' : size === 'lg' ? 'text-base' : 'text-sm'}`}>
          {label}
        </h4>

        {award.player_name ? (
          <Link
            to={`/players/${award.player_id}`}
            className={`${NAME_SIZES[size]} text-[#1F5F43] hover:underline font-medium`}
          >
            {award.player_name}
          </Link>
        ) : (
          <span className="text-sm text-[#466353]">—</span>
        )}

        {showMetadata && award.metadata && (
          <div className="mt-2 text-xs text-[#466353] space-y-0.5">
            {award.metadata.rating !== undefined && (
              <span>评分 {award.metadata.rating.toFixed(1)}</span>
            )}
            {award.metadata.matches !== undefined && (
              <span> · {award.metadata.matches}场</span>
            )}
            {award.metadata.goals !== undefined && award.metadata.goals > 0 && (
              <div>{award.metadata.goals}球{award.metadata.assists ? ` · ${award.metadata.assists}助` : ''}</div>
            )}
            {award.metadata.primary_value !== undefined && (
              <div>
                {award.metadata.primary_value}
                {award.award_type.includes('golden_glove') ? '次零封'
                  : award.award_type.includes('golden_wall') ? '次防守'
                  : ''}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
