import type { LeaderboardType } from '../../types/leaderboard'

export interface LeaderboardOption {
  type: LeaderboardType
  label: string
  format: 'int' | 'float1' | 'percent'
}

export const LEAGUE_LEADERBOARDS: LeaderboardOption[] = [
  { type: 'goals', label: '射手榜', format: 'int' },
  { type: 'assists', label: '助攻榜', format: 'int' },
  { type: 'clean_sheets', label: '零封榜', format: 'int' },
  { type: 'saves', label: '扑救榜', format: 'int' },
  { type: 'average_rating', label: '场均评分', format: 'float1' },
  { type: 'tackles', label: '抢断榜', format: 'int' },
  { type: 'interceptions', label: '拦截榜', format: 'int' },
  { type: 'clearances', label: '解围榜', format: 'int' },
  { type: 'blocks', label: '封堵榜', format: 'int' },
  { type: 'shots', label: '射门榜', format: 'int' },
  { type: 'shots_on_target', label: '射正榜', format: 'int' },
  { type: 'shot_accuracy', label: '射正率', format: 'percent' },
  { type: 'key_passes', label: '关键传球', format: 'int' },
  { type: 'passes', label: '传球榜', format: 'int' },
  { type: 'pass_accuracy', label: '传球成功率', format: 'percent' },
  { type: 'crosses', label: '传中榜', format: 'int' },
  { type: 'cross_accuracy', label: '传中成功率', format: 'percent' },
  { type: 'dribbles', label: '盘带榜', format: 'int' },
  { type: 'dribble_accuracy', label: '盘带成功率', format: 'percent' },
  { type: 'tackle_accuracy', label: '抢断成功率', format: 'percent' },
  { type: 'header_accuracy', label: '头球成功率', format: 'percent' },
  { type: 'yellow_cards', label: '黄牌榜', format: 'int' },
  { type: 'red_cards', label: '红牌榜', format: 'int' },
  { type: 'fouls', label: '犯规榜', format: 'int' },
  { type: 'offsides', label: '越位榜', format: 'int' },
  { type: 'touches', label: '触球榜', format: 'int' },
  { type: 'free_kick_goals', label: '任意球进球', format: 'int' },
  { type: 'penalty_goals', label: '点球进球', format: 'int' },
  { type: 'minutes_played', label: '出场时间', format: 'int' },
  { type: 'matches_played', label: '出场榜', format: 'int' },
  { type: 'goals_per_game', label: '场均进球', format: 'float1' },
  { type: 'assists_per_game', label: '场均助攻', format: 'float1' },
]

export function getLeaderboardFormat(type: LeaderboardType): 'int' | 'float1' | 'percent' {
  return LEAGUE_LEADERBOARDS.find(lb => lb.type === type)?.format ?? 'int'
}

interface LeaderboardSidebarProps {
  activeType: LeaderboardType
  onChange: (type: LeaderboardType) => void
}

export function LeaderboardSidebar({ activeType, onChange }: LeaderboardSidebarProps) {
  return (
    <div className="flex flex-col gap-1 max-h-[600px] overflow-y-auto pr-1 custom-scrollbar">
      {LEAGUE_LEADERBOARDS.map((lb) => (
        <button
          key={lb.type}
          onClick={() => onChange(lb.type)}
          className={`text-left px-3 py-2 text-sm rounded-none transition-all ${
            activeType === lb.type
              ? 'bg-[#B9EF3F] text-[#173126] font-bold'
              : 'text-[#466353] hover:text-[#173126] hover:bg-[#FFF8DC]/80'
          }`}
        >
          {lb.label}
        </button>
      ))}
    </div>
  )
}
