import { useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { 
  Calendar, ChevronLeft, Trophy, MapPin, 
  Sword as Swords, CircleCheck as CheckCircle, Play as PlayCircle 
} from '../../components/ui/pixel-icons'
import api from '../../api/client'
import { useSeason } from '../../hooks/useSeason'
import type { SeasonCalendarDay } from '../../types/season'

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

// 获取状态显示配置
function getStatusConfig(status: string) {
 switch (status) {
 case 'finished':
 return {
 icon: CheckCircle,
 label: '已结束',
 className: 'bg-[#1E1E2D] text-[#8B8BA7]',
 pillClassName: 'bg-[#1E1E2D] text-[#8B8BA7]'
 }
 case 'ongoing':
 return {
 icon: PlayCircle,
 label: '进行中',
 className: 'bg-red-500 text-white animate-pulse',
 pillClassName: 'bg-red-500/20 text-red-400 border border-red-500/30'
 }
 default:
 return {
 icon: Calendar,
 label: '未开始',
 className: 'bg-[#0D4A4D]/40 text-[#0D7377]',
 pillClassName: 'bg-[#0D4A4D]/40 text-[#0D7377] border border-[#0D7377]/30'
 }
 }
}

// 获取比赛类型标签
function getFixtureTypeLabel(type: string, cupStage?: string) {
 if (type === 'league') {
 return `联赛 第${type === 'league' ? '' : ''}轮`
 }
 if (type.includes('cup_lightning')) {
 if (cupStage === 'GROUP') return '闪电杯-小组赛'
 if (cupStage?.startsWith('ROUND_')) return `闪电杯-${cupStage.replace('ROUND_', '')}强`
 if (cupStage === 'QUARTER') return '闪电杯-1/4决赛'
 if (cupStage === 'SEMI') return '闪电杯-半决赛'
 if (cupStage === 'FINAL') return '闪电杯-决赛'
 return '闪电杯'
 }
 if (type === 'cup_jenny') {
 return '杰尼杯'
 }
 return '其他'
}

// 格式化日期显示
function formatMatchDate(dateStr: string): string {
 const date = new Date(dateStr)
 const month = date.getMonth() + 1
 const day = date.getDate()
 return `${month}月${day}日`
}

// 比赛行组件
function MatchRow({
 date,
 fixture,
 team,
 isCurrentDay
}: {
 date: string
 fixture: ScheduleDay['teamFixtures'][0]
 team: Team
 isCurrentDay: boolean
}) {
 const statusConfig = getStatusConfig(fixture.status)
 
 const myScore = fixture.is_home ? fixture.home_score : fixture.away_score
 const opponentScore = fixture.is_home ? fixture.away_score : fixture.home_score
 
 // 判断胜负
 const getResult = () => {
 if (fixture.status !== 'finished' || myScore === undefined || opponentScore === undefined) {
 return null
 }
 if (myScore > opponentScore) return 'win'
 if (myScore < opponentScore) return 'loss'
 return 'draw'
 }
 
 const result = getResult()
 const resultBadge = result === 'win' 
 ? { text: '胜', className: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' }
 : result === 'loss'
 ? { text: '负', className: 'bg-red-500/20 text-red-400 border-red-500/30' }
 : result === 'draw'
 ? { text: '平', className: 'bg-[#2D2D44] text-[#8B8BA7] border-[#4B4B6A]' }
 : null

 // 确定主队和客队显示
 const homeTeamName = fixture.home_team_name
 const awayTeamName = fixture.away_team_name
 const homeTeamId = fixture.is_home ? team.id : fixture.opponent_id
 const awayTeamId = fixture.is_home ? fixture.opponent_id : team.id
 const isHomeMyTeam = fixture.is_home
 const isAwayMyTeam = !fixture.is_home

 return (
 <div className={`
 grid grid-cols-12 gap-4 items-center px-4 py-4 
 border-b border-[#2D2D44]/50 last:border-b-0
 hover:bg-[#1E1E2D]/50 transition-colors
 ${isCurrentDay ? 'bg-[#0D7377]/5' : ''}
 `}>
 {/* 日期 */}
 <div className="col-span-2">
 <div className="flex items-center gap-2">
 <span className={`font-semibold ${isCurrentDay ? 'text-[#0D7377]' : 'text-white'}`}>
 {formatMatchDate(date)}
 </span>
 {isCurrentDay && (
 <span className="text-[10px] px-1.5 py-0.5 bg-[#0D7377] text-white">
 今天
 </span>
 )}
 </div>
 </div>

 {/* 比赛类型 */}
 <div className="col-span-2">
 <span className="text-sm text-[#8B8BA7]">
 {fixture.type === 'league' ? `联赛 第${fixture.round}轮` : getFixtureTypeLabel(fixture.type, fixture.cup_stage)}
 </span>
 </div>

 {/* 主队 */}
 <div className="col-span-2 text-right">
 <Link 
 to={`/teams/${homeTeamId}`}
 className={`text-sm font-medium hover:text-[#0D7377] transition-colors ${
 isHomeMyTeam ? 'text-white' : 'text-[#8B8BA7]'
 }`}
 >
 {homeTeamName || '未知球队'}
 </Link>
 </div>

 {/* VS / 比分 */}
 <div className="col-span-2 flex items-center justify-center gap-3">
 {fixture.status === 'scheduled' ? (
 <div className="flex items-center gap-2">
 <span className="text-xs text-[#4B4B6A]">主</span>
 <span className="text-sm font-bold text-[#4B4B6A]">VS</span>
 <span className="text-xs text-[#4B4B6A]">客</span>
 </div>
 ) : (
 <div className="flex items-center gap-3">
 <span className={`text-lg font-bold pixel-number ${isHomeMyTeam ? 'text-white' : 'text-[#8B8BA7]'}`}>
 {fixture.home_score}
 </span>
 <span className="text-[#4B4B6A]">:</span>
 <span className={`text-lg font-bold pixel-number ${isAwayMyTeam ? 'text-white' : 'text-[#8B8BA7]'}`}>
 {fixture.away_score}
 </span>
 </div>
 )}
 </div>

 {/* 客队 */}
 <div className="col-span-2 text-left">
 <Link 
 to={`/teams/${awayTeamId}`}
 className={`text-sm font-medium hover:text-[#0D7377] transition-colors ${
 isAwayMyTeam ? 'text-white' : 'text-[#8B8BA7]'
 }`}
 >
 {awayTeamName || '未知球队'}
 </Link>
 </div>

 {/* 状态 & 结果 */}
 <div className="col-span-1 flex items-center justify-end gap-2">
 {resultBadge && (
 <span className={`text-xs px-2 py-0.5 border ${resultBadge.className}`}>
 {resultBadge.text}
 </span>
 )}
 <span className={`text-xs px-2 py-0.5 border ${statusConfig.pillClassName}`}>
 {statusConfig.label}
 </span>
 </div>
 </div>
 )
}

function Schedule() {
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
 
 // 当前比赛日
 const currentDay = season?.current_day || 0
 
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
 <Calendar className="w-16 h-16 text-[#4B4B6A] mx-auto mb-4" />
 <h2 className="text-xl font-bold text-white mb-2">加载失败</h2>
 <p className="text-[#8B8BA7] mb-6">{error}</p>
 <Link to="/dashboard" className="btn-primary inline-flex items-center gap-2">
 <ChevronLeft className="w-4 h-4" />
 返回首页
 </Link>
 </div>
 )
 }
 
 if (!team) {
 return (
 <div className="max-w-[1200px] text-center py-20">
 <Trophy className="w-16 h-16 text-[#4B4B6A] mx-auto mb-4" />
 <h2 className="text-xl font-bold text-white mb-2">暂无球队</h2>
 <p className="text-[#8B8BA7] mb-6">您还没有创建或加入球队</p>
 <Link to="/dashboard" className="btn-primary inline-flex items-center gap-2">
 <ChevronLeft className="w-4 h-4" />
 返回首页
 </Link>
 </div>
 )
 }
 
 return (
 <div className="max-w-[1200px]">
 {/* 返回按钮 */}
 <Link 
 to="/dashboard"
 className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
 >
 <ChevronLeft className="w-4 h-4" />
 返回首页
 </Link>
 
 {/* 页面标题 */}
 <div className="flex items-center justify-between mb-6">
 <div>
 <h1 className="text-2xl font-bold text-white">赛程安排</h1>
 <p className="text-sm text-[#8B8BA7] mt-1">
 {team.name} · 第 {season?.season_number || '-'} 赛季
 </p>
 </div>
 {displayStatus && (
 <div className="text-right hidden md:block">
 <p className="text-sm text-[#0D7377]">{displayStatus.display_text}</p>
 </div>
 )}
 </div>
 
 {/* 统计卡片 */}
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
 <div className="card p-4 border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="flex items-center gap-2 mb-2">
 <Swords className="w-4 h-4 text-[#0D7377]" />
 <span className="text-xs text-[#8B8BA7]">已赛场次</span>
 </div>
 <p className="text-2xl font-bold pixel-number text-white">{stats.played}</p>
 </div>
 
 <div className="card p-4 border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="flex items-center gap-2 mb-2">
 <CheckCircle className="w-4 h-4 text-emerald-400" />
 <span className="text-xs text-[#8B8BA7]">战绩</span>
 </div>
 <p className="text-2xl font-bold pixel-number text-white">
 {stats.wins}-{stats.draws}-{stats.losses}
 </p>
 </div>
 
 <div className="card p-4 border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="flex items-center gap-2 mb-2">
 <Trophy className="w-4 h-4 text-amber-400" />
 <span className="text-xs text-[#8B8BA7]">胜率</span>
 </div>
 <p className="text-2xl font-bold pixel-number text-white">
 {stats.played > 0 ? Math.round((stats.wins / stats.played) * 100) : 0}%
 </p>
 </div>
 
 <div className="card p-4 border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="flex items-center gap-2 mb-2">
 <MapPin className="w-4 h-4 text-[#8B8BA7]" />
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
 
 {/* 赛程列表 - 表格形式 */}
 <div className="card overflow-hidden border-2 border-[#2D2D44] hover:-translate-y-1 transition-all">
 <div className="px-4 py-4 border-b border-[#2D2D44]">
 <h3 className="text-lg font-semibold text-white">全部赛程</h3>
 </div>
 
 {schedule.length === 0 ? (
 <div className="text-center py-12">
 <Calendar className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
 <p className="text-[#8B8BA7]">暂无赛程数据</p>
 </div>
 ) : (
 <div>
 {/* 表头 */}
 <div className="grid grid-cols-12 gap-4 px-4 py-3 bg-[#1E1E2D] text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
 <div className="col-span-2">日期</div>
 <div className="col-span-2">赛事</div>
 <div className="col-span-2 text-right">主队</div>
 <div className="col-span-2 text-center">比分</div>
 <div className="col-span-2">客队</div>
 <div className="col-span-2 text-right">状态</div>
 </div>
 
 {/* 赛程行 */}
 <div className="divide-y divide-[#2D2D44]/50">
 {schedule.map(day => (
 day.teamFixtures.map(fixture => (
 <MatchRow
 key={`${day.day}-${fixture.id}`}
 date={day.date}
 fixture={fixture}
 team={team}
 isCurrentDay={day.day === currentDay}
 />
 ))
 ))}
 </div>
 </div>
 )}
 </div>
 </div>
 )
}

export default Schedule
