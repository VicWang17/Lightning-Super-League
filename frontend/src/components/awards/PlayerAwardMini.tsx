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
    FW: 'text-[#FF6F59] border-red-400/30',
    MF: 'text-[#1F5F43] border-emerald-400/30',
    DF: 'text-[#1F5F43] border-[#1F5F43]/30',
    GK: 'text-[#C77A00] border-amber-400/30',
  }
  const posColor = posColors[award.position || ''] || 'text-[#466353] border-[#1F5F43]/20'

  return (
    <div className="flex items-center gap-3 bg-white/70 border border-[#1F5F43]/20 hover:border-[#1F5F43] p-2.5 transition-all group">
      {showRank && rank !== undefined && (
        <div className="w-6 h-6 flex items-center justify-center text-xs font-bold pixel-number bg-[#FFF8DC]/80 text-[#466353]">
          {rank}
        </div>
      )}

      {award.player_avatar_url ? (
        <div className="w-10 h-10 bg-[#FFF8DC]/80 border border-[#1F5F43]/20 overflow-hidden shrink-0">
          <img src={`/${award.player_avatar_url}`} alt={award.player_name || ''} className="w-full h-full object-cover" />
        </div>
      ) : (
        <div className="w-10 h-10 bg-[#B9EF3F]/20 border border-[#1F5F43]/20 flex items-center justify-center shrink-0">
          <Users className="w-5 h-5 text-[#1F5F43]" />
        </div>
      )}

      <div className="min-w-0 flex-1">
        <Link
          to={`/players/${award.player_id}`}
          className="block text-sm font-medium text-[#173126] hover:text-[#1F5F43] truncate transition-colors"
        >
          {award.player_name}
        </Link>
        <div className="flex items-center gap-2 text-xs text-[#466353]">
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
            <div className="text-xs text-[#466353]">{award.metadata.goals}球</div>
          )}
          {award.metadata.matches !== undefined && (
            <div className="text-xs text-[#8B5A2B]/40">{award.metadata.matches}场</div>
          )}
        </div>
      )}
    </div>
  )
}
