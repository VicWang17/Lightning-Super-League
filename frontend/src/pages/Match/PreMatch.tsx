import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Sword,
  Shield,
  Target,
  Clock,
  ChevronRight
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import { Card } from '../../components/ui/Card'

interface MatchPayload {
  id: string
  season_day: number
  round_number: number
  home_team_id: string
  away_team_id: string
  home_team_name?: string
  away_team_name?: string
  home_score?: number
  away_score?: number
  status: string
  scheduled_at: string
  fixture_type: string
}

interface PlayerSetup {
  player_id: string
  name: string
  position: string
}

interface LineupsPayload {
  home_team_name?: string
  away_team_name?: string
  home_lineup: PlayerSetup[]
  away_lineup: PlayerSetup[]
  home_formation: string
  away_formation: string
}

export default function PreMatch() {
  const [match, setMatch] = useState<MatchPayload | null>(null)
  const [lineups, setLineups] = useState<LineupsPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function fetch() {
      try {
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) {
          setError('未找到球队')
          setLoading(false)
          return
        }
        const teamId = teamRes.data.id

        // 查找最近的未开始比赛
        const matchesRes = await api.get<{
          items: MatchPayload[]
        }>(`/matches?team_id=${teamId}&status=scheduled&page_size=1`)
        if (!matchesRes.success || !matchesRes.data?.items?.length) {
          setError('暂无 upcoming 比赛')
          setLoading(false)
          return
        }
        const nextMatch = matchesRes.data.items[0]

        const [matchRes, lineupRes] = await Promise.all([
          api.get<MatchPayload>(`/matches/${nextMatch.id}`),
          api.get<LineupsPayload>(`/matches/${nextMatch.id}/lineups`),
        ])

        if (!cancelled) {
          if (matchRes.success) setMatch(matchRes.data)
          if (lineupRes.success) setLineups(lineupRes.data)
        }
      } catch {
        if (!cancelled) setError('加载失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetch()
    return () => { cancelled = true }
  }, [])

  if (loading) {
    return <div className="max-w-[1200px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  if (error || !match) {
    return (
      <div className="max-w-[1200px] p-8 text-center">
        <p className="text-[#8B8BA7]">{error || '暂无 upcoming 比赛'}</p>
        <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white mt-4 inline-block">
          查看赛程 →
        </Link>
      </div>
    )
  }

  const homeName = match.home_team_name || lineups?.home_team_name || match.home_team_id
  const awayName = match.away_team_name || lineups?.away_team_name || match.away_team_id

  return (
    <div className="space-y-6 max-w-[1200px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">赛前准备</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">下一场比赛情报</p>
        </div>
        <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white transition-colors">
          返回赛程 →
        </Link>
      </div>

      <Card className="bg-[#0D4A4D]/20 border-[#0D7377]/30">
        <div className="flex items-center justify-center gap-8 py-6">
          <div className="text-center">
            <div className="w-20 h-20 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center mx-auto mb-3 shadow-pixel-green">
              <span className="text-3xl">🏠</span>
            </div>
            <h2 className="text-xl font-bold">{homeName}</h2>
            <p className="text-sm text-[#8B8BA7]">{lineups?.home_formation || '-'} · 主队</p>
          </div>

          <div className="text-center px-6">
            <p className="text-4xl font-bold pixel-number text-[#0D7377]">VS</p>
            <div className="flex items-center gap-2 mt-2 text-xs text-[#8B8BA7]">
              <Clock className="w-3 h-3" />
              <span>第 {match.season_day} 天</span>
            </div>
            <span className="inline-block mt-2 px-3 py-1 bg-[#0D7377]/20 text-[#0D7377] text-xs border border-[#0D7377]/30">
              {match.fixture_type === 'league' ? `联赛第${match.round_number}轮` : match.fixture_type}
            </span>
          </div>

          <div className="text-center">
            <div className="w-20 h-20 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-3">
              <span className="text-3xl">✈</span>
            </div>
            <h2 className="text-xl font-bold">{awayName}</h2>
            <p className="text-sm text-[#8B8BA7]">{lineups?.away_formation || '-'} · 客队</p>
          </div>
        </div>
      </Card>

      {lineups && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Sword className="w-4 h-4 text-[#0D7377]" />
              主队阵容
            </h3>
            <div className="space-y-2">
              {lineups.home_lineup.map(p => (
                <div key={p.player_id} className="flex items-center justify-between text-sm border-b border-[#2D2D44]/50 pb-2">
                  <span className="text-white">{p.name}</span>
                  <span className="text-[#8B8BA7]">{p.position}</span>
                </div>
              ))}
            </div>
          </Card>
          <Card>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Shield className="w-4 h-4 text-[#0D7377]" />
              客队阵容
            </h3>
            <div className="space-y-2">
              {lineups.away_lineup.map(p => (
                <div key={p.player_id} className="flex items-center justify-between text-sm border-b border-[#2D2D44]/50 pb-2">
                  <span className="text-white">{p.name}</span>
                  <span className="text-[#8B8BA7]">{p.position}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Link to="/team/tactics" className="flex items-center gap-3 p-4 bg-[#0A0A0F] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all hover:-translate-x-0.5 hover:-translate-y-0.5">
          <Target className="w-5 h-5 text-[#0D7377]" />
          <div>
            <p className="text-sm font-medium">调整阵型</p>
            <p className="text-xs text-[#4B4B6A]">当前: {lineups?.home_formation || '-'}</p>
          </div>
          <ChevronRight className="w-4 h-4 text-[#4B4B6A] ml-auto" />
        </Link>
        <Link to="/team/players" className="flex items-center gap-3 p-4 bg-[#0A0A0F] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all hover:-translate-x-0.5 hover:-translate-y-0.5">
          <Shield className="w-5 h-5 text-[#0D7377]" />
          <div>
            <p className="text-sm font-medium">更换首发</p>
            <p className="text-xs text-[#4B4B6A]">调整出场球员</p>
          </div>
          <ChevronRight className="w-4 h-4 text-[#4B4B6A] ml-auto" />
        </Link>
        <Link to="/training/weekly" className="flex items-center gap-3 p-4 bg-[#0A0A0F] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all hover:-translate-x-0.5 hover:-translate-y-0.5">
          <Sword className="w-5 h-5 text-[#0D7377]" />
          <div>
            <p className="text-sm font-medium">赛前训练</p>
            <p className="text-xs text-[#4B4B6A]">针对性备战</p>
          </div>
          <ChevronRight className="w-4 h-4 text-[#4B4B6A] ml-auto" />
        </Link>
      </div>
    </div>
  )
}
