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

function FormIndicator({ form }: { form: string }) {
  if (!form) return <span className="text-[#6E7258]">暂无</span>

  const resultConfig = {
    W: 'bg-[#8FD14F] text-[#10220D]',
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
    default: 'border-[#56613D] bg-[#151A10] text-[#F1F4DF]',
    green: 'border-[#9FE84B] bg-[#203B16] text-[#F1FFC5]',
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
          <p className="truncate text-base font-black text-[#12160F]">{activity.name}</p>
          <span className="border-2 border-[#5E6B3B] bg-[#202A17] px-1.5 py-0.5 text-[10px] font-bold text-[#CDEB7B]">
            {activity.value}
          </span>
        </div>
        <p className="mt-1 text-xs font-bold text-[#536234]">{activity.role}</p>
        <p className="truncate text-xs text-[#333B25]">{activity.detail}</p>
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
            : 'border-[#5E6B3B] bg-[#202A17] text-[#CDEB7B]'
        }`}
      >
        <Icon className="h-5 w-5" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-black text-[#15170E]">{title}</p>
        <p className="truncate text-xs font-medium text-[#4A4630]">{detail}</p>
      </div>
      <ChevronRight className="h-4 w-4 shrink-0 text-[#5C5B3A] group-hover:text-[#15170E]" />
    </Link>
  )
}

function RecentMatchRow({ match }: { match: RecentMatch }) {
  const config = {
    W: 'bg-[#8FD14F] text-[#10220D]',
    D: 'bg-[#5E6472] text-white',
    L: 'bg-[#D75A4A] text-white',
  }[match.result]

  return (
    <div className="match-stub">
      <span className={`flex h-8 w-8 items-center justify-center border-2 border-black/40 text-xs font-bold ${config}`}>
        {match.result === 'W' ? '胜' : match.result === 'D' ? '平' : '负'}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-[#F1F4DF]">
          {match.is_home ? '主场' : '客场'} {match.opponent}
        </p>
        <p className="text-xs text-[#737B5B]">{match.date}</p>
      </div>
      <p className="font-mono text-sm font-black text-[#F1F4DF]">{match.score}</p>
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
              opponent: isHome ? fixture.away_team_name : fixture.home_team_name,
              result: myScore > opponentScore ? 'W' : myScore < opponentScore ? 'L' : 'D',
              score: `${myScore}:${opponentScore}`,
              date: `Day ${fixture.season_day}`,
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
        date: `Day ${stats.next_match.day}`,
        type: stats.next_match.fixture_type || '联赛',
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
        className="manager-hero pixel-panel relative min-h-[440px] overflow-hidden border-[#3F4A2E] bg-[#10140E]"
        style={{ backgroundImage: "url('/dashboard/manager-office-training-v1.png')" }}
      >
        <div className="absolute inset-0 bg-gradient-to-r from-[#090B08] via-[#090B08]/78 to-[#090B08]/20" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#090B08] via-transparent to-[#090B08]/45" />
        <div className="relative z-10 grid min-h-[440px] gap-5 p-5 lg:grid-cols-[1.15fr_0.85fr] lg:p-7">
          <div className="flex max-w-3xl flex-col justify-between">
            <div>
              <div className="mb-4 inline-flex items-center gap-2 border-2 border-[#8FD14F] bg-[#172412] px-3 py-1.5 text-xs font-bold text-[#DFFFB4]">
                <span className="h-2 w-2 bg-[#8FD14F]" />
                {currentActivity.eyebrow}
              </div>
              <h1 className="max-w-2xl text-3xl font-black leading-tight text-[#F4F7DF] sm:text-4xl lg:text-5xl">
                {currentActivity.title}
              </h1>
              <p className="mt-4 max-w-xl text-sm leading-7 text-[#D1D6B8] sm:text-base">
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

      <section className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="space-y-5">
          <div className="coach-clipboard">
            <div className="clipboard-clip" />
            <div className="mb-5 flex items-center justify-between gap-3 border-b-2 border-[#47582E] pb-3">
              <div>
                <p className="text-xs font-black uppercase tracking-wider text-[#536234]">Training Ground</p>
                <h2 className="text-2xl font-black text-[#15170E]">球员正在干什么</h2>
              </div>
              <Link to="/training/weekly" className="border-2 border-[#536234] bg-[#202A17] px-3 py-2 text-sm font-black text-[#CDEB7B] hover:bg-[#C6F135] hover:text-[#0A0A0F]">
                训练计划
              </Link>
            </div>
            {playerActivities.length > 0 ? (
              <div className="grid gap-3 md:grid-cols-2">
                {playerActivities.map((activity) => (
                  <PlayerActivityRow key={activity.id} activity={activity} />
                ))}
              </div>
            ) : (
              <div className="border-2 border-dashed border-[#8A7B4A] bg-[#D8C98D] p-8 text-center font-bold text-[#5A5233]">
                后端暂未返回球员列表。
              </div>
            )}
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <div className="bulletin-board">
              <div className="board-title-strip">
                <h2 className="text-lg font-black text-[#F1F4DF]">经理待办</h2>
                <Mailbox className="h-5 w-5 text-[#CDEB7B]" />
              </div>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
                {taskItems.map((task) => (
                  <ManagerTask key={task.title} {...task} />
                ))}
              </div>
            </div>

            <div className="status-board">
              <div className="mb-5 flex items-center justify-between border-b-2 border-[#41513A] pb-3">
                <h2 className="text-lg font-black text-[#F1F4DF]">俱乐部状态</h2>
                <FormIndicator form={form} />
              </div>
              <div className="space-y-5">
                {[
                  { label: '综合', value: team?.overall_rating, color: 'bg-[#CDEB7B]' },
                  { label: '进攻', value: team?.attack, color: 'bg-[#D75A4A]' },
                  { label: '中场', value: team?.midfield, color: 'bg-[#D7A94A]' },
                  { label: '防守', value: team?.defense, color: 'bg-[#6EA8E5]' },
                ].map((item) => {
                  const value = typeof item.value === 'number' ? item.value : 0
                  return (
                  <div key={item.label} className="status-meter">
                    <div className="mb-2 flex items-center justify-between text-sm">
                      <span className="font-black text-[#D1D6B8]">{item.label}</span>
                      <span className="font-mono font-bold text-[#F1F4DF]">{typeof item.value === 'number' ? item.value : '-'}</span>
                    </div>
                    <div className="pixel-progress-track h-3 border-[#323A28] bg-[#070907]">
                      <div className={`pixel-progress-fill ${item.color}`} style={{ width: `${value}%` }} />
                    </div>
                  </div>
                  )
                })}
              </div>
            </div>
          </div>
        </div>

        <aside className="space-y-5">
          <div className="match-office border-2 border-[#6B4C25] bg-[#1A130B] p-5">
            <div className="mb-4 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-[#FFE2A1]" />
              <h2 className="text-lg font-black text-[#F7E9C6]">下一场比赛</h2>
              </div>
              <span className="ticket-serial">LSL-{stats?.next_match?.day || '---'}</span>
            </div>
            {nextMatch ? (
              <>
                <div className="match-ticket p-5">
                  <div className="mb-4 flex items-center justify-between border-b-2 border-[#6B4C25] pb-3">
                    <p className="text-xs font-black uppercase tracking-widest text-[#BFA56B]">{nextMatch.type}</p>
                    <p className="text-xs font-black text-[#BFA56B]">{nextMatch.date}</p>
                  </div>
                  <div className="mt-4 grid grid-cols-[1fr_auto_1fr] items-center gap-3">
                    <div className="min-w-0 text-center">
                      <div className="mx-auto mb-2 flex h-14 w-14 items-center justify-center border-2 border-[#6B4C25] bg-[#10140E]">
                        <Shield className="h-7 w-7 text-[#CDEB7B]" />
                      </div>
                      <p className="truncate text-sm font-bold text-[#F7E9C6]">{team?.short_name || team?.name || '我的球队'}</p>
                      <p className="text-xs text-[#BFA56B]">{nextMatch.isHome ? '主场' : '客场'}</p>
                    </div>
                    <div className="text-center">
                      <p className="font-pixel text-xl text-[#FFE2A1]">VS</p>
                      <p className="mt-2 text-[10px] font-black uppercase tracking-widest text-[#8A6B34]">Fixture</p>
                    </div>
                    <div className="min-w-0 text-center">
                      <div className="mx-auto mb-2 flex h-14 w-14 items-center justify-center border-2 border-[#6B4C25] bg-[#10140E]">
                        <Trophy className="h-7 w-7 text-[#D7A94A]" />
                      </div>
                      <p className="truncate text-sm font-bold text-[#F7E9C6]">{nextMatch.opponent}</p>
                      <p className="text-xs text-[#BFA56B]">{nextMatch.isHome ? '客场' : '主场'}</p>
                    </div>
                  </div>
                </div>
                <Link to="/match/pre" className="btn-primary mt-4 flex w-full items-center justify-center gap-2">
                  <Swords className="h-4 w-4" />
                  赛前准备
                </Link>
              </>
            ) : (
              <div className="ticket-empty border-2 border-dashed border-[#6B4C25] bg-[#120E09] p-6 text-center font-bold text-[#BFA56B]">
                暂无比赛安排，适合推进训练和阵容磨合。
              </div>
            )}
          </div>

          <div className="result-board">
            <div className="mb-4 flex items-center justify-between border-b-2 border-[#3F4A2E] pb-3">
              <h2 className="text-lg font-black text-[#F1F4DF]">最近比赛</h2>
              <Link to="/match/schedule" className="text-sm font-bold text-[#CDEB7B] hover:text-white">
                赛程表
              </Link>
            </div>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((item) => (
                  <div key={item} className="h-12 animate-pulse border-2 border-[#3F4A2E] bg-[#202A17]" />
                ))}
              </div>
            ) : recentMatches.length > 0 ? (
              <div>
                {recentMatches.map((match, index) => (
                  <RecentMatchRow key={`${match.opponent}-${index}`} match={match} />
                ))}
              </div>
            ) : (
              <div className="border-2 border-dashed border-[#3F4A2E] bg-[#0C100B] p-6 text-center font-bold text-[#737B5B]">
                还没有可展示的比赛记录。
              </div>
            )}
          </div>

          <div className="quick-dock">
            <h2 className="mb-4 border-b-2 border-[#3F4A2E] pb-3 text-lg font-black text-[#F1F4DF]">快速前往</h2>
            <div className="grid grid-cols-2 gap-3">
              {[
                { label: '战术板', to: '/team/tactics', icon: Target },
                { label: '更衣室', to: '/team/players', icon: Users },
                { label: '联赛大厅', to: leagueId ? `/leagues/${leagueId}` : '/leagues', icon: Trophy },
                { label: '转会市场', to: '/transfer', icon: Wallet },
              ].map((item) => (
                <Link
                  key={item.label}
                  to={item.to}
                  className="quick-dock-key"
                >
                  <item.icon className="h-4 w-4 text-[#CDEB7B]" />
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        </aside>
      </section>
    </div>
  )
}

export default Dashboard
