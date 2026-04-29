import { useEffect, useState } from 'react'
import { 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Calendar,
  ChevronRight,
  Target,
  Shield,
  Zap,
  Trophy,
  Users,
  Swords,
  ArrowUpRight,
  Clock
} from 'lucide-react'
import { Link } from 'react-router-dom'
import api from '../../api/client'
import { useAuthStore } from '../../stores/auth'
import type { League } from '../../types/league'

// 球队类型定义
interface Team {
  id: string
  name: string
  short_name?: string
  overall_rating: number
  attack: number
  midfield: number
  defense: number
  league_id?: string
  league_name?: string
}

// Dashboard 统计数据
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

// 近期比赛结果
interface RecentMatch {
  opponent: string
  opponent_id: string
  result: 'W' | 'D' | 'L'
  score: string
  date: string
  is_home: boolean
}

// 数据卡片组件
function StatCard({ 
  label, 
  value, 
  subtext, 
  trend,
  trendValue,
  icon: Icon
}: { 
  label: string
  value: string
  subtext: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
  icon?: React.ElementType
}) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-[#4B4B6A]'

  return (
    <div className="card card-hover">
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            {Icon && <Icon className="w-4 h-4 text-[#0D7377]" />}
            <p className="text-sm text-[#8B8BA7]">{label}</p>
          </div>
          <p className="text-3xl font-bold pixel-number text-white">{value}</p>
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
            <TrendIcon className="w-3 h-3" />
            <span>{trendValue}</span>
          </div>
        )}
      </div>
      <p className="text-xs text-[#4B4B6A] mt-2">{subtext}</p>
    </div>
  )
}

// 快捷操作卡片
function QuickAction({ icon: Icon, label, desc, to }: { icon: any, label: string, desc: string, to: string }) {
  return (
    <Link 
      to={to}
      className="flex items-center gap-4 p-4 bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-sm hover:border-[#0D7377]/50 transition-all duration-200 group hover:-translate-x-0.5 hover:-translate-y-0.5"
    >
      <div className="w-10 h-10 bg-[#0D4A4D]/40 border-2 border-[#0D7377]/30 flex items-center justify-center flex-shrink-0">
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white group-hover:text-[#0D7377] transition-colors">{label}</p>
        <p className="text-xs text-[#4B4B6A] truncate">{desc}</p>
      </div>
      <ChevronRight className="w-4 h-4 text-[#4B4B6A] group-hover:text-white transition-colors" />
    </Link>
  )
}

// 比赛记录
function MatchResult({ opponent, result, score, date, is_home }: { 
  opponent: string, 
  result: 'W' | 'D' | 'L', 
  score: string, 
  date: string,
  is_home: boolean
}) {
  const resultConfig = {
    W: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: '胜' },
    D: { bg: 'bg-[#2D2D44]', text: 'text-[#8B8BA7]', label: '平' },
    L: { bg: 'bg-red-500/20', text: 'text-red-400', label: '负' },
  }
  const config = resultConfig[result]

  return (
    <div className="flex items-center gap-4 py-3 border-b-2 border-[#2D2D44] last:border-0">
      <div className={`w-8 h-8 ${config.bg} border-2 border-transparent flex items-center justify-center text-xs font-bold ${config.text}`}>
        {config.label}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">
          {is_home ? 'vs ' : '@ '}{opponent}
        </p>
        <p className="text-xs text-[#4B4B6A]">{date}</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-bold stat-number">{score}</p>
      </div>
    </div>
  )
}

// 近期状态
function FormIndicator({ form }: { form: string }) {
  if (!form) return <div className="text-xs text-[#4B4B6A]">暂无数据</div>
  
  return (
    <div className="flex items-center gap-1">
      {form.split('').map((result, idx) => {
        const colors = {
          'W': 'bg-emerald-500',
          'D': 'bg-[#4B4B6A]',
          'L': 'bg-red-500'
        }
        return (
          <div 
            key={idx} 
            className={`w-5 h-5 ${colors[result as keyof typeof colors]} border-2 border-transparent flex items-center justify-center text-[10px] font-bold text-white`}
          >
            {result}
          </div>
        )
      })}
    </div>
  )
}

