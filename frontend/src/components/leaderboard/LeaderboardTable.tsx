import { Link } from 'react-router-dom'
import type { LeaderboardItem } from '../../types/leaderboard'
import { LeaderboardValue } from './LeaderboardValue'

interface LeaderboardTableProps {
  items: LeaderboardItem[]
  valueFormat?: 'int' | 'float1' | 'percent'
  loading?: boolean
}

const RANK_COLORS = [
  'bg-amber-500 text-black',
  'bg-slate-300 text-black',
  'bg-orange-400 text-black',
]

export function LeaderboardTable({ items, valueFormat = 'int', loading }: LeaderboardTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-14 bg-[#1E1E2D] animate-pulse" />
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-[#8B8BA7]">暂无数据</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
            <th className="py-2 px-4 font-medium">排名</th>
            <th className="py-2 px-4 font-medium">球员</th>
            <th className="py-2 px-4 font-medium">位置</th>
            <th className="py-2 px-4 font-medium">球队</th>
            <th className="py-2 px-4 font-medium text-center">数据</th>
            <th className="py-2 px-4 font-medium text-center">场次</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.player_id} className="border-b border-[#2D2D44] hover:bg-[#1E1E2D]/50 transition-colors">
              <td className="py-3 px-4">
                <div className={`w-7 h-7 flex items-center justify-center text-sm font-bold pixel-number ${
                  item.rank <= 3 ? RANK_COLORS[item.rank - 1] : 'bg-[#1E1E2D] text-[#8B8BA7]'
                }`}>
                  {item.rank}
                </div>
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-3">
                  {item.avatar_url ? (
                    <div className="w-8 h-8 bg-[#1E1E2D] border border-[#2D2D44] overflow-hidden">
                      <img src={`/${item.avatar_url}`} alt={item.player_name} className="w-full h-full object-cover" />
                    </div>
                  ) : (
                    <div className="w-8 h-8 bg-[#0D4A4D]/30 border border-[#0D7377]/30 flex items-center justify-center">
                      <span className="text-[10px] text-[#0D7377]">?</span>
                    </div>
                  )}
                  <Link
                    to={`/players/${item.player_id}`}
                    className="font-medium text-white hover:text-[#C6F135] transition-colors"
                  >
                    {item.player_name}
                  </Link>
                </div>
              </td>
              <td className="py-3 px-4">
                <span className="px-2 py-0.5 text-xs bg-[#1E1E2D] border border-[#2D2D44] text-[#8B8BA7]">
                  {item.position}
                </span>
              </td>
              <td className="py-3 px-4">
                <Link
                  to={`/teams/${item.team_id}`}
                  className="text-sm text-[#8B8BA7] hover:text-white transition-colors"
                >
                  {item.team_name}
                </Link>
              </td>
              <td className="py-3 px-4 text-center">
                <span className="font-bold pixel-number text-lg text-[#C6F135]">
                  <LeaderboardValue value={item.value} format={valueFormat} />
                </span>
              </td>
              <td className="py-3 px-4 text-center text-[#8B8BA7] text-sm">
                {item.matches > 0 ? `${item.matches}场` : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
