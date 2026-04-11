import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  Trophy, 
  ChevronLeft, 
  Users,
  Target,
  ArrowUpRight,
  Calendar,
  TrendingUp,
  List
} from 'lucide-react'
import { useLeagueDetail, useLeagueTable, useLeagueSchedule, useTopScorers, useTopAssists } from '../../hooks/useLeagues'
import type { LeagueStanding, Match } from '../../types/league'

// Tab 按钮组件
function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={`px-4 py-2 rounded-lg font-medium text-sm transition-all duration-200 ${
        active
          ? 'bg-[#0D7377] text-white shadow-lg shadow-[#0D7377]/25'
          : 'text-[#8B8BA7] hover:text-white hover:bg-[#1E1E2D]'
      }`}
    >
      {children}
    </button>
  )
}

// 积分榜行组件
function StandingRow({ standing }: { standing: LeagueStanding }) {
  const isChampion = standing.position === 1
  const isPromotion = standing.is_promotion_zone
  const isRelegation = standing.is_relegation_zone
  
  let rowClass = 'hover:bg-[#1E1E2D]/50 transition-colors'
  if (isChampion) rowClass += ' bg-amber-500/5'
  else if (isPromotion) rowClass += ' bg-emerald-500/5'
  else if (isRelegation) rowClass += ' bg-red-500/5'
  
  return (
    <tr className={`border-b border-[#2D2D44] ${rowClass}`}>
      <td className="py-3 px-4">
        <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold ${
          isChampion ? 'bg-amber-500 text-black' :
          isPromotion ? 'bg-emerald-500 text-white' :
          isRelegation ? 'bg-red-500 text-white' :
          'bg-[#1E1E2D] text-[#8B8BA7]'
        }`}>
          {standing.position}
        </div>
      </td>
      <td className="py-3 px-4">
        <Link 
          to={`/teams/${standing.team.id}`}
          className="font-medium text-white hover:text-[#0D7377] transition-colors"
        >
          {standing.team.name}
        </Link>
      </td>
      <td className="py-3 px-4 text-center stat-number">{standing.played}</td>
      <td className="py-3 px-4 text-center stat-number text-emerald-400">{standing.won}</td>
      <td className="py-3 px-4 text-center stat-number text-[#8B8BA7]">{standing.drawn}</td>
      <td className="py-3 px-4 text-center stat-number text-red-400">{standing.lost}</td>
      <td className="py-3 px-4 text-center stat-number">{standing.goals_for}:{standing.goals_against}</td>
      <td className="py-3 px-4 text-center stat-number">{standing.goal_difference > 0 ? '+' : ''}{standing.goal_difference}</td>
      <td className="py-3 px-4 text-center">
        <span className="font-bold stat-number text-lg">{standing.points}</span>
      </td>
      <td className="py-3 px-4">
        {standing.form && (
          <div className="flex items-center gap-1">
            {standing.form.split('').map((result, idx) => {
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
        )}
      </td>
    </tr>
  )
}

// 比赛卡片组件
function MatchCard({ match }: { match: Match }) {
  const isFinished = match.status === 'finished'
  const isLive = match.status === 'ongoing'
  
  return (
    <div className="p-4 rounded-xl bg-[#12121A] border border-[#2D2D44] hover:border-[#0D7377]/30 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <span className="text-xs text-[#8B8BA7]">第 {match.matchday} 轮</span>
        {isLive && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-red-500 text-white animate-pulse">
            进行中
          </span>
        )}
        {isFinished && (
          <span className="text-xs px-2 py-0.5 rounded-full bg-[#1E1E2D] text-[#8B8BA7]">
            已结束
          </span>
        )}
      </div>
      
      <div className="flex items-center justify-between">
        <div className="flex-1 text-center">
          <p className="font-medium text-white">{match.home_team.name}</p>
          <p className="text-xs text-[#8B8BA7]">主</p>
        </div>
        
        <div className="px-4">
          {isFinished || isLive ? (
            <div className="text-2xl font-bold stat-number">
              <span className={isLive ? 'text-red-400' : 'text-white'}>
                {match.home_score}
              </span>
              <span className="text-[#4B4B6A] mx-2">:</span>
              <span className={isLive ? 'text-red-400' : 'text-white'}>
                {match.away_score}
              </span>
            </div>
          ) : (
            <div className="text-lg font-bold text-[#4B4B6A]">VS</div>
          )}
          <p className="text-xs text-[#8B8BA7] mt-1">
            {new Date(match.scheduled_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
          </p>
        </div>
        
        <div className="flex-1 text-center">
          <p className="font-medium text-white">{match.away_team.name}</p>
          <p className="text-xs text-[#8B8BA7]">客</p>
        </div>
      </div>
    </div>
  )
}

// 射手榜/助攻榜行组件
function StatsRow({ rank, name, team, value, label }: { rank: number; name: string; team: string; value: number; label: string }) {
  const rankColors = [
    'bg-amber-500 text-black',
    'bg-slate-300 text-black',
    'bg-orange-400 text-black',
    'bg-[#1E1E2D] text-[#8B8BA7]'
  ]
  
  return (
    <div className="flex items-center gap-4 py-3 border-b border-[#2D2D44] last:border-0">
      <div className={`w-7 h-7 rounded-lg flex items-center justify-center text-sm font-bold ${rankColors[Math.min(rank - 1, 3)]}`}>
        {rank}
      </div>
      <div className="flex-1 min-w-0">
        <p className="font-medium text-white truncate">{name}</p>
        <p className="text-xs text-[#8B8BA7]">{team}</p>
      </div>
      <div className="text-right">
        <p className="font-bold stat-number text-lg">{value}</p>
        <p className="text-xs text-[#8B8BA7]">{label}</p>
      </div>
    </div>
  )
}

function LeagueDetail() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<'standings' | 'schedule' | 'scorers' | 'assists'>('standings')
  
  const { league, loading: leagueLoading, error: leagueError } = useLeagueDetail(id)
  const { standings, loading: standingsLoading } = useLeagueTable(id)
  const { matches, loading: matchesLoading } = useLeagueSchedule(id)
  const { scorers, loading: scorersLoading } = useTopScorers(id, 10)
  const { assists, loading: assistsLoading } = useTopAssists(id, 10)
  
  if (leagueLoading) {
    return (
      <div className="max-w-[1200px]">
        <div className="h-8 w-32 rounded bg-[#1E1E2D] animate-pulse mb-4" />
        <div className="h-48 rounded-xl bg-[#1E1E2D] animate-pulse" />
      </div>
    )
  }
  
  if (!league) {
    return (
      <div className="max-w-[1200px] text-center py-20">
        <Trophy className="w-16 h-16 text-[#4B4B6A] mx-auto mb-4" />
        <h2 className="text-xl font-bold text-white mb-2">联赛未找到</h2>
        <p className="text-[#8B8BA7] mb-2">该联赛不存在或已被删除</p>
        {leagueError && (
          <p className="text-red-400 text-sm mb-6">错误: {leagueError}</p>
        )}
        <p className="text-[#4B4B6A] text-xs mb-6">联赛ID: {id || '未提供'}</p>
        <Link to="/leagues" className="btn-primary inline-flex items-center gap-2">
          <ChevronLeft className="w-4 h-4" />
          返回联赛列表
        </Link>
      </div>
    )
  }

  const levelNames = ['超级联赛', '甲级联赛', '乙级联赛A', '乙级联赛B']
  const levelColors = [
    'from-amber-500 to-yellow-400',
    'from-slate-300 to-slate-400',
    'from-orange-500 to-orange-600',
    'from-stone-400 to-stone-500'
  ]

  return (
    <div className="max-w-[1200px]">
      {/* 返回按钮和所有联赛链接 */}
      <div className="flex items-center justify-between mb-4">
        <Link 
          to="/dashboard"
          className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          返回首页
        </Link>
        <Link 
          to="/leagues/all"
          className="inline-flex items-center gap-1 text-sm text-[#0D7377] hover:text-white transition-colors"
        >
          <List className="w-4 h-4" />
          所有联赛
        </Link>
      </div>

      {/* 联赛信息头部 */}
      <div className="card mb-6 bg-gradient-to-br from-[#0D4A4D]/30 to-[#12121A]">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${levelColors[league.level - 1]} flex items-center justify-center text-3xl shadow-lg`}>
              {league.level === 1 ? '👑' : league.level === 2 ? '🥈' : league.level === 3 ? '🥉' : '🏅'}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">{league.name}</h1>
              <div className="flex items-center gap-3 mt-2">
                <span className="text-sm text-[#8B8BA7]">{league.system_name}</span>
                <span className="text-[#4B4B6A]">·</span>
                <span className="text-sm text-[#8B8BA7]">{levelNames[league.level - 1]}</span>
                {league.current_season && (
                  <>
                    <span className="text-[#4B4B6A]">·</span>
                    <span className="text-sm text-[#0D7377]">{league.current_season.name}</span>
                  </>
                )}
              </div>
            </div>
          </div>
          <div className="text-right hidden md:block">
            <div className="flex items-center gap-4 text-sm">
              <div className="flex items-center gap-1.5">
                <Users className="w-4 h-4 text-[#8B8BA7]" />
                <span className="text-[#8B8BA7]">{league.teams_count} 支球队</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4 text-[#8B8BA7]" />
                <span className="text-[#8B8BA7]">30 轮</span>
              </div>
            </div>
            {league.current_season && (
              <p className="text-xs text-[#4B4B6A] mt-2">
                赛季时间: {new Date(league.current_season.start_date).toLocaleDateString('zh-CN')}
                {league.current_season.end_date && ` - ${new Date(league.current_season.end_date).toLocaleDateString('zh-CN')}`}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Tab 导航 */}
      <div className="flex flex-wrap gap-2 mb-6">
        <TabButton active={activeTab === 'standings'} onClick={() => setActiveTab('standings')}>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4" />
            积分榜
          </div>
        </TabButton>
        <TabButton active={activeTab === 'schedule'} onClick={() => setActiveTab('schedule')}>
          <div className="flex items-center gap-2">
            <Calendar className="w-4 h-4" />
            赛程
          </div>
        </TabButton>
        <TabButton active={activeTab === 'scorers'} onClick={() => setActiveTab('scorers')}>
          <div className="flex items-center gap-2">
            <Target className="w-4 h-4" />
            射手榜
          </div>
        </TabButton>
        <TabButton active={activeTab === 'assists'} onClick={() => setActiveTab('assists')}>
          <div className="flex items-center gap-2">
            <ArrowUpRight className="w-4 h-4" />
            助攻榜
          </div>
        </TabButton>
      </div>

      {/* Tab 内容 */}
      <div className="card">
        {activeTab === 'standings' && (
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">积分榜</h3>
              <div className="flex items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded bg-amber-500" />
                  <span className="text-[#8B8BA7]">冠军</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded bg-emerald-500" />
                  <span className="text-[#8B8BA7]">升级区</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <div className="w-3 h-3 rounded bg-red-500" />
                  <span className="text-[#8B8BA7]">降级区</span>
                </div>
              </div>
            </div>
            
            {standingsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="h-12 rounded bg-[#1E1E2D] animate-pulse" />
                ))}
              </div>
            ) : standings.length === 0 ? (
              <div className="text-center py-12">
                <TrendingUp className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
                <p className="text-[#8B8BA7]">暂无积分数据</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="text-left text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
                      <th className="py-2 px-4 font-medium">排名</th>
                      <th className="py-2 px-4 font-medium">球队</th>
                      <th className="py-2 px-4 font-medium text-center">赛</th>
                      <th className="py-2 px-4 font-medium text-center">胜</th>
                      <th className="py-2 px-4 font-medium text-center">平</th>
                      <th className="py-2 px-4 font-medium text-center">负</th>
                      <th className="py-2 px-4 font-medium text-center">进/失</th>
                      <th className="py-2 px-4 font-medium text-center">净</th>
                      <th className="py-2 px-4 font-medium text-center">积分</th>
                      <th className="py-2 px-4 font-medium">状态</th>
                    </tr>
                  </thead>
                  <tbody>
                    {standings.map((standing) => (
                      <StandingRow key={standing.team.id} standing={standing} />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {activeTab === 'schedule' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">赛程安排</h3>
            {matchesLoading ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {[1, 2, 3, 4].map(i => (
                  <div key={i} className="h-32 rounded-xl bg-[#1E1E2D] animate-pulse" />
                ))}
              </div>
            ) : matches.length === 0 ? (
              <div className="text-center py-12">
                <Calendar className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
                <p className="text-[#8B8BA7]">暂无赛程数据</p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {matches.slice(0, 10).map(match => (
                  <MatchCard key={match.id} match={match} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'scorers' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">射手榜</h3>
            {scorersLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="h-14 rounded bg-[#1E1E2D] animate-pulse" />
                ))}
              </div>
            ) : scorers.length === 0 ? (
              <div className="text-center py-12">
                <Target className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
                <p className="text-[#8B8BA7]">暂无射手数据</p>
              </div>
            ) : (
              <div>
                {scorers.map(scorer => (
                  <StatsRow 
                    key={scorer.player_id}
                    rank={scorer.rank}
                    name={scorer.player_name}
                    team={scorer.team_name}
                    value={scorer.goals}
                    label="进球"
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'assists' && (
          <div>
            <h3 className="text-lg font-semibold mb-4">助攻榜</h3>
            {assistsLoading ? (
              <div className="space-y-2">
                {[1, 2, 3, 4, 5].map(i => (
                  <div key={i} className="h-14 rounded bg-[#1E1E2D] animate-pulse" />
                ))}
              </div>
            ) : assists.length === 0 ? (
              <div className="text-center py-12">
                <ArrowUpRight className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
                <p className="text-[#8B8BA7]">暂无助攻数据</p>
              </div>
            ) : (
              <div>
                {assists.map(assist => (
                  <StatsRow 
                    key={assist.player_id}
                    rank={assist.rank}
                    name={assist.player_name}
                    team={assist.team_name}
                    value={assist.assists}
                    label="助攻"
                  />
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default LeagueDetail
