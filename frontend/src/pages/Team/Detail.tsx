import { useParams, Link } from 'react-router-dom'
import { useEffect, useState } from 'react'
import {
  Users, ChevronLeft, Shield, Target, Zap, Trophy,
  MapPin, Calendar, TrendingUp, ChevronRight
} from '../../components/ui/pixel-icons'
import { Card } from '../../components/ui/Card'
import { getPositionColor, type PlayerListItem } from '../../types/player'
import { api } from '../../api/client'

// Mock team data
const MOCK_TEAM = {
  id: '1',
  name: '东方巨龙',
  short_name: '巨龙',
  logo_url: null,
  stadium: '巨龙体育场',
  city: '上海',
  founded_year: 2020,
  reputation: 1800,
  overall_rating: 72,
  attack: 74,
  midfield: 70,
  defense: 71,
  league_position: 3,
  league_name: '东区超级联赛',
  league_id: '1',
  user: {
    id: '1',
    nickname: '龙傲天',
    level: 15
  },
  stats: {
    matches_played: 11,
    wins: 8,
    draws: 0,
    losses: 3,
    goals_for: 26,
    goals_against: 14,
    points: 24
  },
  finances: {
    balance: 25000000,
    weekly_wages: 125000,
    stadium_capacity: 45000,
    ticket_price: 35
  }
}

