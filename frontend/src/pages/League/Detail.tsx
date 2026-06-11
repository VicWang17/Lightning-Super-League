import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { 
  Trophy, 
  ChevronLeft, 
  Target,
  Calendar,
  TrendingUp,
  Sword as Swords,
  Medal,
} from '../../components/ui/pixel-icons'
import { LeagueBadge } from '../../components/league/LeagueBadge'
import { api } from '../../api/client'
import { useLeagueDetail, useLeagueTable, useLeagueSchedule, useLeagueLeaderboard } from '../../hooks/useLeagues'
import { useLeagueAwards } from '../../hooks/useAwards'
import { AwardCard, DataKingsRow, TeamOfSeasonGrid } from '../../components/awards'
import { useSeasons } from '../../hooks/useSeasons'
import type { League, LeagueStanding, Match, PlayoffMatch } from '../../types/league'
import type { Season } from '../../types/season'
import type { LeaderboardType } from '../../types/leaderboard'
import { LeaderboardSidebar, getLeaderboardFormat } from '../../components/leaderboard/LeaderboardSidebar'
import { LeaderboardTable } from '../../components/leaderboard/LeaderboardTable'

// 图例组件 — 根据联赛赛制动态显示
function Legend({ league }: { league: League }) {
  const items: { color: string; label: string }[] = []

  // 冠军（所有联赛都有）
  items.push({ color: 'bg-amber-500', label: '冠军' })

  // 直升升级
  if (league.promotion_spots > 0) {
    items.push({ color: 'bg-emerald-500', label: '升级区' })
  }

  // 附加赛升级
  if (league.has_promotion_playoff) {
    items.push({ color: 'bg-sky-500', label: '附加赛' })
  }

  // 附加赛降级
  if (league.has_relegation_playoff) {
    items.push({ color: 'bg-orange-500', label: '附加赛' })
  }

  // 降级
  if (league.relegation_spots > 0) {
    items.push({ color: 'bg-red-500', label: '降级区' })
  }

  return (
    <div className="flex items-center gap-4 text-xs flex-wrap">
      {items.map((item) => (
        <div key={item.label + item.color} className="flex items-center gap-1.5">
          <div className={`w-3 h-3 ${item.color}`} />
          <span className="text-[#8B8BA7]">{item.label}</span>
        </div>
      ))}
    </div>
  )
}

// Tab 按钮组件
function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
 return (
 <button
 onClick={onClick}
 className={`px-4 py-2 font-medium text-sm transition-all duration-200 ${
 active
 ? 'bg-[#C6F135] text-[#0A0A0F] border-2 font-bold shadow-pixel shadow-[#C6F135]/25'
 : 'text-[#8B8BA7] hover:text-white hover:bg-[#1E1E2D] border-2 border-transparent'
 }`}
 >
 {children}
 </button>
 )
}

// 赛季选择器组件
function SeasonSelector({ 
 seasons, 
 selectedSeasonId, 
 onChange 
}: { 
 seasons: Season[]; 
 selectedSeasonId: string | undefined; 
 onChange: (seasonId: string) => void 
}) {
 return (
 <div className="relative">
 <select
 value={selectedSeasonId || ''}
 onChange={(e) => onChange(e.target.value)}
 className="appearance-none bg-[#1E1E2D] border-2 border-[#2D2D44] text-white text-sm px-4 py-2 pr-8 focus:outline-none focus:border-[#C6F135] focus:ring-1 focus:ring-[#C6F135] cursor-pointer"
 >
 {seasons.map((season) => (
 <option key={season.id} value={season.id}>
 第 {season.season_number} 赛季
 </option>
 ))}
 </select>
 <ChevronLeft className="w-4 h-4 text-[#8B8BA7] absolute right-2 top-1/2 -translate-y-1/2 rotate-[-90deg] pointer-events-none" />
 </div>
 )
}

// 根据赛制计算排名区域类型
// 规则来源: backend/scripts/init_system.py
type ZoneType = 'champion' | 'promotion' | 'promotion_playoff' | 'safe' | 'relegation_playoff' | 'relegation'

