import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Calendar,
  Chart,
  ChevronRight,
  Clipboard,
  Flag,
  Shield,
  Target,
  Trophy,
  Users,
  Wallet,
  Zap,
} from '../../components/ui/pixel-icons'
import api from '../../api/client'
import type { PlayerListItem } from '../../types/player'

interface Team {
  id: string
  name: string
  short_name?: string
  overall_rating: number
  attack: number
  midfield: number
  defense: number
  league_id?: string
  current_league_id?: string
  league_name?: string
}

interface DashboardStats {
  league_position: number | null
  points: number
  played: number
  won: number
  drawn: number
  lost: number
  goals_for: number
  goals_against: number
  goal_difference: number
  recent_form: string
  next_match: {
    opponent_id: string
    opponent_name: string
    is_home: boolean
    day: number
    fixture_type: string
  } | null
}

interface RecentMatch {
  opponent: string
  result: 'W' | 'D' | 'L'
  score: string
  date: string
  is_home: boolean
}

interface PlayerActivity {
  id: string
  name: string
  role: string
  detail: string
  value: string
  avatar: string
}

const activityByPosition: Record<string, { role: string; detail: string }> = {
  FW: { role: '前场组', detail: '冲刺、射门、禁区跑位' },
  MF: { role: '中场组', detail: '传控节奏、二点球保护' },
  DF: { role: '防线组', detail: '压迫距离、回追站位' },
  GK: { role: '门将组', detail: '出击判断、反应训练' },
}

function positionText(position?: string) {
  const map: Record<string, string> = {
    FW: '前锋',
    MF: '中场',
    DF: '后卫',
    GK: '门将',
  }
  return position ? map[position] || position : '球员'
}

function fixtureTypeText(type?: string) {
  const map: Record<string, string> = {
    LEAGUE: '联赛',
    CUP: '杯赛',
    CUP_LIGHTNING_GROUP: '闪电杯小组赛',
    CUP_LIGHTNING_KNOCKOUT: '闪电杯淘汰赛',
    FRIENDLY: '友谊赛',
  }
  return type ? map[type] || '赛事' : '联赛'
}

function FormIndicator({ form }: { form: string }) {
  if (!form) return <span className="fresh-muted">暂无走势</span>

  const resultConfig = {
    W: 'is-win',
    D: 'is-draw',
    L: 'is-loss',
  }

  return (
    <div className="fresh-form-strip" aria-label="近期战绩">
      {form.split('').slice(0, 5).map((result, index) => (
        <span
          key={`${result}-${index}`}
          className={resultConfig[result as keyof typeof resultConfig] || resultConfig.D}
        >
          {result === 'W' ? '胜' : result === 'D' ? '平' : '负'}
        </span>
      ))}
    </div>
  )
}