// 联赛卡片
function LeagueCard({ league }: { league: League }) {
  const levelNames = ['超级联赛', '甲级联赛', '乙级联赛A', '乙级联赛B']
  
  return (
    <Link 
      to={`/leagues/${league.id}`}
      className={`block p-4 bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-sm hover:scale-[1.02] transition-transform duration-200`}
    >
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-white">{league.name}</h4>
          <p className="text-xs text-[#8B8BA7] mt-1">{league.teams_count} 支球队</p>
        </div>
        <div className="w-10 h-10 bg-[#12121A]/60 border-2 border-transparent flex items-center justify-center">
          <Trophy className="w-5 h-5 text-[#0D7377]" />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs px-2 py-0.5 -none bg-[#12121A]/60 text-[#8B8BA7]">
          {league.system_name}
        </span>
        <span className="text-xs px-2 py-0.5 -none bg-[#12121A]/60 text-[#8B8BA7]">
          {levelNames[league.level - 1]}
        </span>
      </div>
    </Link>
  )
}

function Dashboard() {
  const [leagues, setLeagues] = useState<League[]>([])
  const [team, setTeam] = useState<Team | null>(null)
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [recentMatches, setRecentMatches] = useState<RecentMatch[]>([])
  const [loading, setLoading] = useState(true)
  const user = useAuthStore((state) => state.user)

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true)
        
        // 获取联赛列表
        const leaguesResponse = await api.get<League[]>('/leagues')
        if (leaguesResponse.success) {
          const topLeagues = leaguesResponse.data.filter(l => l.level === 1).slice(0, 4)
          setLeagues(topLeagues)
        }

        // 获取当前用户的球队
        const teamResponse = await api.get<Team>('/teams/my-team')
        if (teamResponse.success) {
          setTeam(teamResponse.data)
          
          // 获取 Dashboard 统计数据
          const statsResponse = await api.get<DashboardStats>('/teams/my-team/dashboard')
          if (statsResponse.success) {
            setStats(statsResponse.data)
            
            // 获取最近比赛详情
            if (statsResponse.data.recent_form) {
              await fetchRecentMatches(teamResponse.data.id)
            }
          }
        }
      } catch (error) {
        console.error('Failed to fetch data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [])

  // 获取最近比赛详情
  const fetchRecentMatches = async (teamId: string) => {
    try {
      // 获取当前赛季
      const seasonResponse = await api.get('/seasons/current')
      if (!seasonResponse.success) return
      
      const seasonNumber = (seasonResponse.data as { season_number?: number })?.season_number
      if (!seasonNumber) return
      
      // 获取球队赛程
      const fixturesResponse = await api.get(`/seasons/${seasonNumber}/teams/${teamId}/fixtures?limit=5`)
      if (!fixturesResponse.success) return
      
      const fixtures = (fixturesResponse.data as { fixtures?: unknown[] })?.fixtures || []
      
      // 过滤已完成的比赛并格式化
      const completed = fixtures
        .filter((f: any) => f.status === 'finished')
        .slice(0, 5)
        .map((f: any) => {
          const isHome = f.home_team_id === teamId
          const myScore = isHome ? f.home_score : f.away_score
          const oppScore = isHome ? f.away_score : f.home_score
          const opponent = isHome ? f.away_team_name : f.home_team_name
          
          let result: 'W' | 'D' | 'L'
          if (myScore > oppScore) result = 'W'
          else if (myScore < oppScore) result = 'L'
          else result = 'D'
          
          return {
            opponent,
            opponent_id: isHome ? f.away_team_id : f.home_team_id,
            result,
            score: `${myScore}:${oppScore}`,
            date: `Day ${f.season_day}`,
            is_home: isHome
          }
        })
      
      setRecentMatches(completed.reverse()) // 最新的在前面
    } catch (error) {
      console.error('Failed to fetch recent matches:', error)
    }
  }

  // 如果没有获取到球队，使用占位数据
  const displayTeam: Team = team || {
    id: '1',
    name: user?.nickname || '我的球队',
    overall_rating: 50,
    attack: 50,
    midfield: 50,
    defense: 50,
    league_id: undefined,
    league_name: undefined,
  }

  // 使用真实统计数据
  const league_position = stats?.league_position ?? '-'
  const points = stats?.points ?? 0
  const played = stats?.played ?? 0
  const won = stats?.won ?? 0
  const drawn = stats?.drawn ?? 0
  const lost = stats?.lost ?? 0
  const goals_for = stats?.goals_for ?? 0
  const goals_against = stats?.goals_against ?? 0
  const goal_diff = stats?.goal_difference ?? 0
  const form = stats?.recent_form ?? ''
  
  const next_match = stats?.next_match ? {
    opponent: stats.next_match.opponent_name,
    opponent_id: stats.next_match.opponent_id,
    is_home: stats.next_match.is_home,
    date: `Day ${stats.next_match.day}`,
    time: '20:00'
  } : null

  // 计算胜率趋势
  const winRate = played > 0 ? Math.round((won / played) * 100) : 0
  const trend = winRate >= 50 ? 'up' : winRate >= 30 ? 'neutral' : 'down'

  return (
    <div className="space-y-6 max-w-[1600px]">
      {/* 欢迎区域 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">欢迎回来，{user?.nickname || '经理'}</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">以下是您球队的最新概况</p>
        </div>
        <Link 
          to="/match/schedule"
          className="btn-primary flex items-center gap-2"
        >
          <Calendar className="w-4 h-4" />
          下一场比赛
        </Link>
      </div>

      {/* 数据概览 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          label="联赛排名" 
          value={`#${league_position}`}
          subtext={`${points} 积分 · ${played} 场次`}
          trend={trend as any}
          trendValue={league_position && typeof league_position === 'number' && league_position <= 3 ? "上游" : league_position && typeof league_position === 'number' && league_position >= 6 ? "下游" : "中游"}
          icon={Trophy}
        />
        <StatCard 
          label="本赛季战绩" 
          value={`${won}-${drawn}-${lost}`}
          subtext="胜 - 平 - 负"
          trend={trend as any}
          trendValue={`${winRate}%`}
          icon={Swords}
        />
        <StatCard 
          label="球队总评" 
          value={displayTeam.overall_rating?.toString() || '-'}
          subtext={`进攻 ${displayTeam.attack || '-'} · 防守 ${displayTeam.defense || '-'}`}
          trend="neutral"
          trendValue="-"
          icon={Zap}
        />
        <StatCard 
          label="净胜球" 
          value={goal_diff >= 0 ? `+${goal_diff}` : `${goal_diff}`}
          subtext={`${goals_for} 进球 · ${goals_against} 失球`}
          trend={goal_diff > 0 ? 'up' : goal_diff < 0 ? 'down' : 'neutral'}
          trendValue={goal_diff > 0 ? "+" : goal_diff < 0 ? "-" : "="}
          icon={Target}
        />
      </div>

      {/* 主内容区 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧 - 球队概览和比赛 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 球队信息卡 */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">我的球队</h3>
              <Link 
                to="/team/players"
                className="text-sm text-[#0D7377] hover:text-white transition-colors"
              >
                查看详情 →
              </Link>
            </div>
            
            <div className="flex items-center gap-6 pb-6 border-b-2 border-[#2D2D44]">
              <div className="w-20 h-20 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center shadow-pixel shadow-[#0D7377]/20">
                <span className="text-3xl">🐉</span>
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold">{displayTeam.name}</h2>
                <p className="text-sm text-[#8B8BA7] mt-1">{displayTeam.league_name || '暂无联赛'}</p>
                <div className="flex items-center gap-4 mt-3">
                  <div className="flex items-center gap-1.5 text-sm">
                    <Target className="w-4 h-4 text-red-400" />
                    <span>进攻 {displayTeam.attack || '-'}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Zap className="w-4 h-4 text-[#0D7377]" />
                    <span>中场 {displayTeam.midfield || '-'}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Shield className="w-4 h-4 text-emerald-400" />
                    <span>防守 {displayTeam.defense || '-'}</span>
                  </div>
                </div>
              </div>
              <div className="hidden md:block">
                <p className="text-xs text-[#8B8BA7] mb-2">近期状态</p>
                <FormIndicator form={form} />
              </div>
            </div>

            {/* 能力条 */}
            <div className="grid grid-cols-3 gap-6 pt-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">进攻</span>
                  <span className="text-sm font-medium stat-number">{displayTeam.attack || '-'}</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] -none overflow-hidden">
                  <div className="h-full bg-red-500 -none" style={{ width: `${displayTeam.attack || 0}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">中场</span>
                  <span className="text-sm font-medium stat-number">{displayTeam.midfield || '-'}</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] -none overflow-hidden">
                  <div className="h-full bg-[#0D7377] -none" style={{ width: `${displayTeam.midfield || 0}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">防守</span>
                  <span className="text-sm font-medium stat-number">{displayTeam.defense || '-'}</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] -none overflow-hidden">
                  <div className="h-full bg-emerald-500 -none" style={{ width: `${displayTeam.defense || 0}%` }} />
                </div>
              </div>
            </div>
          </div>

          {/* 热门联赛 */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">热门联赛</h3>
              <Link 
                to="/leagues"
                className="text-sm text-[#0D7377] hover:text-white transition-colors flex items-center gap-1"
              >
                查看全部 <ArrowUpRight className="w-3 h-3" />
              </Link>
            </div>
            {loading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="h-24 bg-[#1E1E2D] animate-pulse" />
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {leagues.map(league => (
                  <LeagueCard key={league.id} league={league} />
                ))}
              </div>
            )}
          </div>

          {/* 最近比赛 */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">最近比赛</h3>
              <Link 
                to="/match/schedule"
                className="text-sm text-[#8B8BA7] hover:text-white transition-colors"
              >
                查看全部
              </Link>
            </div>
            <div>
              {recentMatches.length > 0 ? (
                recentMatches.map((match, idx) => (
                  <MatchResult 
                    key={idx}
                    opponent={match.opponent}
                    result={match.result}
                    score={match.score}
                    date={match.date}
                    is_home={match.is_home}
                  />
                ))
              ) : (
                <div className="text-center py-8 text-[#4B4B6A]">
                  <p>暂无比赛记录</p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* 右侧 - 快捷操作和下场比赛 */}
        <div className="space-y-6">
          {/* 下场比赛预告 */}
          <div className="card bg-[#0D4A4D]/30 border-[#0D7377]/30">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-4 h-4 text-[#0D7377]" />
              <span className="text-sm text-[#8B8BA7]">下场比赛</span>
            </div>
            {next_match ? (
              <>
                <div className="flex items-center justify-between">
                  <div className="text-center flex-1">
                    <div className="w-14 h-14 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
                      <span className="text-2xl">🐉</span>
                    </div>
                    <p className="text-sm font-medium truncate">{displayTeam.name}</p>
                    <p className="text-xs text-[#8B8BA7]">{next_match.is_home ? '主' : '客'}</p>
                  </div>
                  <div className="text-center px-4">
                    <p className="text-2xl font-bold stat-number text-[#0D7377]">VS</p>
                    <p className="text-xs text-[#4B4B6A] mt-1">{next_match.date}</p>
                    <p className="text-xs text-[#0D7377]">{next_match.time}</p>
                  </div>
                  <div className="text-center flex-1">
                    <div className="w-14 h-14 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
                      <span className="text-2xl">🌊</span>
                    </div>
                    <p className="text-sm font-medium truncate">{next_match.opponent}</p>
                    <p className="text-xs text-[#8B8BA7]">{next_match.is_home ? '客' : '主'}</p>
                  </div>
                </div>
                <div className="mt-4 pt-4 border-t-2 border-[#2D2D44]">
                  <Link 
                    to="/match/pre"
                    className="btn-primary w-full flex items-center justify-center gap-2"
                  >
                    <Swords className="w-4 h-4" />
                    赛前准备
                  </Link>
                </div>
              </>
            ) : (
              <div className="text-center py-8 text-[#4B4B6A]">
                <p>暂无安排</p>
              </div>
            )}
          </div>

          {/* 快捷操作 */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">快捷操作</h3>
            <div className="space-y-3">
              <QuickAction 
                icon={Target} 
                label="设置战术" 
                desc="调整阵型和球员指令"
                to="/team/tactics"
              />
              <QuickAction 
                icon={Users} 
                label="阵容调整" 
                desc="首发11人和替补名单"
                to="/team/players"
              />
              <QuickAction 
                icon={Trophy} 
                label="查看排名" 
                desc={displayTeam.league_id ? "联赛积分榜和射手榜" : "请先加入联赛"}
                to={displayTeam.league_id ? `/leagues/${displayTeam.league_id}` : '/leagues'}
              />
              <QuickAction 
                icon={Calendar} 
                label="赛程安排" 
                desc=" upcoming matches"
                to="/match/schedule"
              />
            </div>
          </div>

          {/* 最新动态 */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">最新动态</h3>
            <div className="space-y-4">
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-emerald-500/20 border-2 border-transparent flex items-center justify-center flex-shrink-0">
                  <Trophy className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm text-[#E2E2F0]">球队在主场 3:1 战胜紫电龙骑</p>
                  <p className="text-xs text-[#4B4B6A] mt-0.5">2小时前</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-blue-500/20 border-2 border-transparent flex items-center justify-center flex-shrink-0">
                  <Users className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-[#E2E2F0]">年轻球员李伟能力值 +3</p>
                  <p className="text-xs text-[#4B4B6A] mt-0.5">5小时前</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 bg-amber-500/20 border-2 border-transparent flex items-center justify-center flex-shrink-0">
                  <Calendar className="w-4 h-4 text-amber-400" />
                </div>
                <div>
                  <p className="text-sm text-[#E2E2F0]">下轮对阵南海蛟龙的门票已售罄</p>
                  <p className="text-xs text-[#4B4B6A] mt-0.5">1天前</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