function TeamDetail() {
  const { id: _id } = useParams<{ id: string }>()
  const [team, setTeam] = useState(MOCK_TEAM)
  const [players, setPlayers] = useState<PlayerListItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    async function load() {
      try {
        let teamId = _id
        let teamData = MOCK_TEAM

        if (!teamId) {
          // 无 id 时获取当前用户球队
          const myTeamRes = await api.get<{ id: string; name: string; short_name: string; overall_rating: number; current_league_id: string; league_name: string }>('/teams/my-team')
          if (!cancelled && myTeamRes.success && myTeamRes.data) {
            teamId = myTeamRes.data.id
            teamData = { ...MOCK_TEAM, ...myTeamRes.data }
          }
        }

        if (!cancelled && teamId) {
          setTeam(teamData)
          const playersRes = await api.get<{ items: PlayerListItem[], total: number, page: number, page_size: number }>(`/teams/${teamId}/players?page=1&page_size=50`)
          if (!cancelled && playersRes.success) {
            setPlayers(playersRes.data.items || [])
          }
        }
      } catch (err) {
        console.error('加载球队数据失败:', err)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => { cancelled = true }
  }, [_id])

  return (
    <div className="max-w-[1200px]">
      {/* 返回按钮 */}
      <Link
        to="/leagues"
        className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
      >
        <ChevronLeft className="w-4 h-4" />
        返回联赛
      </Link>

      {/* 球队信息头部 */}
      <Card className="mb-6 bg-[#0D4A4D]/30 border-2 border-[#2D2D44] hover:-translate-y-1 hover:shadow-pixel transition-all">
        <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
          <div className="w-24 h-24 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center text-5xl shadow-pixel">
            🐉
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h1 className="text-3xl font-bold text-white">{team.name}</h1>
              <span className="text-lg text-[#8B8BA7]">({team.short_name})</span>
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-[#8B8BA7]">
              <div className="flex items-center gap-1.5">
                <MapPin className="w-4 h-4" />
                {team.city}
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                成立于 {team.founded_year}
              </div>
              <div className="flex items-center gap-1.5">
                <Trophy className="w-4 h-4" />
                声望 {team.reputation}
              </div>
            </div>
            <div className="mt-3">
              <Link
                to={`/leagues/${team.league_id}`}
                className="inline-flex items-center gap-1.5 text-sm text-[#0D7377] hover:text-white transition-colors"
              >
                <Shield className="w-4 h-4" />
                {team.league_name} · 排名第 {team.league_position}
                <ChevronRight className="w-3 h-3" />
              </Link>
            </div>
          </div>
          <div className="flex items-center gap-4">
            <div className="text-center">
              <div className="text-3xl font-bold stat-number pixel-number text-[#0D7377]">{team.overall_rating}</div>
              <div className="text-xs text-[#8B8BA7]">总评</div>
            </div>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧 - 能力值和统计 */}
        <div className="space-y-6">
          {/* 能力值 */}
          <Card hover>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5 text-[#0D7377]" />
              球队能力
            </h3>
            <div className="space-y-4">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Target className="w-4 h-4 text-red-400" />
                    <span className="text-sm text-[#8B8BA7]">进攻</span>
                  </div>
                  <span className="font-bold stat-number pixel-number">{team.attack}</span>
                </div>
                <div className="pixel-progress-track">
                  <div
                    className="pixel-progress-fill bg-red-500"
                    style={{ width: `${team.attack}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Zap className="w-4 h-4 text-[#0D7377]" />
                    <span className="text-sm text-[#8B8BA7]">中场</span>
                  </div>
                  <span className="font-bold stat-number pixel-number">{team.midfield}</span>
                </div>
                <div className="pixel-progress-track">
                  <div
                    className="pixel-progress-fill bg-[#0D7377]"
                    style={{ width: `${team.midfield}%` }}
                  />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm text-[#8B8BA7]">防守</span>
                  </div>
                  <span className="font-bold stat-number pixel-number">{team.defense}</span>
                </div>
                <div className="pixel-progress-track">
                  <div
                    className="pixel-progress-fill bg-emerald-500"
                    style={{ width: `${team.defense}%` }}
                  />
                </div>
              </div>
            </div>
          </Card>

          {/* 赛季统计 */}
          <Card hover>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5 text-[#0D7377]" />
              本赛季统计
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="text-center p-3 bg-[#1E1E2D]">
                <div className="text-2xl font-bold stat-number pixel-number text-white">{team.stats.matches_played}</div>
                <div className="text-xs text-[#8B8BA7]">场次</div>
              </div>
              <div className="text-center p-3 bg-[#1E1E2D]">
                <div className="text-2xl font-bold stat-number pixel-number text-emerald-400">{team.stats.wins}</div>
                <div className="text-xs text-[#8B8BA7]">胜</div>
              </div>
              <div className="text-center p-3 bg-[#1E1E2D]">
                <div className="text-2xl font-bold stat-number pixel-number text-[#8B8BA7]">{team.stats.draws}</div>
                <div className="text-xs text-[#8B8BA7]">平</div>
              </div>
              <div className="text-center p-3 bg-[#1E1E2D]">
                <div className="text-2xl font-bold stat-number pixel-number text-red-400">{team.stats.losses}</div>
                <div className="text-xs text-[#8B8BA7]">负</div>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t-2 border-[#2D2D44]">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">进球/失球</span>
                <span className="font-bold stat-number pixel-number">{team.stats.goals_for} / {team.stats.goals_against}</span>
              </div>
              <div className="flex items-center justify-between mt-2">
                <span className="text-sm text-[#8B8BA7]">积分</span>
                <span className="font-bold stat-number pixel-number text-[#0D7377]">{team.stats.points}</span>
              </div>
            </div>
          </Card>

          {/* 财务信息 */}
          <Card hover>
            <h3 className="text-lg font-semibold mb-4">财务状况</h3>
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">资金余额</span>
                <span className="font-bold stat-number pixel-number text-emerald-400">
                  €{(team.finances.balance / 1000000).toFixed(1)}M
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">周薪支出</span>
                <span className="font-bold stat-number pixel-number text-red-400">
                  €{(team.finances.weekly_wages / 1000).toFixed(0)}K
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">球场容量</span>
                <span className="font-bold stat-number pixel-number">{team.finances.stadium_capacity.toLocaleString()}</span>
              </div>
            </div>
          </Card>
        </div>

        {/* 右侧 - 球员列表 */}
        <div className="lg:col-span-2">
          <Card hover>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold flex items-center gap-2">
                <Users className="w-5 h-5 text-[#0D7377]" />
                球队阵容
              </h3>
              <span className="text-sm text-[#8B8BA7]">{players.length} 名球员</span>
            </div>

            {loading ? (
              <div className="text-center py-8 text-[#8B8BA7]">加载球员中...</div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
                      <th className="py-3 px-2 font-medium">头像</th>
                      <th className="py-3 px-2 font-medium">位置</th>
                      <th className="py-3 px-2 font-medium">姓名</th>
                      <th className="py-3 px-2 font-medium text-center">年龄</th>
                      <th className="py-3 px-2 font-medium text-center">潜力</th>
                      <th className="py-3 px-2 font-medium text-center">能力</th>
                    </tr>
                  </thead>
                  <tbody>
                    {players.map(player => (
                      <tr key={player.id} className="border-b border-[#2D2D44] hover:bg-[#1E1E2D]/50 transition-colors">
                        <td className="py-3 px-2">
                          <div className="w-8 h-8 bg-[#1E1E2D] border border-[#2D2D44] overflow-hidden">
                            {player.avatar_url ? (
                              <img src={`/${player.avatar_url}`} alt={player.name} className="w-full h-full object-cover" />
                            ) : (
                              <span className="text-xs flex items-center justify-center h-full">👤</span>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-2">
                          <span className={`inline-flex items-center justify-center w-8 h-8 text-xs font-bold ${getPositionColor(player.position)}`}>
                            {player.position}
                          </span>
                        </td>
                        <td className="py-3 px-2">
                          <Link
                            to={`/players/${player.id}`}
                            className="font-medium text-white hover:text-[#0D7377] transition-colors"
                          >
                            {player.name}
                          </Link>
                        </td>
                        <td className="py-3 px-2 text-center stat-number text-[#8B8BA7]">{player.age}</td>
                        <td className="py-3 px-2 text-center">
                          <span className={`text-xs font-bold ${
                            player.potential_letter === 'S' ? 'text-amber-400' :
                            player.potential_letter === 'A' ? 'text-emerald-400' :
                            player.potential_letter === 'B' ? 'text-[#0D7377]' :
                            'text-[#8B8BA7]'
                          }`}>
                            {player.potential_letter}
                          </span>
                        </td>
                        <td className="py-3 px-2 text-center">
                          <span className={`font-bold stat-number pixel-number ${
                            player.ovr >= 75 ? 'text-emerald-400' :
                            player.ovr >= 70 ? 'text-[#0D7377]' :
                            'text-[#8B8BA7]'
                          }`}>
                            {player.ovr}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}

export default TeamDetail