function MiniMetric({
  label,
  value,
  icon: Icon,
}: {
  label: string
  value: string
  icon: typeof Chart
}) {
  return (
    <div className="fresh-mini-metric">
      <Icon className="h-4 w-4" />
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function AbilityMeter({
  label,
  value,
  tone,
}: {
  label: string
  value?: number
  tone: 'lime' | 'coral' | 'amber' | 'sky'
}) {
  const safeValue = typeof value === 'number' ? Math.min(100, Math.max(0, value)) : 0

  return (
    <div className="fresh-meter">
      <div>
        <span>{label}</span>
        <strong>{typeof value === 'number' ? value : '-'}</strong>
      </div>
      <div className="fresh-meter-track">
        <div className={`fresh-meter-fill tone-${tone}`} style={{ width: `${safeValue}%` }} />
      </div>
    </div>
  )
}

function PlayerActivityRow({ activity }: { activity: PlayerActivity }) {
  return (
    <Link to={`/team/players/${activity.id}`} className="fresh-player-row">
      {activity.avatar ? (
        <img src={activity.avatar} alt={activity.name} />
      ) : (
        <div className="fresh-player-initial">{activity.name.charAt(0)}</div>
      )}
      <div className="min-w-0 flex-1">
        <div className="fresh-row-title">
          <strong>{activity.name}</strong>
          <span>{activity.value}</span>
        </div>
        <p>{activity.role}</p>
        <small>{activity.detail}</small>
      </div>
      <ChevronRight className="h-4 w-4" />
    </Link>
  )
}

function ManagerTask({
  title,
  detail,
  to,
  urgent,
}: {
  title: string
  detail: string
  to: string
  urgent?: boolean
}) {
  return (
    <Link to={to} className={`fresh-task ${urgent ? 'is-urgent' : ''}`}>
      <span className="fresh-task-pin" />
      <div>
        <strong>{title}</strong>
        <p>{detail}</p>
      </div>
      <ChevronRight className="h-4 w-4" />
    </Link>
  )
}

function RecentMatchRow({ match }: { match: RecentMatch }) {
  const resultClass = {
    W: 'is-win',
    D: 'is-draw',
    L: 'is-loss',
  }[match.result]

  return (
    <div className="fresh-result-row">
      <span className={resultClass}>{match.result === 'W' ? '胜' : match.result === 'D' ? '平' : '负'}</span>
      <div>
        <strong>{match.is_home ? '主场' : '客场'} {match.opponent}</strong>
        <p>{match.date}</p>
      </div>
      <b>{match.score}</b>
    </div>
  )
}

function Dashboard() {
  const [team, setTeam] = useState<Team | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [players, setPlayers] = useState<PlayerListItem[]>([])
  const [recentMatches, setRecentMatches] = useState<RecentMatch[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    const fetchRecentMatches = async (teamId: string) => {
      try {
        const seasonResponse = await api.get('/seasons/current')
        if (!seasonResponse.success) return

        const seasonNumber = (seasonResponse.data as { season_number?: number })?.season_number
        if (!seasonNumber) return

        const fixturesResponse = await api.get(`/seasons/${seasonNumber}/teams/${teamId}/fixtures?limit=5`)
        if (!fixturesResponse.success) return

        const fixtures = (fixturesResponse.data as { fixtures?: unknown[] })?.fixtures || []
        const completed = fixtures
          .filter((fixture: any) => fixture.status === 'finished')
          .slice(0, 5)
          .map((fixture: any) => {
            const isHome = fixture.home_team_id === teamId
            const myScore = isHome ? fixture.home_score : fixture.away_score
            const opponentScore = isHome ? fixture.away_score : fixture.home_score

            return {
              opponent: (isHome ? fixture.away_team_name : fixture.home_team_name) || '对手未定',
              result: myScore > opponentScore ? 'W' : myScore < opponentScore ? 'L' : 'D',
              score: `${myScore}:${opponentScore}`,
              date: fixture.season_day ? `Day ${fixture.season_day}` : '日期未定',
              is_home: isHome,
            } as RecentMatch
          })

        if (!cancelled) setRecentMatches(completed.reverse())
      } catch (error) {
        console.error('Failed to fetch recent matches:', error)
      }
    }

    const fetchData = async () => {
      try {
        setLoading(true)

        const teamResponse = await api.get<Team>('/teams/my-team')
        if (!teamResponse.success || !teamResponse.data) return

        if (!cancelled) setTeam(teamResponse.data)

        const [statsResponse, playersResponse] = await Promise.all([
          api.get<DashboardStats>('/teams/my-team/dashboard'),
          api
            .get<{ items: PlayerListItem[] }>(`/teams/${teamResponse.data.id}/players?page=1&page_size=8`)
            .catch(() => null),
        ])

        if (!cancelled && statsResponse.success) {
          setStats(statsResponse.data)
          await fetchRecentMatches(teamResponse.data.id)
        }

        if (!cancelled && playersResponse?.success) {
          setPlayers(playersResponse.data.items || [])
        }
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [])

  const leagueId = team?.league_id || team?.current_league_id
  const played = stats?.played
  const won = stats?.won
  const drawn = stats?.drawn
  const lost = stats?.lost
  const points = stats?.points
  const leaguePosition = stats?.league_position ? `第 ${stats.league_position} 名` : '未定级'
  const winRate = typeof played === 'number' && played > 0 && typeof won === 'number' ? Math.round((won / played) * 100) : null
  const form = stats?.recent_form ?? ''
  const goalDifference = typeof stats?.goal_difference === 'number' ? `${stats.goal_difference >= 0 ? '+' : ''}${stats.goal_difference}` : '-'

  const nextMatch = stats?.next_match
    ? {
        opponent: stats.next_match.opponent_name,
        isHome: stats.next_match.is_home,
        date: `第 ${stats.next_match.day} 天`,
        type: fixtureTypeText(stats.next_match.fixture_type),
      }
    : null

  const currentActivity = nextMatch
    ? {
        eyebrow: 'MATCHDAY QUEUE',
        title: '比赛日前台已亮灯',
        detail: `${nextMatch.date} ${nextMatch.isHome ? '主场' : '客场'}对阵 ${nextMatch.opponent}。先看状态，再定战术，最后确认名单。`,
        action: '进入赛前准备',
        to: '/match/pre',
        status: '待准备',
      }
    : {
        eyebrow: 'TRAINING DAY',
        title: '今天从训练场开始',
        detail: '当前没有临近比赛。适合安排训练负荷、查看球员成长，并提前整理下一轮轮换。',
        action: '安排本周训练',
        to: '/training/weekly',
        status: '训练日',
      }

  const playerActivities = useMemo<PlayerActivity[]>(() => {
    const source = players.slice(0, 5)

    return source.map((player) => {
      const activity = activityByPosition[player.position] || activityByPosition.MF

      return {
        id: player.id,
        name: player.name,
        role: `${positionText(player.position)} · ${activity.role}`,
        detail: activity.detail,
        value: `OVR ${player.ovr || '-'}`,
        avatar: player.avatar_url ? `/${player.avatar_url}` : '',
      }
    })
  }, [players])

  const taskItems = [
    {
      title: nextMatch ? '锁定首发名单' : '铺开训练课表',
      detail: nextMatch ? `${nextMatch.date} 对阵 ${nextMatch.opponent}` : '按体能与短板拆分训练组',
      to: nextMatch ? '/match/pre' : '/training/weekly',
      urgent: !!nextMatch,
    },
    {
      title: '微调战术站位',
      detail: team ? `进攻 ${team.attack || '-'} / 中场 ${team.midfield || '-'} / 防守 ${team.defense || '-'}` : '等待球队能力数据',
      to: '/team/tactics',
    },
    {
      title: '巡视更衣室',
      detail: players.length > 0 ? `${players.length} 名球员已载入` : '暂无球员数据',
      to: '/team/players',
    },
    {
      title: '查看董事会预算',
      detail: '工资、青训投入与赛季盈亏',
      to: '/finance',
    },
  ]

  const quickLinks = [
    { label: '战术板', to: '/team/tactics', icon: Target, tone: 'lime' },
    { label: '更衣室', to: '/team/players', icon: Users, tone: 'sky' },
    { label: '赛程', to: '/match/schedule', icon: Calendar, tone: 'coral' },
    { label: '联赛', to: leagueId ? `/leagues/${leagueId}` : '/leagues', icon: Trophy, tone: 'amber' },
    { label: '转会', to: '/transfer', icon: Wallet, tone: 'mint' },
  ]

  return (
    <div className="fresh-dashboard">
      <section className="fresh-hero" style={{ backgroundImage: "url('/dashboard/fresh-dashboard-bg-v1.png')" }}>
        <div className="fresh-hero-copy">
          <span className="fresh-eyebrow">{currentActivity.eyebrow}</span>
          <h1>{currentActivity.title}</h1>
          <p>{currentActivity.detail}</p>

          <div className="fresh-hero-actions">
            <Link to={currentActivity.to} className="fresh-primary-action">
              <Zap className="h-4 w-4" />
              {currentActivity.action}
            </Link>
            <Link to="/team/players" className="fresh-secondary-action">
              查看球员状态
            </Link>
          </div>
        </div>

        <div className="fresh-scoreboard">
          <div className="fresh-scoreboard-head">
            <span>{currentActivity.status}</span>
            <FormIndicator form={form} />
          </div>
          <div className="fresh-club-name">
            <small>{team?.league_name || 'Lightning Super League'}</small>
            <strong>{team?.short_name || team?.name || '我的球队'}</strong>
          </div>
          <div className="fresh-score-grid">
            <MiniMetric icon={Flag} label="排名" value={leaguePosition} />
            <MiniMetric icon={Trophy} label="积分" value={typeof points === 'number' ? `${points}` : '-'} />
            <MiniMetric icon={Chart} label="胜率" value={winRate !== null ? `${winRate}%` : '-'} />
            <MiniMetric icon={Shield} label="净胜" value={goalDifference} />
          </div>
        </div>
      </section>

      <nav className="fresh-quick-pitch" aria-label="快速入口">
        {quickLinks.map((item) => (
          <Link key={item.label} to={item.to} className={`fresh-pitch-link tone-${item.tone}`}>
            <item.icon className="h-5 w-5" />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <section className="fresh-console-grid">
        <div className="fresh-match-card">
          <div className="fresh-section-title">
            <div>
              <span>Next Fixture</span>
              <h2>下一场比赛</h2>
            </div>
            <Calendar className="h-5 w-5" />
          </div>

          {nextMatch ? (
            <div className="fresh-fixture">
              <div className="fresh-fixture-meta">
                <span>{nextMatch.type}</span>
                <strong>{nextMatch.date}</strong>
              </div>
              <div className="fresh-versus">
                <div>
                  <small>{nextMatch.isHome ? '主场' : '客场'}</small>
                  <strong>{team?.short_name || team?.name || '我的球队'}</strong>
                </div>
                <b>VS</b>
                <div>
                  <small>{nextMatch.isHome ? '客场' : '主场'}</small>
                  <strong>{nextMatch.opponent}</strong>
                </div>
              </div>
              <Link to="/match/pre" className="fresh-ticket-action">
                <Clipboard className="h-4 w-4" />
                打开比赛清单
              </Link>
            </div>
          ) : (
            <div className="fresh-empty">暂无比赛安排，先把训练节奏跑顺。</div>
          )}
        </div>

        <div className="fresh-team-card">
          <div className="fresh-section-title">
            <div>
              <span>Club Shape</span>
              <h2>球队状态</h2>
            </div>
            <strong>{typeof team?.overall_rating === 'number' ? team.overall_rating : '-'}</strong>
          </div>
          <div className="fresh-meter-stack">
            <AbilityMeter label="综合" value={team?.overall_rating} tone="lime" />
            <AbilityMeter label="进攻" value={team?.attack} tone="coral" />
            <AbilityMeter label="中场" value={team?.midfield} tone="amber" />
            <AbilityMeter label="防守" value={team?.defense} tone="sky" />
          </div>
        </div>

        <div className="fresh-roster-card">
          <div className="fresh-section-title">
            <div>
              <span>Dressing Room</span>
              <h2>球员状态</h2>
            </div>
            <Link to="/team/players">全队</Link>
          </div>
          {playerActivities.length > 0 ? (
            <div className="fresh-player-list">
              {playerActivities.map((activity) => (
                <PlayerActivityRow key={activity.id} activity={activity} />
              ))}
            </div>
          ) : (
            <div className="fresh-empty">后端暂未返回球员列表。</div>
          )}
        </div>

        <div className="fresh-tasks-card">
          <div className="fresh-section-title">
            <div>
              <span>Touchline Notes</span>
              <h2>经理待办</h2>
            </div>
            <Clipboard className="h-5 w-5" />
          </div>
          <div className="fresh-task-list">
            {taskItems.map((task) => (
              <ManagerTask key={task.title} {...task} />
            ))}
          </div>
        </div>

        <div className="fresh-results-card">
          <div className="fresh-section-title">
            <div>
              <span>Recent Results</span>
              <h2>最近比赛</h2>
            </div>
            <Link to="/match/schedule">赛程表</Link>
          </div>
          {loading ? (
            <div className="fresh-loading-lines">
              <span />
              <span />
              <span />
            </div>
          ) : recentMatches.length > 0 ? (
            <div className="fresh-result-list">
              {recentMatches.slice(0, 4).map((match, index) => (
                <RecentMatchRow key={`${match.opponent}-${index}`} match={match} />
              ))}
            </div>
          ) : (
            <div className="fresh-empty">还没有可展示的比赛记录。</div>
          )}
        </div>

        <div className="fresh-season-card">
          <span>Season Line</span>
          <strong>
            {typeof won === 'number' && typeof drawn === 'number' && typeof lost === 'number'
              ? `${won}-${drawn}-${lost}`
              : '暂无战绩'}
          </strong>
          <p>
            {typeof stats?.goals_for === 'number' && typeof stats?.goals_against === 'number'
              ? `进 ${stats.goals_for} / 失 ${stats.goals_against}`
              : '等待赛季数据'}
          </p>
        </div>
      </section>
    </div>
  )
}

export default Dashboard
