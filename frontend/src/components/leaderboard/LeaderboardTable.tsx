import { Link } from 'react-router-dom'
import type { LeaderboardItem } from '../../types/leaderboard'
import { LeaderboardValue } from './LeaderboardValue'

interface LeaderboardTableProps {
  items: LeaderboardItem[]
  valueFormat?: 'int' | 'float1' | 'percent'
  loading?: boolean
}

const RANK_COLORS = [
  'bg-[#FFC247] text-[#173126]',
  'bg-[#B9D3A8] text-[#173126]',
  'bg-[#FF6F59] text-[#173126]',
]

export function LeaderboardTable({ items, valueFormat = 'int', loading }: LeaderboardTableProps) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[1, 2, 3, 4, 5].map(i => (
          <div key={i} className="h-14 bg-[#FFF8DC]/80 animate-pulse" />
        ))}
      </div>
    )
  }

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-[#466353]">暂无数据</p>
      </div>
    )
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full">
        <thead>
          <tr className="text-left text-xs text-[#466353] border-b border-[#1F5F43]/20">
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
            <tr key={item.player_id} className="border-b border-[#1F5F43]/20 hover:bg-[#FFF8DC]/80 transition-colors">
              <td className="py-3 px-4">
                <div className={`w-7 h-7 flex items-center justify-center text-sm font-bold pixel-number ${
                  item.rank <= 3 ? RANK_COLORS[item.rank - 1] : 'bg-[#FFF8DC]/80 text-[#466353]'
                }`}>
                  {item.rank}
                </div>
              </td>
              <td className="py-3 px-4">
                <div className="flex items-center gap-3">
                  {item.avatar_url ? (
                    <div className="w-8 h-8 bg-[#FFF8DC]/80 border border-[#1F5F43]/20 overflow-hidden">
                      <img src={`/${item.avatar_url}`} alt={item.player_name} className="w-full h-full object-cover" />
                    </div>
                  ) : (
                    <div className="w-8 h-8 bg-[#B9EF3F]/20 border border-[#1F5F43]/25 flex items-center justify-center">
                      <span className="text-[10px] text-[#1F5F43]">?</span>
                    </div>
                  )}
                  <Link
                    to={`/players/${item.player_id}`}
                    className="font-medium text-[#173126] hover:text-[#1F5F43] transition-colors"
                  >
                    {item.player_name}
                  </Link>
                </div>
              </td>
              <td className="py-3 px-4">
                <span className="px-2 py-0.5 text-xs bg-[#FFF8DC]/80 border border-[#1F5F43]/20 text-[#466353]">
                  {item.position}
                </span>
              </td>
              <td className="py-3 px-4">
                <Link
                  to={`/teams/${item.team_id}`}
                  className="text-sm text-[#466353] hover:text-[#173126] transition-colors"
                >
                  {item.team_name}
                </Link>
              </td>
              <td className="py-3 px-4 text-center">
                <span className="font-bold pixel-number text-lg text-[#1F5F43]">
                  <LeaderboardValue value={item.value} format={valueFormat} />
                </span>
              </td>
              <td className="py-3 px-4 text-center text-[#466353] text-sm">
                {item.matches > 0 ? `${item.matches}场` : '-'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