function getZoneType(position: number, league: League): ZoneType {
  const { promotion_spots, relegation_spots, has_promotion_playoff, has_relegation_playoff, max_teams } = league
  if (position === 1) return 'champion'
  if (promotion_spots > 0 && position <= promotion_spots) return 'promotion'
  if (has_promotion_playoff && position === promotion_spots + 1) return 'promotion_playoff'
  if (has_relegation_playoff && position === max_teams - relegation_spots) return 'relegation_playoff'
  if (relegation_spots > 0 && position > max_teams - relegation_spots) return 'relegation'
  return 'safe'
}

const zoneColors: Record<ZoneType, { bg: string; text: string; row: string; label: string }> = {
  champion: { bg: 'bg-amber-500', text: 'text-black', row: 'bg-amber-500/5', label: '冠军' },
  promotion: { bg: 'bg-emerald-500', text: 'text-white', row: 'bg-emerald-500/5', label: '升级区' },
  promotion_playoff: { bg: 'bg-sky-500', text: 'text-white', row: 'bg-sky-500/5', label: '附加赛' },
  safe: { bg: 'bg-[#1E1E2D]', text: 'text-[#8B8BA7]', row: '', label: '' },
  relegation_playoff: { bg: 'bg-orange-500', text: 'text-white', row: 'bg-orange-500/5', label: '附加赛' },
  relegation: { bg: 'bg-red-500', text: 'text-white', row: 'bg-red-500/5', label: '降级区' },
}

