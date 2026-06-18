import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import api from '../../api/client'

interface MatchPayload {
  id: string
  fixture_type: string
  season_day: number
  round_number: number
  home_team_id: string
  away_team_id: string
  home_team_name?: string
  away_team_name?: string
  home_score?: number
  away_score?: number
  status: 'scheduled' | 'ongoing' | 'finished'
  scheduled_at: string
  cup_stage?: string
  cup_group?: string
  engine_result?: EngineResult
}

interface EngineResult {
  winner_team_id?: string
  resolution?: string
  penalty_score?: { home: number; away: number }
  stats?: Record<string, number>
  player_stats?: PlayerStat[]
  events?: MatchEvent[]
  narratives?: string[]
}

interface MatchEvent {
  id?: number
  minute?: number
  type?: string
  team?: string
  player_name?: string
  result?: string
  narrative?: string
}

interface PlayerSetup {
  player_id: string
  name: string
  position: string
  stamina?: number
}

interface LineupsPayload {
  home_team_name?: string
  away_team_name?: string
  home_lineup: PlayerSetup[]
  away_lineup: PlayerSetup[]
  home_bench: PlayerSetup[]
  away_bench: PlayerSetup[]
  home_formation: string
  away_formation: string
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

export default function MatchDetail() {
  const { id } = useParams()
  const [match, setMatch] = useState<MatchPayload | null>(null)
  const [lineups, setLineups] = useState<LineupsPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const load = async () => {
      if (!id) return
      try {
        setLoading(true)
        setError(null)
        const [matchRes, lineupRes] = await Promise.all([
          api.get<MatchPayload>(`/matches/${id}`),
          api.get<LineupsPayload>(`/matches/${id}/lineups`),
        ])
        if (!matchRes.success || !matchRes.data) throw new Error('比赛不存在')
        setMatch(matchRes.data)
        if (lineupRes.success && lineupRes.data) setLineups(lineupRes.data)
      } catch (err) {
        setError(err instanceof Error ? err.message : '加载比赛失败')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [id])

  const stats = match?.engine_result?.stats || {}
  const narratives = useMemo(() => {
    const existing = match?.engine_result?.narratives || []
    if (existing.length > 0) return existing
    return (match?.engine_result?.events || [])
      .map(ev => ev.narrative ? `${formatMinute(ev.minute)} ${ev.narrative}` : '')
      .filter(Boolean)
  }, [match])

  if (loading) {
    return <div className="max-w-[1200px] space-y-4"><div className="h-10 bg-[#1E1E2D] animate-pulse" /><div className="h-80 bg-[#1E1E2D] animate-pulse" /></div>
  }

  if (error || !match) {
    return (
      <div className="max-w-[1200px] text-center py-20">
        <h2 className="text-xl font-bold text-white mb-2">比赛加载失败</h2>
        <p className="text-[#8B8BA7] mb-6">{error || '比赛不存在'}</p>
        <Link to="/match/schedule" className="btn-primary inline-flex items-center gap-2">
          返回赛程
        </Link>
      </div>
    )
  }

  const homeName = match.home_team_name || lineups?.home_team_name || match.home_team_id
  const awayName = match.away_team_name || lineups?.away_team_name || match.away_team_id
  const hasResult = match.status !== 'scheduled' && match.home_score !== undefined && match.away_score !== undefined

  return (
    <div className="max-w-[1200px] space-y-6">
      <Link to="/match/schedule" className="text-sm text-[#8B8BA7] hover:text-white transition-colors">
        返回赛程
      </Link>

      <section className="border-2 border-[#2D2D44] bg-[#11111A] px-6 py-6">
        <div className="flex items-center justify-between mb-6">
          <div className="text-sm text-[#8B8BA7]">
            {new Date(match.scheduled_at).toLocaleString('zh-CN')} · 第 {match.round_number} 轮
          </div>
          <StatusBadge status={match.status} resolution={match.engine_result?.resolution} />
        </div>

        <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-6">
          <TeamBlock name={homeName} teamId={match.home_team_id} align="right" />
          <div className="text-center">
            {hasResult ? (
              <div className="pixel-scoreboard">
                <span>{match.home_score}</span>
                <span className="mx-3 text-[#4B4B6A]">:</span>
                <span>{match.away_score}</span>
              </div>
            ) : (
              <div className="text-2xl font-bold text-[#4B4B6A]">VS</div>
            )}
            {match.engine_result?.penalty_score && (
              <p className="text-xs text-[#8B8BA7] mt-2">
                点球 {match.engine_result.penalty_score.home}:{match.engine_result.penalty_score.away}
              </p>
            )}
          </div>
          <TeamBlock name={awayName} teamId={match.away_team_id} align="left" />
        </div>
      </section>

      {match.status === 'scheduled' ? (
        <PreMatchView lineups={lineups} />
      ) : (
        <>
          <StatsPanel stats={stats} />
          <Commentary narratives={narratives} />
          <PlayerStats stats={match.engine_result?.player_stats || []} />
        </>
      )}
    </div>
  )
}

function TeamBlock({ name, teamId, align }: { name: string; teamId: string; align: 'left' | 'right' }) {
  return (
    <Link to={`/teams/${teamId}`} className={`block ${align === 'right' ? 'text-right' : 'text-left'} hover:text-[#0D7377] transition-colors`}>
      <p className="text-xl font-bold text-white">{name}</p>
      <p className="text-xs text-[#8B8BA7] mt-1">{align === 'right' ? '主队' : '客队'}</p>
    </Link>
  )
}

function StatusBadge({ status, resolution }: { status: string; resolution?: string }) {
  const label = status === 'scheduled' ? '未开始' : status === 'ongoing' ? '进行中' : resolutionLabel(resolution)
  const cls = status === 'ongoing' ? 'border-red-500/30 bg-red-500/20 text-red-400' : 'border-[#0D7377]/30 bg-[#0D4A4D]/40 text-[#0D7377]'
  return <span className={`text-xs px-2 py-1 border ${cls}`}>{label}</span>
}

function PreMatchView({ lineups }: { lineups: LineupsPayload | null }) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <LineupCard title="主队阵容" formation={lineups?.home_formation} players={lineups?.home_lineup || []} />
      <LineupCard title="客队阵容" formation={lineups?.away_formation} players={lineups?.away_lineup || []} />
    </div>
  )
}

