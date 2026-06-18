import { useEffect, useState, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import { useSeason } from '../../hooks/useSeason'
import type { SeasonCalendarDay } from '../../types/season'
import { PageHeader } from '../../components/ui/PageHeader'

// 球队类型
interface Team {
 id: string
 name: string
 short_name?: string
 logo_url?: string
}

// 扩展的赛程日类型，包含球队信息
interface ScheduleDay extends SeasonCalendarDay {
 teamFixtures: {
 id: string
 type: string
 round: number
 opponent: string
 opponent_id: string
 is_home: boolean
 home_team_name: string
 away_team_name: string
 home_score?: number
 away_score?: number
 status: string
 cup_stage?: string
 cup_group?: string
 }[]
}

// 紧凑日期格式
function formatCompactDate(dateStr: string): string {
 const date = new Date(dateStr)
 return `${date.getMonth() + 1}/${date.getDate()}`
}

// 紧凑比赛行组件
function FixtureRow({
 date,
 fixture,
 team
}: {
 date: string
 fixture: ScheduleDay['teamFixtures'][0]
 team: Team
}) {
 const navigate = useNavigate()
 const isFinished = fixture.status === 'finished'
 const isLive = fixture.status === 'ongoing'

 const winner = isFinished && fixture.home_score != null && fixture.away_score != null
   ? fixture.home_score > fixture.away_score ? 'home' : fixture.away_score > fixture.home_score ? 'away' : null
   : null

 const homeTeamName = fixture.home_team_name
 const awayTeamName = fixture.away_team_name
 const homeTeamId = fixture.is_home ? team.id : fixture.opponent_id
 const awayTeamId = fixture.is_home ? fixture.opponent_id : team.id

 return (
 <div
   className="grid grid-cols-[48px_1fr_48px_1fr] items-center gap-1 px-2 py-1 hover:bg-[#1E1E2D]/50 transition-colors cursor-pointer"
   onClick={() => navigate(`/match/${fixture.id}`)}
 >
   <div className="text-[10px] text-[#8B8BA7] leading-tight text-center">
     <div>{formatCompactDate(date)}</div>
     <div>{fixture.type === 'league' ? `${fixture.round}轮` : '杯'}</div>
   </div>

   <div className={`text-right truncate text-xs font-bold ${winner === 'home' ? 'text-[#C6F135]' : 'text-white'}`}>
     <Link
       to={`/teams/${homeTeamId}`}
       onClick={(e) => e.stopPropagation()}
       className="hover:text-[#C6F135] transition-colors"
     >
       {homeTeamName || '未知'}
     </Link>
   </div>

   <div className="text-center">
     {fixture.status === 'scheduled' ? (
       <span className="text-[10px] font-black pixel-number text-[#4B4B6A]">VS</span>
     ) : (
       <span className={`text-xs font-black stat-number ${isLive ? 'text-red-400' : 'text-white'}`}>
         {fixture.home_score ?? '-'}:{fixture.away_score ?? '-'}
       </span>
     )}
   </div>

   <div className={`text-left truncate text-xs font-bold ${winner === 'away' ? 'text-[#C6F135]' : 'text-white'}`}>
     <Link
       to={`/teams/${awayTeamId}`}
       onClick={(e) => e.stopPropagation()}
       className="hover:text-[#C6F135] transition-colors"
     >
       {awayTeamName || '未知'}
     </Link>
   </div>
 </div>
 )
}

function Schedule() {
 const navigate = useNavigate()
 const [team, setTeam] = useState<Team | null>(null)
 const [schedule, setSchedule] = useState<ScheduleDay[]>([])
 const [loading, setLoading] = useState(true)
 const [error, setError] = useState<string | null>(null)
 
 const { season, displayStatus } = useSeason()
 
 // 获取球队和赛程数据
 useEffect(() => {
 const fetchData = async () => {
 try {
 setLoading(true)
 setError(null)
 
 // 获取当前用户的球队
 const teamResponse = await api.get<Team>('/teams/my-team')
 if (!teamResponse.success || !teamResponse.data) {
 throw new Error('获取球队信息失败')
 }
 const teamData = teamResponse.data
 setTeam(teamData)
 
 // 获取当前赛季
 const seasonResponse = await api.getCurrentSeason()
 if (!seasonResponse.success || !seasonResponse.data) {
 throw new Error('获取赛季信息失败')
 }
 const seasonData = seasonResponse.data
 
 // 获取球队赛程日历
 const calendarResponse = await api.getSeasonCalendar(
 seasonData.season_number,
 teamData.id
 )
 
 if (!calendarResponse.success || !calendarResponse.data) {
 throw new Error('获取赛程失败')
 }
 const calendarData = calendarResponse.data
 
 // 处理赛程数据，为每一天找到该球队的比赛
 const processedSchedule: ScheduleDay[] = calendarData.calendar.map(day => {
 const teamFixtures = day.fixtures
 .filter(f => f.home_team_id === teamData.id || f.away_team_id === teamData.id)
 .map(f => {
 const isHome = f.home_team_id === teamData.id
 return {
 id: f.id,
 type: f.type,
 round: f.round,
 opponent: isHome ? f.away_team_name : f.home_team_name,
 opponent_id: isHome ? f.away_team_id : f.home_team_id,
 is_home: isHome,
 home_team_name: f.home_team_name,
 away_team_name: f.away_team_name,
 home_score: f.home_score,
 away_score: f.away_score,
 status: f.status,
 cup_stage: f.cup_stage,
 cup_group: f.cup_group
 }
 })
 
 return {
 ...day,
 teamFixtures
 }
 }).filter(day => day.teamFixtures.length > 0)
 
 setSchedule(processedSchedule)
 } catch (err) {
 setError(err instanceof Error ? err.message : '未知错误')
 } finally {
 setLoading(false)
 }
 }
 
 fetchData()
 }, [])
 
 // 统计信息
 const stats = useMemo(() => {
 let played = 0
 let wins = 0
 let draws = 0
 let losses = 0
 let goalsFor = 0
 let goalsAgainst = 0
 
 schedule.forEach(day => {
 day.teamFixtures.forEach(fixture => {
 if (fixture.status === 'finished') {
 played++
 const myScore = fixture.is_home ? fixture.home_score : fixture.away_score
 const opponentScore = fixture.is_home ? fixture.away_score : fixture.home_score
 
 if (myScore !== undefined && opponentScore !== undefined) {
 goalsFor += myScore
 goalsAgainst += opponentScore
 
 if (myScore > opponentScore) wins++
 else if (myScore < opponentScore) losses++
 else draws++
 }
 }
 })
 })
 
 return { played, wins, draws, losses, goalsFor, goalsAgainst }
 }, [schedule])
 
 if (loading) {
 return (
 <div className="max-w-[1200px]">
 <div className="h-8 w-48 bg-[#1E1E2D] animate-pulse mb-4" />
 <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
 {[1, 2, 3, 4].map(i => (
 <div key={i} className="h-24 bg-[#1E1E2D] animate-pulse" />
 ))}
 </div>
 <div className="h-96 bg-[#1E1E2D] animate-pulse" />
 </div>
 )
 }
 
 if (error) {
 return (
 <div className="max-w-[1200px] text-center py-20">
 <h2 className="text-xl font-bold text-white mb-2">加载失败</h2>
 <p className="text-[#8B8BA7] mb-6">{error}</p>
 <button onClick={() => navigate(-1)} className="btn-primary inline-flex items-center gap-2">
 返回上一页
 </button>
 </div>
 )
 }
 
 if (!team) {
 return (
 <div className="max-w-[1200px] text-center py-20">
 <h2 className="text-xl font-bold text-white mb-2">暂无球队</h2>
 <p className="text-[#8B8BA7] mb-6">您还没有创建或加入球队</p>
 <button onClick={() => navigate(-1)} className="btn-primary inline-flex items-center gap-2">
 返回上一页
 </button>
 </div>
 )
 }
 
 return (
 <div className="max-w-[1200px]">
 {/* 返回按钮 */}
 <button 
 onClick={() => navigate(-1)}
 className="text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
 >
 返回上一页
 </button>
 
 <PageHeader
 title="赛程安排"
 subtitle={`${team.name} · 第 ${season?.season_number || '-'} 赛季`}
 action={
 displayStatus ? (
 <div className="text-right hidden md:block">
 <p className="text-sm text-[#0D7377]">{displayStatus.display_text}</p>
 </div>
 ) : undefined
 }
 />
 
 {/* 统计卡片 */}
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
 <div className="card p-4 border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="mb-2">
 <span className="text-xs text-[#8B8BA7]">已赛场次</span>
 </div>
 <p className="text-2xl font-bold pixel-number text-white">{stats.played}</p>
 </div>
 
 <div className="card p-4 border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="mb-2">
 <span className="text-xs text-[#8B8BA7]">战绩</span>
 </div>
 <p className="text-2xl font-bold pixel-number text-white">
 {stats.wins}-{stats.draws}-{stats.losses}
 </p>
 </div>
 
 <div className="card p-4 border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="mb-2">
 <span className="text-xs text-[#8B8BA7]">胜率</span>
 </div>
 <p className="text-2xl font-bold pixel-number text-white">
 {stats.played > 0 ? Math.round((stats.wins / stats.played) * 100) : 0}%
 </p>
 </div>
 
 <div className="card p-4 border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="mb-2">
 <span className="text-xs text-[#8B8BA7]">净胜球</span>
 </div>
 <p className={`text-2xl font-bold pixel-number ${
 stats.goalsFor - stats.goalsAgainst >= 0 ? 'text-emerald-400' : 'text-red-400'
 }`}>
 {stats.goalsFor - stats.goalsAgainst >= 0 ? '+' : ''}
 {stats.goalsFor - stats.goalsAgainst}
 </p>
 </div>
 </div>
 
 {/* 赛程列表 - 紧凑平铺 */}
 <div>
 <div className="flex items-center justify-between mb-3">
 <h3 className="text-lg font-semibold text-white">全部赛程</h3>
 <span className="text-xs text-[#8B8BA7]">{schedule.reduce((sum, d) => sum + d.teamFixtures.length, 0)} 场</span>
 </div>
 
 {schedule.length === 0 ? (
 <div className="text-center py-12">
 <p className="text-[#8B8BA7]">暂无赛程数据</p>
 </div>
 ) : (
 <section className="border-2 border-[#2D2D44] bg-[#0B0D14] shadow-pixel-sm overflow-hidden">
 <div className="grid grid-cols-[48px_1fr_48px_1fr] gap-1 px-2 py-1.5 text-[10px] text-[#8B8BA7] border-b border-[#2D2D44] bg-[#12121A]">
 <span className="text-center">日期</span>
 <span className="text-right">主队</span>
 <span></span>
 <span className="text-left">客队</span>
 </div>
 <div className="divide-y divide-[#2D2D44]">
 {schedule.flatMap(day =>
 day.teamFixtures.map(fixture => (
 <FixtureRow
 key={fixture.id}
 date={day.date}
 fixture={fixture}
 team={team}
 />
 ))
 )}
 </div>
 </section>
 )}
 </div>
 </div>
 )
}

export default Schedule