// 积分榜行组件
function StandingRow({ standing, league }: { standing: LeagueStanding; league: League }) {
  const zone = getZoneType(standing.position, league)
  const colors = zoneColors[zone]

  let rowClass = 'hover:bg-[#1E1E2D]/50 transition-colors'
  if (colors.row) rowClass += ' ' + colors.row

  return (
    <tr className={`border-b border-[#2D2D44] ${rowClass}`}>
      <td className="py-3 px-4">
        <div className={`w-7 h-7 flex items-center justify-center text-sm font-bold pixel-number ${colors.bg} ${colors.text}`}>
          {standing.position}
        </div>
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/teams/${standing.team.id}`}
          className="font-medium text-white hover:text-[#C6F135] transition-colors"
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
 <span className="font-bold pixel-number text-lg">{standing.points}</span>
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
 className={`w-5 h-5 ${colors[result as keyof typeof colors]} flex items-center justify-center text-[10px] font-bold text-white`}
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

// 附加赛卡片组件
function PlayoffCard({ playoff }: { playoff: PlayoffMatch }) {
 const isFinished = playoff.status === 'finished'
 const isLive = playoff.status === 'ongoing'

 return (
 <div className="p-3 bg-amber-500/10 border-2 border-amber-500/30 shadow-pixel-sm hover:-translate-y-1 transition-all">
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2">
 <Medal className="w-4 h-4 text-amber-400" />
 <span className="text-xs font-medium text-amber-400">{playoff.name}</span>
 </div>
 {isLive && (
 <span className="text-xs px-2 py-0.5 rounded-none bg-red-500 text-white animate-pulse">
 进行中
 </span>
 )}
 {isFinished && (
 <span className="text-xs px-2 py-0.5 rounded-none bg-[#1E1E2D] text-[#8B8BA7]">
 已结束
 </span>
 )}
 </div>

 <div className="flex items-center justify-between">
 <div className="flex-1 text-center">
 <Link
 to={`/teams/${playoff.home_team.id}`}
 className="font-medium text-white text-sm hover:text-[#C6F135] transition-colors"
 >
 {playoff.home_team.name}
 </Link>
 </div>

 <div className="px-3 text-center">
 {isFinished || isLive ? (
 <div className="text-xl font-bold pixel-number">
 <span className={isLive ? 'text-red-400' : 'text-white'}>
 {playoff.home_score}
 </span>
 <span className="text-[#4B4B6A] mx-1">:</span>
 <span className={isLive ? 'text-red-400' : 'text-white'}>
 {playoff.away_score}
 </span>
 </div>
 ) : (
 <div className="text-sm font-bold pixel-number text-[#4B4B6A]">VS</div>
 )}
 <p className="text-xs text-[#8B8BA7] mt-1">
 {new Date(playoff.scheduled_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
 </p>
 </div>

 <div className="flex-1 text-center">
 <Link
 to={`/teams/${playoff.away_team.id}`}
 className="font-medium text-white text-sm hover:text-[#C6F135] transition-colors"
 >
 {playoff.away_team.name}
 </Link>
 </div>
 </div>
 </div>
 )
}

// 比赛卡片组件
function MatchCard({ match }: { match: Match }) {
 const isFinished = match.status === 'finished'
 const isLive = match.status === 'ongoing'

 return (
 <div className="p-4 bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-sm hover:border-[#0D7377]/30 hover:-translate-y-1 transition-all">
 <div className="flex items-center justify-between mb-3">
 <span className="text-xs text-[#8B8BA7]">第 {match.matchday} 轮</span>
 {isLive && (
 <span className="text-xs px-2 py-0.5 rounded-none bg-red-500 text-white animate-pulse">
 进行中
 </span>
 )}
 {isFinished && (
 <span className="text-xs px-2 py-0.5 rounded-none bg-[#1E1E2D] text-[#8B8BA7]">
 已结束
 </span>
 )}
 </div>

 <div className="flex items-center justify-between">
 <div className="flex-1 text-center">
 <Link
 to={`/teams/${match.home_team.id}`}
 className="font-medium text-white hover:text-[#C6F135] transition-colors"
 >
 {match.home_team.name}
 </Link>
 <p className="text-xs text-[#8B8BA7]">主</p>
 </div>

 <div className="px-4">
 {isFinished || isLive ? (
 <div className="text-2xl font-bold pixel-number">
 <span className={isLive ? 'text-red-400' : 'text-white'}>
 {match.home_score}
 </span>
 <span className="text-[#4B4B6A] mx-2">:</span>
 <span className={isLive ? 'text-red-400' : 'text-white'}>
 {match.away_score}
 </span>
 </div>
 ) : (
 <div className="text-lg font-bold pixel-number text-[#4B4B6A]">VS</div>
 )}
 <p className="text-xs text-[#8B8BA7] mt-1">
 {new Date(match.scheduled_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
 </p>
 </div>

 <div className="flex-1 text-center">
 <Link
 to={`/teams/${match.away_team.id}`}
 className="font-medium text-white hover:text-[#C6F135] transition-colors"
 >
 {match.away_team.name}
 </Link>
 <p className="text-xs text-[#8B8BA7]">客</p>
 </div>
 </div>
 </div>
 )
}



function LeagueDetail() {
 const { id } = useParams<{ id: string }>()
 const [activeTab, setActiveTab] = useState<'standings' | 'schedule' | 'stats' | 'records' | 'awards'>('standings')
 const [selectedSeasonId, setSelectedSeasonId] = useState<string | undefined>(undefined)
 const [leaderboardType, setLeaderboardType] = useState<LeaderboardType>('goals')
 
 const { league, loading: leagueLoading, error: leagueError } = useLeagueDetail(id)
 const { seasons, loading: seasonsLoading } = useSeasons()
 const { standings, loading: standingsLoading } = useLeagueTable(id, selectedSeasonId)
 const { matches, loading: matchesLoading } = useLeagueSchedule(id, selectedSeasonId)
 const { items: leaderboardItems, loading: leaderboardLoading } = useLeagueLeaderboard(id, leaderboardType, selectedSeasonId, 20)
 const { awards: leagueAwards, loading: awardsLoading } = useLeagueAwards(id, selectedSeasonId)
 
 // 默认选中当前赛季
 useEffect(() => {
 if (league?.current_season && !selectedSeasonId) {
 setSelectedSeasonId(league.current_season.id)
 }
 }, [league?.current_season, selectedSeasonId])
 
 if (leagueLoading) {
 return (
 <div className="max-w-[1200px]">
 <div className="h-8 w-32 bg-[#1E1E2D] animate-pulse mb-4" />
 <div className="h-48 bg-[#1E1E2D] animate-pulse" />
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

 return (
 <div className="max-w-[1200px]">
 {/* 返回按钮和所有比赛链接 */}
 <div className="flex items-center justify-between mb-4">
 <Link 
 to="/dashboard"
 className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors"
 >
 <ChevronLeft className="w-4 h-4" />
 返回首页
 </Link>
 <Link 
 to="/cups"
 className="inline-flex items-center gap-1 text-sm text-[#0D7377] hover:text-white transition-colors"
 >
 <Swords className="w-4 h-4" />
 查看杯赛
 </Link>
 </div>

 {/* 联赛信息头部 */}
 <div className="relative mb-6 overflow-hidden border-2 border-[#30334D] bg-[#080B11] shadow-pixel">
 <div className="absolute inset-0 opacity-40 bg-[linear-gradient(90deg,rgba(13,115,119,0.28),rgba(8,11,17,0.15)_42%,rgba(198,241,53,0.08))]" />
 <div className="absolute inset-0 opacity-20 bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[size:16px_16px]" />
 <div className="absolute left-0 top-0 h-2 w-2 bg-[#C6F135]" />
 <div className="absolute right-0 bottom-0 h-2 w-2 bg-[#C6F135]" />

 <div className="relative flex items-center gap-6 p-6">
 <div className="w-24 h-24 shrink-0 bg-[#050609] border-2 border-[#30334D] flex items-center justify-center shadow-pixel">
 <LeagueBadge
 systemCode={league.system_code}
 level={league.level}
 size="lg"
 title={`${league.name} 徽章`}
 />
 </div>
 <div className="min-w-0">
 <h1 className="text-4xl font-black text-white leading-tight">{league.name}</h1>
 </div>
 </div>

 {/* 附加赛信息 */}
 {league.playoffs && league.playoffs.length > 0 && (
 <div className="mt-6 pt-6 border-t border-[#2D2D44]">
 <div className="flex items-center gap-2 mb-4">
 <Medal className="w-5 h-5 text-amber-400" />
 <h2 className="text-lg font-semibold text-white">升降级附加赛</h2>
 </div>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {league.playoffs.map(playoff => (
 <PlayoffCard key={playoff.id} playoff={playoff} />
 ))}
 </div>
 </div>
 )}
 </div>

 {/* 赛季选择器 + Tab 导航 */}
 <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
 <div className="flex flex-wrap gap-2">
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
 <TabButton active={activeTab === 'stats'} onClick={() => setActiveTab('stats')}>
 <div className="flex items-center gap-2">
 <Target className="w-4 h-4" />
 数据
 </div>
 </TabButton>
 <TabButton active={activeTab === 'records'} onClick={() => setActiveTab('records')}>
 <div className="flex items-center gap-2">
 <Target className="w-4 h-4" />
 联赛纪录
 </div>
 </TabButton>
 <TabButton active={activeTab === 'awards'} onClick={() => setActiveTab('awards')}>
 <div className="flex items-center gap-2">
 <Trophy className="w-4 h-4" />
 赛季最佳
 </div>
 </TabButton>
 </div>
 
 {!seasonsLoading && seasons.length > 0 && (
 <SeasonSelector 
 seasons={seasons} 
 selectedSeasonId={selectedSeasonId} 
 onChange={setSelectedSeasonId} 
 />
 )}
 </div>

 {/* Tab 内容 */}
 <div className="card">
 {activeTab === 'standings' && (
 <div>
 <div className="flex items-center justify-between mb-4">
 <h3 className="text-lg font-semibold">积分榜</h3>
 <Legend league={league} />
 </div>
 
 {standingsLoading ? (
 <div className="space-y-2">
 {[1, 2, 3, 4, 5].map(i => (
 <div key={i} className="h-12 bg-[#1E1E2D] animate-pulse" />
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
 <StandingRow key={standing.team.id} standing={standing} league={league} />
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
 <div key={i} className="h-32 bg-[#1E1E2D] animate-pulse" />
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

 {activeTab === 'stats' && (
 <div>
 <div className="flex flex-col md:flex-row gap-4">
 <div className="w-full md:w-40 shrink-0">
 <h3 className="text-sm font-semibold text-[#8B8BA7] mb-2 px-3">榜单</h3>
 <LeaderboardSidebar
 activeType={leaderboardType}
 onChange={setLeaderboardType}
 />
 </div>
 <div className="flex-1 min-w-0">
 <LeaderboardTable
 items={leaderboardItems}
 valueFormat={getLeaderboardFormat(leaderboardType)}
 loading={leaderboardLoading}
 />
 </div>
 </div>
 </div>
 )}

 {activeTab === 'records' && (
 <div>
 <h3 className="text-lg font-semibold mb-4">联赛纪录</h3>
 <LeagueRecordsTab leagueId={id} />
 </div>
 )}

 {activeTab === 'awards' && (
 <div className="space-y-8">
 {awardsLoading ? (
   <div className="space-y-4">
     <div className="h-10 bg-[#1E1E2D] animate-pulse" />
     <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
       {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-[#1E1E2D] animate-pulse" />)}
     </div>
   </div>
 ) : (
   <>
     {/* 联赛最佳阵容 */}
     <section>
       <div className="flex items-center gap-2 mb-4">
         <div className="w-1 h-5 bg-amber-500" />
         <h3 className="text-lg font-bold text-white">联赛最佳阵容</h3>
       </div>
       <TeamOfSeasonGrid
         team={leagueAwards?.team_of_season || []}
         emptyText="该赛季暂无最佳阵容数据"
       />
     </section>

     {/* 联赛最佳位置 */}
     {(leagueAwards?.best_fw || leagueAwards?.best_mf || leagueAwards?.best_df || leagueAwards?.best_gk) && (
       <section>
         <div className="flex items-center gap-2 mb-4">
           <div className="w-1 h-5 bg-[#C6F135]" />
           <h3 className="text-lg font-bold text-white">联赛最佳位置</h3>
         </div>
         <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
           <AwardCard award={leagueAwards?.best_fw} size="lg" />
           <AwardCard award={leagueAwards?.best_mf} size="lg" />
           <AwardCard award={leagueAwards?.best_df} size="lg" />
           <AwardCard award={leagueAwards?.best_gk} size="lg" />
         </div>
       </section>
     )}

     {/* 联赛数据之王 */}
     <section>
       <div className="flex items-center gap-2 mb-4">
         <div className="w-1 h-5 bg-[#0D7377]" />
         <h3 className="text-lg font-bold text-white">联赛数据之王</h3>
       </div>
       <DataKingsRow
         goldenBoot={leagueAwards?.golden_boot}
         playmaker={leagueAwards?.playmaker}
         goldenGlove={leagueAwards?.golden_glove}
         goldenWall={leagueAwards?.golden_wall}
         size="lg"
         emptyText="该赛季暂无数据"
       />
     </section>
   </>
 )}
 </div>
 )}
 </div>
 </div>
 )
}

function LeagueRecordsTab({ leagueId }: { leagueId: string | undefined }) {
  const [records, setRecords] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!leagueId) return
    const fetchRecords = async () => {
      try {
        setLoading(true)
        const res = await api.get(`/leagues/${leagueId}/records`)
        if (res.success) {
          setRecords(res.data)
        }
      } catch (err) {
        console.error('Failed to fetch league records:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchRecords()
  }, [leagueId])

  if (loading) {
    return <div className="text-center py-16 text-[#8B8BA7]">加载中...</div>
  }

  if (!records || (records.team.length === 0 && records.player.length === 0 && records.match.length === 0)) {
    return (
      <div className="text-center py-12">
        <Target className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
        <p className="text-[#8B8BA7]">暂无联赛纪录</p>
      </div>
    )
  }

  const allRecords = [
    ...records.team.map((r: any) => ({ ...r, category: '球队' })),
    ...records.player.map((r: any) => ({ ...r, category: '球员' })),
    ...records.match.map((r: any) => ({ ...r, category: '比赛' })),
  ]

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {allRecords.map((record, idx) => (
        <div key={idx} className="p-4 bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/30 transition-all">
          <div className="flex items-start gap-4">
            <div className="shrink-0">
              <div className="w-12 h-12 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30 flex items-center justify-center">
                <Target className="w-6 h-6 text-[#0D7377]" />
              </div>
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-bold text-white truncate">{record.record_type_label}</h3>
                <span className="text-lg font-bold stat-number pixel-number text-[#C6F135]">{record.record_value}</span>
              </div>
              <div className="mt-1 text-sm text-white font-medium">{record.holder_name}</div>
              <div className="mt-1 flex items-center gap-2">
                <span className="text-xs text-[#4B4B6A]">{record.category}</span>
                {record.season_number !== undefined && (
                  <span className="text-xs text-[#4B4B6A]">第 {record.season_number} 赛季</span>
                )}
              </div>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default LeagueDetail
