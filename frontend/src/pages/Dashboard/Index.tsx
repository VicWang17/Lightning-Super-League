import { useEffect, useMemo, useState, type ElementType } from 'react'
import { Link } from 'react-router-dom'
import {
  Calendar,
  ChevronRight,
  Clock,
  Mailbox,
  Shield,
  Sword as Swords,
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
  FW: { role: '前场组', detail: '等待训练状态接入' },
  MF: { role: '中场组', detail: '等待训练状态接入' },
  DF: { role: '防线组', detail: '等待训练状态接入' },
  GK: { role: '门将组', detail: '等待训练状态接入' },
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
  if (!form) return <span className="text-[#6E7258]">暂无</span>

  const resultConfig = {
    W: 'bg-[#9ECF45] text-[#10220D]',
    D: 'bg-[#5E6472] text-white',
    L: 'bg-[#D75A4A] text-white',
  }

  return (
    <div className="flex items-center gap-1">
      {form.split('').slice(0, 5).map((result, index) => (
        <span
          key={`${result}-${index}`}
          className={`flex h-5 w-5 items-center justify-center border-2 border-[#171B14] text-[10px] font-bold ${
            resultConfig[result as keyof typeof resultConfig] || resultConfig.D
          }`}
        >
          {result}
        </span>
      ))}
    </div>
  )
}

function StatusTile({
  label,
  value,
  icon: Icon,
  tone = 'default',
}: {
  label: string
  value: string
  icon: ElementType
  tone?: 'default' | 'green' | 'amber'
}) {
  const toneClass = {
    default: 'border-[#56613D] bg-[#151A10] text-[#E8EAD8]',
    green: 'border-[#9ECF45] bg-[#0C1A0D] text-[#F1FFC5]',
    amber: 'border-[#D7A94A] bg-[#3B270D] text-[#FFE2A1]',
  }[tone]

  return (
    <div className={`pixel-panel flex items-center gap-3 p-3 ${toneClass}`}>
      <div className="flex h-10 w-10 items-center justify-center border-2 border-[#070907] bg-[#070907]">
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0">
        <p className="text-[11px] uppercase tracking-wider text-white/45">{label}</p>
        <p className="truncate text-sm font-bold">{value}</p>
      </div>
    </div>
  )
}

