import { Link } from 'react-router-dom'
import { Users } from '../../components/ui/pixel-icons'
import type { PlayerAward } from '../../types/awards'

interface PlayerAwardMiniProps {
  award: PlayerAward
  showRank?: boolean
  rank?: number
}

export function PlayerAwardMini({ award, showRank = false, rank }: PlayerAwardMiniProps) {
  const posColors: Record<string, string> = {
    FW: 'text-red-400 border-red-400/30',
    MF: 'text-emerald-400 border-emerald-400/30',
    DF: 'text-blue-400 border-blue-400/30',
    GK: 'text-amber-400 border-amber-400/30',
  }
  const posColor = posColors[award.position || ''] || 'text-[#8B8BA7] border-[#2D2D44]'

  return (
    <div className="flex items-center gap-3 bg-[#0B0D14] border border-[#2D2D44] hover:border-[#0D7377]/40 p-2.5 transition-all group">
      {showRank && rank !== undefined && (
        <div className="w-6 h-6 flex items-center justify-center text-xs font-bold pixel-number bg-[#1E1E2D] text-[#8B8BA7]">
          {rank}
        </div>
      )}

      {award.player_avatar_url ? (
        <div className="w-10 h-10 bg-[#1E1E2D] border border-[#2D2D44] overflow-hidden shrink-0">
          <img src={`/${award.player_avatar_url}`} alt={award.player_name || ''} className="w-full h-full object-cover" />
        </div>
      ) : (
        <div className="w-10 h-10 bg-[#0D4A4D]/20 border border-[#0D7377]/20 flex items-center justify-center shrink-0">
          <Users className="w-5 h-5 text-[#0D7377]" />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <Link
          to={`/players/${award.player_id}`}
          className="block text-sm font-medium text-white hover:text-[#C6F135] truncate transition-colors"
        >
          {award.player_name}
        </Link>
        <div className="flex items-center gap-2 text-xs text-[#8B8BA7]">
          {award.position && (
            <span className={`px-1.5 py-0.5 border ${posColor}`}>
              {award.position}
            </span>
          )}
          {award.metadata?.rating !== undefined && (
            <span>评分 {award.metadata.rating.toFixed(1)}</span>
          )}
        </div>
      </div>

      {award.metadata && (
        <div className="text-right shrink-0">
          {award.metadata.goals !== undefined && award.metadata.goals > 0 && (
            <div className="text-xs text-[#8B8BA7]">{award.metadata.goals}球</div>
          )}
          {award.metadata.matches !== undefined && (
            <div className="text-xs text-[#4B4B6A]">{award.metadata.matches}场</div>
          )}
        </div>
      )}
    </div>
  )
}
