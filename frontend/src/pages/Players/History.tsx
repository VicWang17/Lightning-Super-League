import { useParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Card } from '../../components/ui/Card'
import { PlayerTabs } from '../../components/players/PlayerTabs'
import { api } from '../../api/client'

interface SeasonHistory {
  season_number: number
  team_name: string
  team_id: string
  matches_played: number
  minutes_played: number
  goals: number
  assists: number
  yellow_cards: number
  red_cards: number
  clean_sheets: number
  average_rating: number
  competition_breakdown: Array<{
    competition: string
    matches_played: number
    goals: number
    assists: number
    minutes_played: number
    average_rating: number
  }>
}

interface CareerSummary {
  total_seasons: number
  total_matches: number
  total_goals: number
  total_assists: number
  total_minutes: number
  total_yellow_cards: number
  total_red_cards: number
  overall_average_rating: number
  best_season: {
    season_number: number
    goals: number
    assists: number
    average_rating: number
  } | null
}

interface Milestone {
  milestone_type: string
  season_number: number
  match_date?: string
  description: string
  fixture_id?: string
}

interface PlayerHistoryData {
  seasons: SeasonHistory[]
  summary: CareerSummary
  milestones: Milestone[]
}

function PlayerHistory() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<PlayerHistoryData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.get<PlayerHistoryData>(`/players/${id}/history`)
      .then(res => {
        if (res.success) {
          setData(res.data)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <div className="max-w-[1200px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  if (!data) {
    return <div className="max-w-[1200px] p-8 text-center text-red-400">数据加载失败</div>
  }

  const { seasons, summary, milestones } = data

  return (
    <div className="max-w-[1200px]">
      {/* 返回按钮 */}
      <Link
        to={`/players/${id}`}
        className="text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
      >
        返回球员档案
      </Link>

      {/* Tabs */}
      <PlayerTabs playerId={id!} />

      {/* 生涯总计 + 最佳赛季 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        <Card className="lg:col-span-2">
          <h3 className="text-lg font-semibold mb-4">
            生涯总计
          </h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-[#1E1E2D]">
              <div className="text-2xl font-bold stat-number pixel-number text-white">{summary.total_seasons}</div>
              <div className="text-xs text-[#8B8BA7] mt-1">赛季</div>
            </div>
            <div className="text-center p-4 bg-[#1E1E2D]">
              <div className="text-2xl font-bold stat-number pixel-number text-white">{summary.total_matches}</div>
              <div className="text-xs text-[#8B8BA7] mt-1">出场</div>
            </div>
            <div className="text-center p-4 bg-[#1E1E2D]">
              <div className="text-2xl font-bold stat-number pixel-number text-emerald-400">{summary.total_goals}</div>
              <div className="text-xs text-[#8B8BA7] mt-1">进球</div>
            </div>
            <div className="text-center p-4 bg-[#1E1E2D]">
              <div className="text-2xl font-bold stat-number pixel-number text-[#0D7377]">{summary.total_assists}</div>
              <div className="text-xs text-[#8B8BA7] mt-1">助攻</div>
            </div>
            <div className="text-center p-4 bg-[#1E1E2D]">
              <div className="text-2xl font-bold stat-number pixel-number text-amber-400">{summary.overall_average_rating}</div>
              <div className="text-xs text-[#8B8BA7] mt-1">场均评分</div>
            </div>
            <div className="text-center p-4 bg-[#1E1E2D]">
              <div className="text-2xl font-bold stat-number pixel-number text-white">{summary.total_minutes}</div>
              <div className="text-xs text-[#8B8BA7] mt-1">出场时间</div>
            </div>
            <div className="text-center p-4 bg-[#1E1E2D]">
              <div className="text-2xl font-bold stat-number pixel-number text-yellow-400">{summary.total_yellow_cards}</div>
              <div className="text-xs text-[#8B8BA7] mt-1">黄牌</div>
            </div>
            <div className="text-center p-4 bg-[#1E1E2D]">
              <div className="text-2xl font-bold stat-number pixel-number text-red-400">{summary.total_red_cards}</div>
              <div className="text-xs text-[#8B8BA7] mt-1">红牌</div>
            </div>
          </div>
        </Card>

        <Card>
          <h3 className="text-lg font-semibold mb-4">
            最佳赛季
          </h3>
          {summary.best_season ? (
            <div className="space-y-4">
              <div className="text-center p-6 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30">
                <p className="text-3xl font-bold stat-number pixel-number text-[#C6F135]">
                  第 {summary.best_season.season_number} 赛季
                </p>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3 bg-[#1E1E2D]">
                  <div className="text-xl font-bold stat-number pixel-number text-emerald-400">{summary.best_season.goals}</div>
                  <div className="text-xs text-[#8B8BA7] mt-1">进球</div>
                </div>
                <div className="text-center p-3 bg-[#1E1E2D]">
                  <div className="text-xl font-bold stat-number pixel-number text-[#0D7377]">{summary.best_season.assists}</div>
                  <div className="text-xs text-[#8B8BA7] mt-1">助攻</div>
                </div>
                <div className="text-center p-3 bg-[#1E1E2D]">
                  <div className="text-xl font-bold stat-number pixel-number text-amber-400">{summary.best_season.average_rating}</div>
                  <div className="text-xs text-[#8B8BA7] mt-1">评分</div>
                </div>
              </div>
            </div>
          ) : (
            <p className="text-[#8B8BA7] text-center py-8">暂无数据</p>
          )}
        </Card>
      </div>

      {/* 赛季表现表格 */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold mb-4">
          赛季表现
        </h3>
        {seasons.length === 0 ? (
          <p className="text-[#8B8BA7] text-center py-8">暂无赛季数据</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-[#2D2D44] text-[#8B8BA7]">
                  <th className="text-left py-3 px-2">赛季</th>
                  <th className="text-left py-3 px-2">球队</th>
                  <th className="text-center py-3 px-2">出场</th>
                  <th className="text-center py-3 px-2">进球</th>
                  <th className="text-center py-3 px-2">助攻</th>
                  <th className="text-center py-3 px-2">评分</th>
                  <th className="text-center py-3 px-2">黄牌</th>
                  <th className="text-center py-3 px-2">红牌</th>
                  <th className="text-center py-3 px-2">零封</th>
                </tr>
              </thead>
              <tbody>
                {seasons.map((season) => (
                  <tr
                    key={season.season_number}
                    className="border-b border-[#2D2D44]/50 hover:bg-[#1E1E2D]/50 transition-colors"
                  >
                    <td className="py-3 px-2 font-medium">第 {season.season_number} 赛季</td>
                    <td className="py-3 px-2">
                      <Link
                        to={`/teams/${season.team_id}`}
                        className="text-[#0D7377] hover:text-[#C6F135] transition-colors"
                      >
                        {season.team_name}
                      </Link>
                    </td>
                    <td className="py-3 px-2 text-center">{season.matches_played}</td>
                    <td className="py-3 px-2 text-center text-emerald-400 font-bold">{season.goals}</td>
                    <td className="py-3 px-2 text-center text-[#0D7377] font-bold">{season.assists}</td>
                    <td className="py-3 px-2 text-center text-amber-400 font-bold">{season.average_rating}</td>
                    <td className="py-3 px-2 text-center text-yellow-400">{season.yellow_cards}</td>
                    <td className="py-3 px-2 text-center text-red-400">{season.red_cards}</td>
                    <td className="py-3 px-2 text-center">{season.clean_sheets}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* 生涯里程碑 */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">
          生涯里程碑
        </h3>
        {milestones.length === 0 ? (
          <p className="text-[#8B8BA7] text-center py-8">暂无里程碑</p>
        ) : (
          <div className="space-y-3">
            {milestones.map((m, idx) => (
              <div
                key={idx}
                className="flex items-center gap-4 p-3 bg-[#1E1E2D] border-l-4 border-[#C6F135]"
              >
                <div className="w-2 h-2 bg-[#C6F135]" />
                <div className="flex-1">
                  <p className="text-sm text-white">{m.description}</p>
                  <p className="text-xs text-[#4B4B6A] mt-0.5">第 {m.season_number} 赛季</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

export default PlayerHistory