function PlayerActivityRow({ activity }: { activity: PlayerActivity }) {
  return (
    <div className="training-slip">
      {activity.avatar ? (
        <img
          src={activity.avatar}
          alt={activity.name}
          className="h-14 w-14 border-2 border-[#1C2417] bg-[#1D2418] object-cover"
        />
      ) : (
        <div className="flex h-14 w-14 items-center justify-center border-2 border-[#1C2417] bg-[#1D2418] text-lg font-black text-[#CDEB7B]">
          {activity.name.charAt(0)}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-2">
          <p className="truncate text-sm font-black text-[#E8EAD8]">{activity.name}</p>
          <span className="border-2 border-[#5E6B3B] bg-[#11141A] px-1.5 py-0.5 text-[10px] font-bold text-[#CDEB7B]">
            {activity.value}
          </span>
        </div>
        <p className="mt-1 text-xs font-bold text-[#9CA77A]">{activity.role}</p>
        <p className="truncate text-xs text-[#737B5B]">{activity.detail}</p>
      </div>
    </div>
  )
}

function ManagerTask({
  icon: Icon,
  title,
  detail,
  to,
  urgent,
}: {
  icon: ElementType
  title: string
  detail: string
  to: string
  urgent?: boolean
}) {
  return (
    <Link
      to={to}
      className={`task-note group ${urgent ? 'task-note-urgent' : ''}`}
    >
      <div
        className={`flex h-10 w-10 shrink-0 items-center justify-center border-2 ${
          urgent
            ? 'border-[#6B4C25] bg-[#3B270D] text-[#FFE2A1]'
            : 'border-[#5E6B3B] bg-[#11141A] text-[#CDEB7B]'
        }`}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-black text-[#E8EAD8]">{title}</p>
        <p className="truncate text-xs font-medium text-[#9CA77A]">{detail}</p>
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-[#6F7656] group-hover:text-[#CDEB7B]" />
    </Link>
  )
}

function RecentMatchRow({ match }: { match: RecentMatch }) {
  const config = {
    W: 'bg-[#9ECF45] text-[#10220D]',
    D: 'bg-[#5E6472] text-white',
    L: 'bg-[#D75A4A] text-white',
  }[match.result]

  return (
    <div className="match-stub">
      <span className={`flex h-8 w-8 items-center justify-center border-2 border-black/40 text-xs font-bold ${config}`}>
        {match.result === 'W' ? '胜' : match.result === 'D' ? '平' : '负'}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-[#E8EAD8]">
          {match.is_home ? '主场' : '客场'} {match.opponent}
        </p>
        <p className="text-xs text-[#737B5B]">{match.date}</p>
      </div>
      <p className="font-mono text-sm font-black text-[#E8EAD8]">{match.score}</p>
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
        eyebrow: '赛程已更新',
        title: '赛前准备窗口',
        detail: `${nextMatch.date} ${nextMatch.isHome ? '主场' : '客场'}对阵 ${nextMatch.opponent}。当前后端未提供实时训练状态，请先确认首发、战术和定位球。`,
        action: '进入赛前准备',
        to: '/match/pre',
        status: '待准备',
      }
    : {
        eyebrow: '暂无实时活动',
        title: '等待训练或比赛状态',
        detail: '当前后端没有返回正在进行的训练或比赛。你可以查看赛程、训练计划和球员名单。',
        action: '查看训练计划',
        to: '/training/weekly',
        status: '无活动',
      }

  const playerActivities = useMemo<PlayerActivity[]>(() => {
    const source = players.slice(0, 4)

    return source.map((player) => {
      const position = player.position
      const activity = activityByPosition[position] || activityByPosition.MF

      return {
        id: player.id,
        name: player.name,
        role: `${positionText(position)} · ${activity.role}`,
        detail: activity.detail,
        value: `OVR ${player.ovr || '-'}`,
        avatar: player.avatar_url ? `/${player.avatar_url}` : '',
      }
    })
  }, [players])

  const taskItems = [
    {
      icon: Swords,
      title: nextMatch ? '确认比赛计划' : '制定本周训练',
      detail: nextMatch ? `${nextMatch.date} 对阵 ${nextMatch.opponent}` : '根据体能和阵容短板安排课程',
      to: nextMatch ? '/match/pre' : '/training/weekly',
      urgent: !!nextMatch,
    },
    {
      icon: Target,
      title: '检查战术板',
      detail: team ? `进攻 ${team.attack || '-'} / 中场 ${team.midfield || '-'} / 防守 ${team.defense || '-'}` : '暂无球队能力数据',
      to: '/team/tactics',
    },
    {
      icon: Users,
      title: '巡视更衣室',
      detail: players.length > 0 ? `${players.length} 名球员已载入` : '暂无球员数据',
      to: '/team/players',
    },
    {
      icon: Wallet,
      title: '查看董事会预算',
      detail: '工资帽、青训投入与赛季盈亏',
      to: '/finance',
    },
  ]

  return (
    <div className="dashboard-home mx-auto max-w-[1500px] space-y-5">
      <section
        className="manager-hero pixel-panel relative min-h-[440px] overflow-hidden border-[#242832] bg-[#07080A]"
        style={{ backgroundImage: "url('/dashboard/manager-office-training-v1.png')" }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-[#050609] via-[#050609]/88 to-[#050609]/46" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#050609] via-[#050609]/30 to-[#050609]/62" />
        <div className="relative z-10 grid min-h-[440px] gap-5 p-5 lg:grid-cols-[1.15fr_0.85fr] lg:p-7">
          <div className="flex max-w-3xl flex-col justify-between">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 border-2 border-[#9ECF45] bg-[#0B1409] px-3 py-1.5 text-xs font-bold text-[#DFFFB4]">
                <span className="h-2 w-2 bg-[#9ECF45]" />
                {currentActivity.eyebrow}
              </div>
              <h1 className="max-w-2xl text-3xl font-black leading-tight text-[#F4F7DF] sm:text-4xl lg:text-5xl">
                {currentActivity.title}
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-7 text-[#C7CBB8] sm:text-base">
                {currentActivity.detail}
              </p>
            </div>

            <div className="mt-8 flex flex-wrap items-center gap-3">
              <Link to={currentActivity.to} className="btn-primary inline-flex items-center gap-2">
                <Zap className="h-4 w-4" />
                {currentActivity.action}
              </Link>
              <Link to="/team/players" className="btn-secondary inline-flex items-center gap-2">
                <Users className="h-4 w-4" />
                查看球员状态
              </Link>
            </div>
          </div>

          <div className="grid content-end gap-3 sm:grid-cols-2 lg:grid-cols-1">
            <StatusTile label="当前状态" value={currentActivity.status} icon={Clock} tone={nextMatch ? 'green' : 'amber'} />
            <StatusTile label="联赛排名" value={`${leaguePosition}${typeof points === 'number' ? ` · ${points} 分` : ''}`} icon={Trophy} />
            <StatusTile
              label="赛季战绩"
              value={
                typeof won === 'number' && typeof drawn === 'number' && typeof lost === 'number'
                  ? `${won}-${drawn}-${lost}${winRate !== null ? ` · 胜率 ${winRate}%` : ''}`
                  : '暂无战绩'
              }
              icon={Swords}
            />
          </div>
        </div>
      </section>

      <section className="office-console">
        <div className="console-left">
          <section className="roster-ledger">
            <div className="console-heading">
              <div>
                <h2 className="text-xl font-black text-[#E8EAD8]">球员状态</h2>
              </div>
              <Link to="/training/weekly" className="console-link">训练计划</Link>
            </div>
            {playerActivities.length > 0 ? (
              <div className="compact-roster">
                {playerActivities.map((activity) => (
                  <PlayerActivityRow key={activity.id} activity={activity} />
                ))}
              </div>
            ) : (
              <div className="empty-line">后端暂未返回球员列表。</div>
            )}
          </section>

          <section className="agenda-strip">
            <div className="console-heading">
              <h2 className="text-lg font-black text-[#E8EAD8]">经理待办</h2>
              <Mailbox className="h-5 w-5 text-[#CDEB7B]" />
            </div>
            <div className="agenda-grid">
              {taskItems.slice(0, 3).map((task) => (
                <ManagerTask key={task.title} {...task} />
              ))}
            </div>
          </section>

          <section className="status-strip">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-lg font-black text-[#E8EAD8]">俱乐部状态</h2>
              <FormIndicator form={form} />
            </div>
            <div className="status-grid">
              {[
                { label: '综合', value: team?.overall_rating, color: 'bg-[#CDEB7B]' },
                { label: '进攻', value: team?.attack, color: 'bg-[#D75A4A]' },
                { label: '中场', value: team?.midfield, color: 'bg-[#D7A94A]' },
                { label: '防守', value: team?.defense, color: 'bg-[#6EA8E5]' },
              ].map((item) => {
                const value = typeof item.value === 'number' ? item.value : 0
                return (
                  <div key={item.label} className="status-meter compact">
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="font-black text-[#C7CBB8]">{item.label}</span>
                      <span className="font-mono font-bold text-[#E8EAD8]">{typeof item.value === 'number' ? item.value : '-'}</span>
                    </div>
                    <div className="pixel-progress-track h-3 border-[#242832] bg-[#070907]">
                      <div className={`pixel-progress-fill ${item.color}`} style={{ width: `${value}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
          </section>
        </div>

        <aside className="console-right">
          <section className="fixture-brief">
            <div className="console-heading amber">
              <div className="flex items-center gap-2">
                <Calendar className="h-5 w-5 text-[#FFE2A1]" />
                <h2 className="text-lg font-black text-[#F7E9C6]">下一场比赛</h2>
              </div>
              <span className="ticket-serial">LSL-{stats?.next_match?.day || '---'}</span>
            </div>
            {nextMatch ? (
              <>
                <div className="match-ticket compact-ticket p-4">
                  <div className="mb-3 flex items-center justify-between border-b-2 border-[#6B4C25] pb-2">
                    <p className="text-xs font-black text-[#BFA56B]">{nextMatch.type}</p>
                    <p className="text-xs font-black text-[#BFA56B]">{nextMatch.date}</p>
                  </div>
                  <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                    <div className="min-w-0 text-center">
                      <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center border-2 border-[#6B4C25] bg-[#07080A]">
                        <Shield className="h-6 w-6 text-[#CDEB7B]" />
                      </div>
                      <p className="truncate text-sm font-bold text-[#F7E9C6]">{team?.short_name || team?.name || '我的球队'}</p>
                      <p className="text-xs text-[#BFA56B]">{nextMatch.isHome ? '主场' : '客场'}</p>
                    </div>
                    <div className="text-center">
                      <p className="font-pixel text-lg text-[#FFE2A1]">VS</p>
                      <p className="mt-1 text-[10px] font-black text-[#8A6B34]">赛程</p>
                    </div>
                    <div className="min-w-0 text-center">
                      <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center border-2 border-[#6B4C25] bg-[#07080A]">
                        <Trophy className="h-6 w-6 text-[#D7A94A]" />
                      </div>
                      <p className="truncate text-sm font-bold text-[#F7E9C6]">{nextMatch.opponent}</p>
                      <p className="text-xs text-[#BFA56B]">{nextMatch.isHome ? '客场' : '主场'}</p>
                    </div>
                  </div>
                </div>
                <Link to="/match/pre" className="btn-primary mt-3 flex w-full items-center justify-center gap-2 py-2.5">
                  <Swords className="h-4 w-4" />
                  赛前准备
                </Link>
              </>
            ) : (
              <div className="empty-line amber">暂无比赛安排。</div>
            )}
          </section>

          <section className="result-ledger">
            <div className="console-heading">
              <h2 className="text-lg font-black text-[#E8EAD8]">最近比赛</h2>
              <Link to="/match/schedule" className="console-link">赛程表</Link>
            </div>
            {loading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((item) => (
                  <div key={item} className="h-10 animate-pulse border-2 border-[#242832] bg-[#11141A]" />
                ))}
              </div>
            ) : recentMatches.length > 0 ? (
              <div>
                {recentMatches.slice(0, 4).map((match, index) => (
                  <RecentMatchRow key={`${match.opponent}-${index}`} match={match} />
                ))}
              </div>
            ) : (
              <div className="empty-line">还没有可展示的比赛记录。</div>
            )}
          </section>
        </aside>

        <nav className="quick-rail">
          <h2 className="text-base font-black text-[#E8EAD8]">快速前往</h2>
          <div className="quick-rail-links">
            {[
              { label: '战术板', to: '/team/tactics', icon: Target },
              { label: '更衣室', to: '/team/players', icon: Users },
              { label: '联赛', to: leagueId ? `/leagues/${leagueId}` : '/leagues', icon: Trophy },
              { label: '转会市场', to: '/transfer', icon: Wallet },
            ].map((item) => (
              <Link key={item.label} to={item.to} className="quick-dock-key">
                <item.icon className="h-4 w-4 text-[#CDEB7B]" />
                {item.label}
              </Link>
            ))}
          </div>
        </nav>
      </section>
    </div>
  )
}

export default Dashboard
