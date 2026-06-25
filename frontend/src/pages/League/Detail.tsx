import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { 
  ChevronLeft, 
} from '../../components/ui/pixel-icons'
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
import { RecordsBoard } from '../../components/records/RecordsBoard'
import { PageHeader } from '../../components/ui/PageHeader'
import { SegmentedTabs } from '../../components/ui/SegmentedTabs'

// 图例组件 — 根据联赛赛制动态显示
function Legend({ league }: { league: League }) {
  const items: { color: string; label: string }[] = []

  // 冠军（所有联赛都有）
  items.push({ color: 'bg-[#FFC247]', label: '冠军' })

  // 直升升级
  if (league.promotion_spots > 0) {
    items.push({ color: 'bg-[#1F5F43]', label: '升级区' })
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
    items.push({ color: 'bg-[#FF6F59]', label: '降级区' })
  }

  return (
    <div className="flex items-center gap-4 text-xs flex-wrap">
      {items.map((item) => (
        <div key={item.label + item.color} className="flex items-center gap-1.5">
          <div className={`w-3 h-3 ${item.color}`} />
          <span className="text-[#466353]">{item.label}</span>
        </div>
      ))}
    </div>
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
 className="appearance-none bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#173126] text-sm px-4 py-2 pr-8 focus:outline-none focus:border-[#1F5F43] focus:ring-1 focus:ring-[#1F5F43] cursor-pointer"
 >
 {seasons.map((season) => (
 <option key={season.id} value={season.id}>
 第 {season.season_number} 赛季
 </option>
 ))}
 </select>
 <ChevronLeft className="w-4 h-4 text-[#466353] absolute right-2 top-1/2 -translate-y-1/2 rotate-[-90deg] pointer-events-none" />
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
  champion: { bg: 'bg-[#FFC247]', text: 'text-[#173126]', row: 'bg-[#FFC247]/5', label: '冠军' },
  promotion: { bg: 'bg-[#1F5F43]', text: 'text-[#173126]', row: 'bg-[#1F5F43]/5', label: '升级区' },
  promotion_playoff: { bg: 'bg-sky-500', text: 'text-[#173126]', row: 'bg-sky-500/5', label: '附加赛' },
  safe: { bg: 'bg-[#FFF8DC]/80', text: 'text-[#466353]', row: '', label: '' },
  relegation_playoff: { bg: 'bg-orange-500', text: 'text-[#173126]', row: 'bg-orange-500/5', label: '附加赛' },
  relegation: { bg: 'bg-[#FF6F59]', text: 'text-[#173126]', row: 'bg-[#FF6F59]/5', label: '降级区' },
}

// 积分榜行组件
function StandingRow({ standing, league }: { standing: LeagueStanding; league: League }) {
  const zone = getZoneType(standing.position, league)
  const colors = zoneColors[zone]

  let rowClass = 'hover:bg-[#FFF8DC]/80 transition-colors'
  if (colors.row) rowClass += ' ' + colors.row

  return (
    <tr className={`border-b border-[#1F5F43]/20 ${rowClass}`}>
      <td className="py-3 px-4">
        <div className={`w-7 h-7 flex items-center justify-center text-sm font-bold pixel-number ${colors.bg} ${colors.text}`}>
          {standing.position}
        </div>
      </td>
      <td className="py-3 px-4">
        <Link
          to={`/teams/${standing.team.id}`}
          className="font-medium text-[#173126] hover:text-[#1F5F43] transition-colors"
        >
          {standing.team.name}
        </Link>
      </td>
 <td className="py-3 px-4 text-center stat-number">{standing.played}</td>
 <td className="py-3 px-4 text-center stat-number text-[#1F5F43]">{standing.won}</td>
 <td className="py-3 px-4 text-center stat-number text-[#466353]">{standing.drawn}</td>
 <td className="py-3 px-4 text-center stat-number text-[#FF6F59]">{standing.lost}</td>
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
 'W': 'bg-[#1F5F43]',
 'D': 'bg-[#8B5A2B]/40',
 'L': 'bg-[#FF6F59]'
 }
 return (
 <div 
 key={idx} 
 className={`w-5 h-5 ${colors[result as keyof typeof colors]} flex items-center justify-center text-[10px] font-bold text-[#173126]`}
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
 <div className="p-3 bg-[#FFC247]/10 border-2 border-amber-500/30 shadow-pixel-sm hover:-translate-y-1 transition-all">
 <div className="flex items-center justify-between mb-2">
 <span className="text-xs font-medium text-[#C77A00]">{playoff.name}</span>
 {isLive && (
 <span className="text-xs px-2 py-0.5 rounded-none bg-[#FF6F59] text-[#F8FFD2] animate-pulse">
 进行中
 </span>
 )}
 {isFinished && (
 <span className="text-xs px-2 py-0.5 rounded-none bg-[#FFF8DC]/80 text-[#466353]">
 已结束
 </span>
 )}
 </div>

 <div className="flex items-center justify-between">
 <div className="flex-1 text-center">
 <Link
 to={`/teams/${playoff.home_team.id}`}
 className="font-medium text-[#173126] text-sm hover:text-[#1F5F43] transition-colors"
 >
 {playoff.home_team.name}
 </Link>
 </div>

 <div className="px-3 text-center">
 {isFinished || isLive ? (
 <div className="text-xl font-bold pixel-number">
 <span className={isLive ? 'text-[#FF6F59]' : 'text-[#173126]'}>
 {playoff.home_score}
 </span>
 <span className="text-[#8B5A2B]/40 mx-1">:</span>
 <span className={isLive ? 'text-[#FF6F59]' : 'text-[#173126]'}>
 {playoff.away_score}
 </span>
 </div>
 ) : (
 <div className="text-sm font-bold pixel-number text-[#8B5A2B]/40">VS</div>
 )}
 <p className="text-xs text-[#466353] mt-1">
 {new Date(playoff.scheduled_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
 </p>
 </div>

 <div className="flex-1 text-center">
 <Link
 to={`/teams/${playoff.away_team.id}`}
 className="font-medium text-[#173126] text-sm hover:text-[#1F5F43] transition-colors"
 >
 {playoff.away_team.name}
 </Link>
 </div>
 </div>
 </div>
 )
}

// 比赛行组件（杯赛风格）
function FixtureRow({ match }: { match: Match }) {
 const isFinished = match.status === 'finished'
 const isLive = match.status === 'ongoing'
 const winner = isFinished && match.home_score != null && match.away_score != null
   ? match.home_score > match.away_score ? 'home' : match.away_score > match.home_score ? 'away' : null
   : null

 return (
 <div
   className="bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 shadow-pixel-sm hover:border-[#1F5F43] transition-colors cursor-pointer"
   onClick={() => window.location.href = `/match/${match.id}`}
 >
   <div className="grid grid-cols-[minmax(0,1fr)_76px_minmax(0,1fr)] items-center gap-3 px-4 py-3">
     <div className={`min-w-0 ${winner === 'home' ? 'text-[#1F5F43]' : 'text-[#173126]'}`}>
       <Link
         to={`/teams/${match.home_team.id}`}
         className="block truncate font-bold hover:text-[#1F5F43] transition-colors"
         onClick={(e) => e.stopPropagation()}
       >
         {match.home_team.name}
       </Link>
     </div>

     <div className="text-center">
       {isFinished || isLive ? (
         <div className={`text-lg font-black stat-number ${isLive ? 'text-[#FF6F59]' : 'text-[#173126]'}`}>
           {match.home_score ?? '-'}:{match.away_score ?? '-'}
         </div>
       ) : (
         <div className="text-xs font-black pixel-number text-[#8B5A2B]/40">VS</div>
       )}
       <div className="mt-1 text-[10px] font-bold text-[#8B5A2B]/40">
         {new Date(match.scheduled_at).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })}
       </div>
     </div>

     <div className={`min-w-0 text-right ${winner === 'away' ? 'text-[#1F5F43]' : 'text-[#173126]'}`}>
       <Link
         to={`/teams/${match.away_team.id}`}
         className="block truncate font-bold hover:text-[#1F5F43] transition-colors"
         onClick={(e) => e.stopPropagation()}
       >
         {match.away_team.name}
       </Link>
     </div>
   </div>
   {isLive && (
     <div className="border-t border-[#1F5F43]/20 px-4 py-1 text-xs font-bold text-[#FF6F59]">进行中</div>
   )}
 </div>
 )
}

// 联赛赛程列表（按轮次分组，杯赛风格）
function LeagueScheduleList({ matches }: { matches: Match[] }) {
 const matchesByMatchday: Record<number, Match[]> = {}
 matches.forEach(m => {
   if (!matchesByMatchday[m.matchday]) matchesByMatchday[m.matchday] = []
   matchesByMatchday[m.matchday].push(m)
 })

 const matchdays = Object.keys(matchesByMatchday).map(Number).sort((a, b) => a - b)

 if (matchdays.length === 0) {
   return (
     <div className="text-center py-12">
       <p className="text-[#466353]">暂无赛程数据</p>
     </div>
   )
 }

 return (
   <div className="space-y-6">
     {matchdays.map((matchday, index) => {
       const roundMatches = matchesByMatchday[matchday]
       return (
         <section key={matchday} className="border-2 border-[#1F5F43]/20 bg-white/70 shadow-pixel-sm overflow-hidden">
           <div className="flex items-center justify-between border-b-2 border-[#1F5F43]/20 bg-[#FFF8DC]/80 px-4 py-3">
             <div className="flex items-center gap-3">
               <div className="h-6 w-2 bg-[#1F5F43]" />
               <h4 className="text-lg font-black text-[#173126]">第 {matchday} 轮</h4>
             </div>
             <span className="text-xs font-bold text-[#466353]">{roundMatches.length} 场</span>
           </div>
           <div className="divide-y divide-[#1F5F43]/20">
             {roundMatches.map(match => (
               <FixtureRow key={match.id} match={match} />
             ))}
           </div>
           {index < matchdays.length - 1 && (
             <div className="border-t border-[#1F5F43]/20 px-4 py-2 text-xs text-[#8B5A2B]/40">
               下一轮：第 {matchdays[index + 1]} 轮
             </div>
           )}
         </section>
       )
     })}
   </div>
 )
}



function LeagueDetail() {
 const { id } = useParams<{ id: string }>()
 const navigate = useNavigate()
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
 <div className="h-8 w-32 bg-[#FFF8DC]/80 animate-pulse mb-4" />
 <div className="h-48 bg-[#FFF8DC]/80 animate-pulse" />
 </div>
 )
 }
 
 if (!league) {
 return (
 <div className="max-w-[1200px] text-center py-20">
 <h2 className="text-xl font-bold text-[#173126] mb-2">联赛未找到</h2>
 <p className="text-[#466353] mb-2">该联赛不存在或已被删除</p>
 {leagueError && (
 <p className="text-[#FF6F59] text-sm mb-6">错误: {leagueError}</p>
 )}
 <p className="text-[#8B5A2B]/40 text-xs mb-6">联赛ID: {id || '未提供'}</p>
 <Link to="/leagues" className="btn-primary inline-flex items-center gap-2">
 返回联赛列表
 </Link>
 </div>
 )
 }

 return (
 <div className="max-w-[1200px]">
 {/* 返回按钮和所有比赛链接 */}
 <div className="flex items-center justify-between mb-4">
 <button 
 onClick={() => navigate(-1)}
 className="text-sm text-[#466353] hover:text-[#173126] transition-colors"
 >
 返回上一页
 </button>
 <Link 
 to="/leagues"
 className="text-sm text-[#1F5F43] hover:text-[#173126] transition-colors"
 >
 所有联赛
 </Link>
 </div>

 {/* 联赛信息头部 */}
 <PageHeader
 title={league.name}
 subtitle={`${league.system_name} · 第 ${league.level} 级联赛`}
 />

 {/* 附加赛信息 */}
 {league.playoffs && league.playoffs.length > 0 && (
 <div className="mb-6 p-4 border border-[#1F5F43]/20 bg-[#ECFFD8]">
 <h2 className="text-lg font-semibold text-[#173126] mb-4">升降级附加赛</h2>
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {league.playoffs.map(playoff => (
 <PlayoffCard key={playoff.id} playoff={playoff} />
 ))}
 </div>
 </div>
 )}

 {/* Tab 导航 + 赛季选择器 */}
 <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
 <SegmentedTabs
 tabs={[
 { value: 'standings', label: '积分榜' },
 { value: 'schedule', label: '赛程' },
 { value: 'stats', label: '数据' },
 { value: 'records', label: '联赛纪录' },
 { value: 'awards', label: '赛季最佳' },
 ]}
 value={activeTab}
 onChange={(v) => setActiveTab(v as 'standings' | 'schedule' | 'stats' | 'records' | 'awards')}
 />
 
 {!seasonsLoading && seasons.length > 0 && (
 <SeasonSelector 
 seasons={seasons} 
 selectedSeasonId={selectedSeasonId} 
 onChange={setSelectedSeasonId} 
 />
 )}
 </div>

 {/* Tab 内容 */}
 <div className="space-y-6">
 {activeTab === 'standings' && (
 <div >
 <div className="mb-4">
 <Legend league={league} />
 </div>
 
 {standingsLoading ? (
 <div className="space-y-2">
 {[1, 2, 3, 4, 5].map(i => (
 <div key={i} className="h-12 bg-[#FFF8DC]/80 animate-pulse" />
 ))}
 </div>
 ) : standings.length === 0 ? (
 <div className="text-center py-12">

 <p className="text-[#466353]">暂无积分数据</p>
 </div>
 ) : (
 <div className="overflow-x-auto">
 <table className="w-full">
 <thead>
 <tr className="text-left text-xs text-[#466353] border-b border-[#1F5F43]/20">
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
 <div >
 {matchesLoading ? (
 <div className="space-y-4">
 {[1, 2, 3, 4].map(i => (
 <div key={i} className="h-28 bg-[#FFF8DC]/80 animate-pulse" />
 ))}
 </div>
 ) : (
 <LeagueScheduleList matches={matches} />
 )}
 </div>
 )}

 {activeTab === 'stats' && (
 <div >
 <div className="flex flex-col md:flex-row gap-4">
 <div className="w-full md:w-40 shrink-0">
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
 <div >
 <LeagueRecordsTab leagueId={id} />
 </div>
 )}

 {activeTab === 'awards' && (
 <div className="space-y-8">
 {awardsLoading ? (
   <div className="space-y-4">
     <div className="h-10 bg-[#FFF8DC]/80 animate-pulse" />
     <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
       {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-[#FFF8DC]/80 animate-pulse" />)}
     </div>
   </div>
 ) : (
   <>
     {/* 联赛最佳阵容 */}
     <section >
       <div className="flex items-center gap-2 mb-4">
         <div className="w-1 h-5 bg-[#FFC247]" />
         <h3 className="text-lg font-bold text-[#173126]">联赛最佳阵容</h3>
       </div>
       <TeamOfSeasonGrid
         team={leagueAwards?.team_of_season || []}
         emptyText="该赛季暂无最佳阵容数据"
       />
     </section>

     {/* 联赛最佳位置 */}
     {(leagueAwards?.best_fw || leagueAwards?.best_mf || leagueAwards?.best_df || leagueAwards?.best_gk) && (
       <section >
         <div className="flex items-center gap-2 mb-4">
           <div className="w-1 h-5 bg-[#B9EF3F]" />
           <h3 className="text-lg font-bold text-[#173126]">联赛最佳位置</h3>
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
     <section >
       <div className="flex items-center gap-2 mb-4">
         <div className="w-1 h-5 bg-[#1F5F43]" />
         <h3 className="text-lg font-bold text-[#173126]">联赛数据之王</h3>
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

  return <RecordsBoard records={records} loading={loading} emptyText="暂无联赛纪录" />
}

export default LeagueDetail
