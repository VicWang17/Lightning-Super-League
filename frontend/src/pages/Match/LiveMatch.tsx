import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronRight,
  Zap
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import { Card } from '../../components/ui/Card'

interface LiveMatchData {
  match_id: string
  status: string
  current_minute: number
  home_score: number
  away_score: number
  events: Array<{
    minute?: number
    type?: string
    team?: string
    player_name?: string
    narrative?: string
  }>
  narratives: string[]
  stats: Record<string, number>
}

interface MatchPayload {
  id: string
  home_team_id: string
  away_team_id: string
  home_team_name?: string
  away_team_name?: string
  home_score?: number
  away_score?: number
  status: string
}

export default function LiveMatch() {
  const [match, setMatch] = useState<MatchPayload | null>(null)
  const [live, setLive] = useState<LiveMatchData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

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

        // 查找进行中的比赛
        const matchesRes = await api.get<{ items: MatchPayload[] }>(`/matches?team_id=${teamId}&status=ongoing&page_size=1`)
        if (!matchesRes.success || !matchesRes.data?.items?.length) {
          // 如果没有 ongoing，尝试找最近已完成的比赛作为 fallback
          const finishedRes = await api.get<{ items: MatchPayload[] }>(`/matches?team_id=${teamId}&status=finished&page_size=1`)
          if (!finishedRes.success || !finishedRes.data?.items?.length) {
            setError('暂无比赛数据')
            setLoading(false)
            return
          }
          const m = finishedRes.data.items[0]
          setMatch(m)
          const liveRes = await api.get<LiveMatchData>(`/matches/${m.id}/live`)
          if (!cancelled && liveRes.success) setLive(liveRes.data)
          setLoading(false)
          return
        }
        const ongoingMatch = matchesRes.data.items[0]
        setMatch(ongoingMatch)

        const liveRes = await api.get<LiveMatchData>(`/matches/${ongoingMatch.id}/live`)
        if (!cancelled && liveRes.success) setLive(liveRes.data)
      } catch {
        if (!cancelled) setError('加载失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetch()
    return () => { cancelled = true }
  }, [])

  // 自动滚动
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [live?.events])

  const isLive = match?.status === 'ongoing'
  const homeName = match?.home_team_name || match?.home_team_id || '主队'
  const awayName = match?.away_team_name || match?.away_team_id || '客队'
  const homeScore = live?.home_score ?? match?.home_score ?? 0
  const awayScore = live?.away_score ?? match?.away_score ?? 0
  const currentMinute = live?.current_minute ?? 0

  // 合并事件和解说
  const narratives = live?.narratives || []
  const events = live?.events || []
  const allEvents = events
    .map(e => ({ time: e.minute ?? 0, text: e.narrative || `${e.type} - ${e.player_name || ''}`, type: e.type || 'normal' }))
    .concat(narratives.map((n, i) => ({ time: 0, text: n, type: 'normal', id: `n-${i}` })))
    .sort((a, b) => a.time - b.time)

  if (loading) {
    return <div className="max-w-[1200px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  if (error || !match) {
    return (
      <div className="max-w-[1200px] p-8 text-center">
        <p className="text-[#8B8BA7]">{error || '暂无比赛数据'}</p>
        <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white mt-4 inline-block">
          查看赛程 →
        </Link>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-[1200px]">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-white">比赛直播</h1>
          {isLive && (
            <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs border border-red-500/30 animate-pulse">
              ● LIVE
            </span>
          )}
        </div>
        <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white transition-colors">
          返回赛程 →
        </Link>
      </div>

      {/* 比分牌 */}
      <Card className="bg-[#0D4A4D]/20 border-[#0D7377]/30">
        <div className="flex items-center justify-center gap-6 py-8">
          <div className="text-center">
            <div className="w-16 h-16 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center mx-auto mb-2 shadow-pixel-green">
              <span className="text-2xl">🏠</span>
            </div>
            <p className="text-sm font-bold">{homeName}</p>
          </div>

          <div className="text-center px-8">
            <div className="text-5xl font-bold pixel-number text-white">
              {homeScore} : {awayScore}
            </div>
            <p className="text-sm text-[#0D7377] font-bold mt-2">
              {isLive ? `${currentMinute}' 进行中` : '已结束'}
            </p>
          </div>

          <div className="text-center">
            <div className="w-16 h-16 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
              <span className="text-2xl">✈</span>
            </div>
            <p className="text-sm font-bold">{awayName}</p>
          </div>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 文字直播 */}
        <div className="lg:col-span-2">
          <Card>
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Zap className="w-4 h-4 text-[#0D7377]" />
              比赛解说
            </h3>
            <div
              ref={scrollRef}
              className="space-y-2 max-h-[500px] overflow-y-auto pr-2"
            >
              {allEvents.length === 0 && (
                <p className="text-sm text-[#4B4B6A] text-center py-8">暂无比赛事件</p>
              )}
              {allEvents.map((ev, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-3 p-2 border-l-2 ${
                    ev.type === 'goal' ? 'bg-yellow-500/10 border-yellow-500' :
                    ev.type === 'yellow' ? 'bg-yellow-500/5 border-yellow-500' :
                    ev.type === 'red' ? 'bg-red-500/10 border-red-500' :
                    ev.type === 'half' || ev.type === 'full' ? 'bg-[#0D7377]/10 border-[#0D7377]' :
                    'border-[#2D2D44]'
                  }`}
                >
                  {ev.time ? <span className="text-xs text-[#4B4B6A] font-mono w-8">{ev.time}'</span> : null}
                  <span className={`text-sm ${
                    ev.type === 'goal' ? 'text-yellow-400 font-bold' :
                    ev.type === 'half' || ev.type === 'full' ? 'text-[#0D7377] font-bold' :
                    'text-[#E2E2F0]'
                  }`}>
                    {ev.text}
                  </span>
                </div>
              ))}
              {isLive && <div className="animate-pulse text-xs text-[#4B4B6A]">实时更新中...</div>}
            </div>
          </Card>
        </div>

        {/* 数据统计 */}
        <div className="space-y-6">
          <Card>
            <h3 className="text-lg font-semibold mb-4">数据统计</h3>
            <div className="space-y-4">
              <StatRow label="控球率" home={live?.stats?.possession_home ?? 50} away={live?.stats?.possession_away ?? 50} unit="%" />
              <StatRow label="射门" home={live?.stats?.shots_home ?? 0} away={live?.stats?.shots_away ?? 0} />
              <StatRow label="射正" home={live?.stats?.shots_on_target_home ?? 0} away={live?.stats?.shots_on_target_away ?? 0} />
              <StatRow label="角球" home={live?.stats?.corners_home ?? 0} away={live?.stats?.corners_away ?? 0} />
              <StatRow label="犯规" home={live?.stats?.fouls_home ?? 0} away={live?.stats?.fouls_away ?? 0} />
            </div>
          </Card>

          {!isLive && match && (
            <Link
              to={`/match/${match.id}`}
              className="flex items-center justify-center gap-2 px-4 py-2 bg-[#0D7377] border-2 border-[#0A5A5D] text-white text-sm font-medium hover:bg-[#0A5A5D] transition-all"
            >
              <ChevronRight className="w-4 h-4" />
              查看完整统计
            </Link>
          )}
        </div>
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