function LineupCard({ title, formation, players }: { title: string; formation?: string; players: PlayerSetup[] }) {
  return (
    <div className="border-2 border-[#2D2D44] bg-[#11111A] p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-white">{title}</h3>
        <span className="text-xs text-[#8B8BA7]">{formation || 'F01'}</span>
      </div>
      <div className="space-y-2">
        {players.map(player => (
          <div key={player.player_id} className="flex items-center justify-between text-sm border-b border-[#2D2D44]/50 pb-2">
            <span className="text-white">{player.name}</span>
            <span className="text-[#8B8BA7]">{player.position}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function StatsPanel({ stats }: { stats: Record<string, number> }) {
  const rows = [
    ['控球率', stats.possession_home, stats.possession_away, '%'],
    ['射门', stats.shots_home, stats.shots_away, ''],
    ['射正', stats.shots_on_target_home, stats.shots_on_target_away, ''],
    ['传球', stats.passes_home, stats.passes_away, ''],
    ['角球', stats.corners_home, stats.corners_away, ''],
    ['犯规', stats.fouls_home, stats.fouls_away, ''],
  ]
  return (
    <section className="border-2 border-[#2D2D44] bg-[#11111A] p-4">
      <h3 className="font-semibold text-white mb-4">技术统计</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {rows.map(([label, home, away, unit]) => <StatRow key={label as string} label={label as string} home={Number(home || 0)} away={Number(away || 0)} unit={unit as string} />)}
      </div>
    </section>
  )
}

function StatRow({ label, home, away, unit }: { label: string; home: number; away: number; unit: string }) {
  const total = home + away
  const pct = total > 0 ? (home / total) * 100 : 50
  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-white font-bold">{Math.round(home)}{unit}</span>
        <span className="text-[#8B8BA7]">{label}</span>
        <span className="text-white font-bold">{Math.round(away)}{unit}</span>
      </div>
      <div className="flex h-2 bg-[#2D2D44]">
        <div className="bg-[#0D7377]" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

function Commentary({ narratives }: { narratives: string[] }) {
  return (
    <section className="border-2 border-[#2D2D44] bg-[#11111A] p-4">
      <h3 className="font-semibold text-white mb-4">比赛解说</h3>
      {narratives.length === 0 ? (
        <p className="text-sm text-[#8B8BA7]">暂无解说记录</p>
      ) : (
        <div className="space-y-2 max-h-[520px] overflow-y-auto pr-2">
          {narratives.map((line, index) => (
            <div key={index} className="text-sm text-[#E2E2F0] border-l-2 border-[#2D2D44] pl-3 py-1">{line}</div>
          ))}
        </div>
      )}
    </section>
  )
}

function PlayerStats({ stats }: { stats: PlayerStat[] }) {
  if (stats.length === 0) return null
  return (
    <section className="border-2 border-[#2D2D44] bg-[#11111A] p-4">
      <h3 className="font-semibold text-white mb-4">球员数据</h3>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-[#8B8BA7] border-b border-[#2D2D44]">
            <tr>
              <th className="text-left py-2">球员</th>
              <th>队</th>
              <th>位置</th>
              <th>进球</th>
              <th>助攻</th>
              <th>射门</th>
              <th>传球</th>
              <th>抢断</th>
              <th>扑救</th>
              <th>评分</th>
            </tr>
          </thead>
          <tbody>
            {stats.map(player => (
              <tr key={player.player_id} className="border-b border-[#2D2D44]/40 text-center">
                <td className="text-left py-2 text-white">{player.name}</td>
                <td className="text-[#8B8BA7]">{player.team === 'home' ? '主' : '客'}</td>
                <td className="text-[#8B8BA7]">{player.position}</td>
                <td>{player.goals}</td>
                <td>{player.assists}</td>
                <td>{player.shots}</td>
                <td>{player.passes}</td>
                <td>{player.tackles}</td>
                <td>{player.saves}</td>
                <td className="text-[#0D7377] font-bold">{player.rating?.toFixed?.(1) || player.rating}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function resolutionLabel(resolution?: string) {
  if (resolution === 'extra_time') return '加时结束'
  if (resolution === 'penalties') return '点球结束'
  if (resolution === 'draw') return '平局'
  return '已结束'
}

function formatMinute(minute?: number) {
  if (minute === undefined) return ''
  return `${Math.floor(minute)}'`
}
