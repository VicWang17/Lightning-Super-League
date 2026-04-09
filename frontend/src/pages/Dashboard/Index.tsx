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
import type { League } from '../../types/league'

// Mock user team data - in real app, this would come from auth context or API
const MOCK_USER_TEAM = {
  id: '1',
  name: '东方巨龙',
  short_name: '巨龙',
  reputation: 1800,
  overall_rating: 72,
  attack: 74,
  midfield: 70,
  defense: 71,
  league_position: 3,
  points: 24,
  played: 11,
  won: 8,
  drawn: 0,
  lost: 3,
  goals_for: 26,
  goals_against: 14,
  form: 'WWDLW',
  league_id: '1', // 东区超级联赛
  next_match: {
    opponent: '南海蛟龙',
    is_home: true,
    date: '2天后',
    time: '20:00'
  }
}

// Mock recent matches
const MOCK_RECENT_MATCHES = [
  { opponent: '紫电龙骑', result: 'W' as const, score: '3:1', date: '2天前', is_home: true },
  { opponent: '青龙偃月', result: 'W' as const, score: '2:0', date: '5天前', is_home: false },
  { opponent: '北海苍龙', result: 'D' as const, score: '1:1', date: '1周前', is_home: true },
  { opponent: '赤龙焚天', result: 'W' as const, score: '4:2', date: '1周前', is_home: false },
  { opponent: '西海金龙', result: 'L' as const, score: '0:1', date: '2周前', is_home: true },
]

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
          <p className="text-3xl font-bold stat-number text-white">{value}</p>
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
      className="flex items-center gap-4 p-4 rounded-xl bg-[#12121A] border border-[#2D2D44] hover:border-[#0D7377]/50 transition-all duration-200 group"
    >
      <div className="w-10 h-10 rounded-lg bg-[#0D4A4D]/40 border border-[#0D7377]/30 flex items-center justify-center flex-shrink-0">
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
    <div className="flex items-center gap-4 py-3 border-b border-[#2D2D44] last:border-0">
      <div className={`w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center text-xs font-bold ${config.text}`}>
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
            className={`w-5 h-5 rounded ${colors[result as keyof typeof colors]} flex items-center justify-center text-[10px] font-bold text-white`}
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
  const levelColors = [
    'from-amber-500/20 to-amber-600/5 border-amber-500/30',
    'from-slate-400/20 to-slate-500/5 border-slate-400/30',
    'from-orange-600/20 to-orange-700/5 border-orange-600/30',
    'from-stone-500/20 to-stone-600/5 border-stone-500/30',
  ]
  
  const levelNames = ['超级联赛', '甲级联赛', '乙级联赛A', '乙级联赛B']
  
  return (
    <Link 
      to={`/leagues/${league.id}`}
      className={`block p-4 rounded-xl bg-gradient-to-br ${levelColors[league.level - 1]} border hover:scale-[1.02] transition-transform duration-200`}
    >
      <div className="flex items-center justify-between">
        <div>
          <h4 className="font-semibold text-white">{league.name}</h4>
          <p className="text-xs text-[#8B8BA7] mt-1">{league.teams_count} 支球队</p>
        </div>
        <div className="w-10 h-10 rounded-lg bg-[#12121A]/60 flex items-center justify-center">
          <Trophy className="w-5 h-5 text-[#0D7377]" />
        </div>
      </div>
      <div className="mt-3 flex items-center gap-2">
        <span className="text-xs px-2 py-0.5 rounded-full bg-[#12121A]/60 text-[#8B8BA7]">
          {league.system_name}
        </span>
        <span className="text-xs px-2 py-0.5 rounded-full bg-[#12121A]/60 text-[#8B8BA7]">
          {levelNames[league.level - 1]}
        </span>
      </div>
    </Link>
  )
}

