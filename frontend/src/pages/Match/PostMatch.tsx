import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../api/client'
import { Card } from '../../components/ui/Card'
import { PageHeader } from '../../components/ui/PageHeader'

interface MatchPayload {
  id: string
  home_team_id: string
  away_team_id: string
  home_team_name?: string
  away_team_name?: string
  home_score?: number
  away_score?: number
  status: string
  engine_result?: {
    winner_team_id?: string
    resolution?: string
    penalty_score?: { home: number; away: number }
  }
}

interface PlayerStat {
  player_id: string
  name: string
  position: string
  team: 'home' | 'away'
  goals: number
  assists: number
  shots: number
  passes: number
  tackles: number
  saves: number
  rating: number
}

interface MatchStatsPayload {
  match_id: string
  stats: Record<string, number>
  player_stats: PlayerStat[]
  resolution?: string
  winner_team_id?: string
  penalty_score?: { home: number; away: number }
}

export default function PostMatch() {
  const [match, setMatch] = useState<MatchPayload | null>(null)
  const [stats, setStats] = useState<MatchStatsPayload | null>(null)
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

        // 查找最近完成的比赛
        const matchesRes = await api.get<{ items: MatchPayload[] }>(`/matches?team_id=${teamId}&status=finished&page_size=1`)
        if (!matchesRes.success || !matchesRes.data?.items?.length) {
          setError('暂无已完成比赛')
          setLoading(false)
          return
        }
        const finishedMatch = matchesRes.data.items[0]
        setMatch(finishedMatch)

        const statsRes = await api.get<MatchStatsPayload>(`/matches/${finishedMatch.id}/stats`)
        if (!cancelled && statsRes.success) {
          setStats(statsRes.data)
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
        <p className="text-[#8B8BA7]">{error || '暂无已完成比赛'}</p>
        <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white mt-4 inline-block">
          查看赛程 →
        </Link>
      </div>
    )
  }

  const homeName = match.home_team_name || match.home_team_id
  const awayName = match.away_team_name || match.away_team_id
  const homeScore = match.home_score ?? 0
  const awayScore = match.away_score ?? 0

  // 判断胜负
  const isWin = (match.engine_result?.winner_team_id === match.home_team_id && homeScore > awayScore) ||
                (match.engine_result?.winner_team_id === match.away_team_id && awayScore > homeScore)
  const isDraw = homeScore === awayScore

  const matchStats = stats?.stats || {}
  const playerStats = stats?.player_stats || []
  const mvp = [...playerStats].sort((a, b) => b.rating - a.rating)[0]

  return (
    <div className="space-y-6 max-w-[1200px]">
      <PageHeader
        title="赛后统计"
        subtitle="全场结束"
        action={
          <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white transition-colors">
            返回赛程 →
          </Link>
        }
      />

      {/* 比分结果 */}
      <Card className="bg-[#0D4A4D]/20 border-[#0D7377]/30">
        <div className="flex items-center justify-center gap-8 py-8">
          <div className="text-center">
            <div className="w-20 h-20 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center mx-auto mb-3 shadow-pixel-green">
              <span className="text-3xl">🏠</span>
            </div>
            <h2 className="text-xl font-bold">{homeName}</h2>
          </div>

          <div className="text-center">
            <div className="text-5xl font-bold pixel-number text-white">
              {homeScore} : {awayScore}
            </div>
            <span className={`inline-block mt-3 px-3 py-1 text-xs border ${
              isWin ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
              isDraw ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' :
              'bg-red-500/20 text-red-400 border-red-500/30'
            }`}>
              {isWin ? '胜利' : isDraw ? '平局' : '失利'}
            </span>
            {stats?.penalty_score && (
              <p className="text-xs text-[#8B8BA7] mt-2">
                点球 {stats.penalty_score.home}:{stats.penalty_score.away}
              </p>
            )}
          </div>

          <div className="text-center">
            <div className="w-20 h-20 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-3">
              <span className="text-3xl">✈</span>
            </div>
            <h2 className="text-xl font-bold">{awayName}</h2>
          </div>
        </div>
      </Card>

      {/* MVP */}
      {mvp && (
        <Card className="border-yellow-500/30">
          <div className="flex items-center gap-4">
            <div>
              <p className="text-xs text-yellow-400 font-bold uppercase tracking-wider">本场最佳</p>
              <h3 className="text-2xl font-bold text-white">{mvp.name}</h3>
              <p className="text-sm text-[#8B8BA7]">{mvp.position} · 评分 {mvp.rating.toFixed(1)} · {mvp.goals}进球 {mvp.assists}助攻</p>
            </div>
          </div>
        </Card>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 球员评分 */}
        <Card >
          <h3 className="text-lg font-semibold mb-4">
            球员评分
          </h3>
          {playerStats.length === 0 ? (
            <p className="text-[#8B8BA7] text-center py-8">暂无球员数据</p>
          ) : (
            <div className="space-y-2">
              {playerStats.sort((a, b) => b.rating - a.rating).map(p => (
                <div key={p.player_id} className="flex items-center gap-3 p-2 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                  <div className="w-8 h-8 bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center">
                    <span className="text-[10px] font-bold text-[#8B8BA7]">{p.position}</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{p.name}</p>
                    <div className="flex items-center gap-2 text-[10px] text-[#4B4B6A]">
                      {p.goals > 0 && <span className="text-yellow-400">⚽{p.goals}</span>}
                      {p.assists > 0 && <span className="text-[#0D7377]">🅰️{p.assists}</span>}
                    </div>
                  </div>
                  <div className={`w-10 h-8 flex items-center justify-center text-sm font-bold pixel-number ${
                    p.rating >= 8 ? 'bg-yellow-500/20 text-yellow-400' :
                    p.rating >= 7 ? 'bg-emerald-500/20 text-emerald-400' :
                    p.rating >= 6 ? 'bg-[#2D2D44] text-[#8B8BA7]' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {p.rating.toFixed(1)}
                  </div>
                </div>
              ))}
            </div>
          )}
        </Card>

        {/* 全场数据 */}
        <Card >
          <h3 className="text-lg font-semibold mb-4">
            全场数据
          </h3>
          <div className="space-y-4">
            <StatRow label="控球率" home={matchStats.possession_home ?? 50} away={matchStats.possession_away ?? 50} unit="%" />
            <StatRow label="射门" home={matchStats.shots_home ?? 0} away={matchStats.shots_away ?? 0} />
            <StatRow label="射正" home={matchStats.shots_on_target_home ?? 0} away={matchStats.shots_on_target_away ?? 0} />
            <StatRow label="角球" home={matchStats.corners_home ?? 0} away={matchStats.corners_away ?? 0} />
            <StatRow label="犯规" home={matchStats.fouls_home ?? 0} away={matchStats.fouls_away ?? 0} />
            <StatRow label="黄牌" home={matchStats.yellows_home ?? 0} away={matchStats.yellows_away ?? 0} />
            <StatRow label="红牌" home={matchStats.reds_home ?? 0} away={matchStats.reds_away ?? 0} />
          </div>
        </Card>
      </div>
    </div>
  )
}

function StatRow({ label, home, away, unit = '' }: { label: string; home: number; away: number; unit?: string }) {
  const total = home + away
  const homePct = total > 0 ? (home / total) * 100 : 50

  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-bold text-white">{home}{unit}</span>
        <span className="text-xs text-[#8B8BA7]">{label}</span>
        <span className="text-sm font-bold text-white">{away}{unit}</span>
      </div>
      <div className="flex h-2">
        <div className="bg-[#0D7377]" style={{ width: `${homePct}%` }} />
        <div className="bg-[#4B4B6A]" style={{ width: `${100 - homePct}%` }} />
      </div>
    </div>
  )
}