function Dashboard() {
  const [leagues, setLeagues] = useState<League[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchLeagues = async () => {
      try {
        const response = await api.get<League[]>('/leagues')
        if (response.success) {
          // Only show top 4 leagues (one from each system, level 1)
          const topLeagues = response.data.filter(l => l.level === 1).slice(0, 4)
          setLeagues(topLeagues)
        }
      } catch (error) {
        console.error('Failed to fetch leagues:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchLeagues()
  }, [])

  const team = MOCK_USER_TEAM

  return (
    <div className="space-y-6 max-w-[1600px]">
      {/* 欢迎区域 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">欢迎回来，经理</h1>
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
          value={`#${team.league_position}`}
          subtext={`${team.points} 积分 · ${team.played} 场次`}
          trend="up"
          trendValue="↑ 2"
          icon={Trophy}
        />
        <StatCard 
          label="本赛季战绩" 
          value={`${team.won}-${team.drawn}-${team.lost}`}
          subtext="胜 - 平 - 负"
          trend="up"
          trendValue={`${Math.round((team.won / team.played) * 100)}%`}
          icon={Swords}
        />
        <StatCard 
          label="球队总评" 
          value={team.overall_rating.toString()}
          subtext={`进攻 ${team.attack} · 防守 ${team.defense}`}
          trend="neutral"
          trendValue="-"
          icon={Zap}
        />
        <StatCard 
          label="净胜球" 
          value={`+${team.goals_for - team.goals_against}`}
          subtext={`${team.goals_for} 进球 · ${team.goals_against} 失球`}
          trend="up"
          trendValue="+3"
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
            
            <div className="flex items-center gap-6 pb-6 border-b border-[#2D2D44]">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-[#0D7377] to-[#0A5A5D] border border-[#0D7377]/50 flex items-center justify-center shadow-lg shadow-[#0D7377]/20">
                <span className="text-3xl">🐉</span>
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold">{team.name}</h2>
                <p className="text-sm text-[#8B8BA7] mt-1">声望值 {team.reputation} · 东区超级联赛</p>
                <div className="flex items-center gap-4 mt-3">
                  <div className="flex items-center gap-1.5 text-sm">
                    <Target className="w-4 h-4 text-red-400" />
                    <span>进攻 {team.attack}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Zap className="w-4 h-4 text-[#0D7377]" />
                    <span>中场 {team.midfield}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Shield className="w-4 h-4 text-emerald-400" />
                    <span>防守 {team.defense}</span>
                  </div>
                </div>
              </div>
              <div className="hidden md:block">
                <p className="text-xs text-[#8B8BA7] mb-2">近期状态</p>
                <FormIndicator form={team.form} />
              </div>
            </div>

            {/* 能力条 */}
            <div className="grid grid-cols-3 gap-6 pt-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">进攻</span>
                  <span className="text-sm font-medium stat-number">{team.attack}</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-red-500 to-red-400 rounded-full" style={{ width: `${team.attack}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">中场</span>
                  <span className="text-sm font-medium stat-number">{team.midfield}</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-[#0D7377] to-[#14A085] rounded-full" style={{ width: `${team.midfield}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">防守</span>
                  <span className="text-sm font-medium stat-number">{team.defense}</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] rounded-full overflow-hidden">
                  <div className="h-full bg-gradient-to-r from-emerald-500 to-emerald-400 rounded-full" style={{ width: `${team.defense}%` }} />
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
                  <div key={i} className="h-24 rounded-xl bg-[#1E1E2D] animate-pulse" />
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
              {MOCK_RECENT_MATCHES.map((match, idx) => (
                <MatchResult 
                  key={idx}
                  opponent={match.opponent}
                  result={match.result}
                  score={match.score}
                  date={match.date}
                  is_home={match.is_home}
                />
              ))}
            </div>
          </div>
        </div>

        {/* 右侧 - 快捷操作和下场比赛 */}
        <div className="space-y-6">
          {/* 下场比赛预告 */}
          <div className="card bg-gradient-to-br from-[#0D4A4D]/30 to-[#12121A] border-[#0D7377]/30">
            <div className="flex items-center gap-2 mb-4">
              <Clock className="w-4 h-4 text-[#0D7377]" />
              <span className="text-sm text-[#8B8BA7]">下场比赛</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="text-center flex-1">
                <div className="w-14 h-14 rounded-xl bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
                  <span className="text-2xl">🐉</span>
                </div>
                <p className="text-sm font-medium truncate">{team.name}</p>
                <p className="text-xs text-[#8B8BA7]">主</p>
              </div>
              <div className="text-center px-4">
                <p className="text-2xl font-bold stat-number text-[#0D7377]">VS</p>
                <p className="text-xs text-[#4B4B6A] mt-1">{team.next_match.date}</p>
                <p className="text-xs text-[#0D7377]">{team.next_match.time}</p>
              </div>
              <div className="text-center flex-1">
                <div className="w-14 h-14 rounded-xl bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
                  <span className="text-2xl">🌊</span>
                </div>
                <p className="text-sm font-medium truncate">{team.next_match.opponent}</p>
                <p className="text-xs text-[#8B8BA7]">客</p>
              </div>
            </div>
            <div className="mt-4 pt-4 border-t border-[#2D2D44]">
              <Link 
                to="/match/pre"
                className="btn-primary w-full flex items-center justify-center gap-2"
              >
                <Swords className="w-4 h-4" />
                赛前准备
              </Link>
            </div>
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
                desc="联赛积分榜和射手榜"
                to={`/leagues/${team.league_id}`}
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
                <div className="w-8 h-8 rounded-lg bg-emerald-500/20 flex items-center justify-center flex-shrink-0">
                  <Trophy className="w-4 h-4 text-emerald-400" />
                </div>
                <div>
                  <p className="text-sm text-[#E2E2F0]">球队在主场 3:1 战胜紫电龙骑</p>
                  <p className="text-xs text-[#4B4B6A] mt-0.5">2小时前</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                  <Users className="w-4 h-4 text-blue-400" />
                </div>
                <div>
                  <p className="text-sm text-[#E2E2F0]">年轻球员李伟能力值 +3</p>
                  <p className="text-xs text-[#4B4B6A] mt-0.5">5小时前</p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="w-8 h-8 rounded-lg bg-amber-500/20 flex items-center justify-center flex-shrink-0">
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
