import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import { 
 Trophy, 
 ChevronLeft, 
 Users,
 Calendar,
 Grid3X3,
 GitBranch,
 List,
 Target,
 ArrowUpRight,
 Shield
} from 'lucide-react'
import { 
 useCupDetail, 
 useCupGroups, 
 useCupFixtures, 
 useCupTopScorers, 
 useCupTopAssists, 
 useCupCleanSheets
} from '../../hooks/useCups'
import { useSeasons } from '../../hooks/useSeasons'
import type { CupFixture, CupGroup } from '../../types/cup'
import type { Season } from '../../types/season'
import { CUP_CONFIG, CUP_STAGE_CONFIG } from '../../types/cup'

type TabType = 'groups' | 'knockout' | 'fixtures' | 'scorers' | 'assists' | 'clean-sheets'

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
 className="appearance-none bg-[#1E1E2D] border border-[#2D2D44] text-white text-sm px-4 py-2 pr-8 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377] cursor-pointer"
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

// Tab 按钮组件
function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
 return (
 <button
 onClick={onClick}
 className={`px-4 py-2 font-medium text-sm transition-all duration-200 ${
 active
 ? 'bg-[#0D7377] text-white border-2 font-bold shadow-pixel shadow-[#0D7377]/25'
 : 'text-[#8B8BA7] hover:text-white hover:bg-[#1E1E2D] border-2 border-transparent'
 }`}
 >
 {children}
 </button>
 )
}

// 比赛卡片组件
function MatchCard({ match }: { match: CupFixture }) {
 const isFinished = match.status === 'finished'
 const isLive = match.status === 'ongoing'
 const stageConfig = match.cup_stage ? CUP_STAGE_CONFIG[match.cup_stage] : null
 
 return (
 <div className="p-4 bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-sm hover:border-[#0D7377]/30 hover:-translate-y-1 transition-all">
 <div className="flex items-center justify-between mb-3">
 <div className="flex items-center gap-2">
 {match.cup_group_name && (
 <span className="text-xs px-2 py-0.5 rounded-none bg-[#1E1E2D] text-[#8B8BA7]">
 小组 {match.cup_group_name}
 </span>
 )}
 {stageConfig && (
 <span className={`text-xs px-2 py-0.5 rounded-none bg-[#2D2D44] text-white`}>
 {stageConfig.name}
 </span>
 )}
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
 第{match.season_day}天
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

// 小组赛表格行组件
function GroupStandingRow({ 
 position, 
 teamName, 
 played, 
 won, 
 drawn, 
 lost, 
 goalsFor, 
 goalsAgainst, 
 points,
 isQualified 
}: { 
 position: number
 teamName: string
 played: number
 won: number
 drawn: number
 lost: number
 goalsFor: number
 goalsAgainst: number
 points: number
 isQualified: boolean
}) {
 const goalDiff = goalsFor - goalsAgainst
 
 return (
 <tr className="border-b border-[#2D2D44] hover:bg-[#1E1E2D]/50 transition-colors">
 <td className="py-2 px-3">
 <div className={`w-6 h-6 flex items-center justify-center text-xs font-bold pixel-number ${
 position <= 2 ? 'bg-emerald-500 text-white' : 'bg-[#1E1E2D] text-[#8B8BA7]'
 }`}>
 {position}
 </div>
 </td>
 <td className="py-2 px-3">
 <span className="text-sm text-white">{teamName}</span>
 {isQualified && <span className="ml-2 text-xs text-emerald-400">✓</span>}
 </td>
 <td className="py-2 px-3 text-center text-sm stat-number">{played}</td>
 <td className="py-2 px-3 text-center text-sm stat-number text-emerald-400">{won}</td>
 <td className="py-2 px-3 text-center text-sm stat-number">{drawn}</td>
 <td className="py-2 px-3 text-center text-sm stat-number text-red-400">{lost}</td>
 <td className="py-2 px-3 text-center text-sm stat-number">{goalsFor}:{goalsAgainst}</td>
 <td className="py-2 px-3 text-center text-sm stat-number">{goalDiff > 0 ? '+' : ''}{goalDiff}</td>
 <td className="py-2 px-3 text-center">
 <span className="font-bold pixel-number">{points}</span>
 </td>
 </tr>
 )
}

// 小组赛分组组件
function GroupSection({ group }: { group: CupGroup }) {
 const standings = group.standings || {}
 const teamIds = group.team_ids || []
 
 // 按积分排序
 const sortedTeams = teamIds.map((teamId, index) => {
 const standing = standings[teamId] || { played: 0, won: 0, drawn: 0, lost: 0, goals_for: 0, goals_against: 0, points: 0 }
 const teamName = group.teams?.find(t => t.id === teamId)?.name || `球队${index + 1}`
 return {
 position: index + 1,
 teamId,
 teamName,
 ...standing,
 isQualified: group.qualified_team_ids?.includes(teamId) || false
 }
 }).sort((a, b) => b.points - a.points || (b.goals_for - b.goals_against) - (a.goals_for - a.goals_against))
 
 // 重新分配位置
 sortedTeams.forEach((team, idx) => {
 team.position = idx + 1
 })

 return (
 <div className="bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-sm overflow-hidden hover:-translate-y-1 transition-all">
 <div className="px-4 py-3 bg-[#0D7377]/20 border-b border-[#2D2D44]">
 <h4 className="font-bold text-white">小组 {group.name}</h4>
 </div>
 <div className="overflow-x-auto">
 <table className="w-full text-sm">
 <thead>
 <tr className="text-left text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
 <th className="py-2 px-3 font-medium">排名</th>
 <th className="py-2 px-3 font-medium">球队</th>
 <th className="py-2 px-3 font-medium text-center">赛</th>
 <th className="py-2 px-3 font-medium text-center">胜</th>
 <th className="py-2 px-3 font-medium text-center">平</th>
 <th className="py-2 px-3 font-medium text-center">负</th>
 <th className="py-2 px-3 font-medium text-center">进/失</th>
 <th className="py-2 px-3 font-medium text-center">净</th>
 <th className="py-2 px-3 font-medium text-center">积分</th>
 </tr>
 </thead>
 <tbody>
 {sortedTeams.map((team) => (
 <GroupStandingRow
 key={team.teamId}
 position={team.position}
 teamName={team.teamName}
 played={team.played}
 won={team.won}
 drawn={team.drawn}
 lost={team.lost}
 goalsFor={team.goals_for}
 goalsAgainst={team.goals_against}
 points={team.points}
 isQualified={team.isQualified}
 />
 ))}
 </tbody>
 </table>
 </div>
 </div>
 )
}

// 统计行组件（射手榜/助攻榜/零封榜）
function StatsRow({ rank, name, team, value, label }: { rank: number; name: string; team: string; value: number; label: string }) {
 const rankColors = [
 'bg-amber-500 text-black',
 'bg-slate-300 text-black',
 'bg-orange-400 text-black',
 'bg-[#1E1E2D] text-[#8B8BA7]'
 ]
 
 return (
 <div className="flex items-center gap-4 py-3 border-b border-[#2D2D44] last:border-0">
 <div className={`w-7 h-7 flex items-center justify-center text-sm font-bold pixel-number ${rankColors[Math.min(rank - 1, 3)]}`}>
 {rank}
 </div>
 <div className="flex-1 min-w-0">
 <p className="font-medium text-white truncate">{name}</p>
 <p className="text-xs text-[#8B8BA7]">{team}</p>
 </div>
 <div className="text-right">
 <p className="font-bold pixel-number text-lg">{value}</p>
 <p className="text-xs text-[#8B8BA7]">{label}</p>
 </div>
 </div>
 )
}

// 树状图比赛卡片
function TreeMatchCard({ match, showTBD }: { match?: CupFixture; showTBD?: boolean }) {
 if (showTBD || !match) {
 return (
 <div className="w-28 p-2 bg-[#1A1A25]/50 border border-dashed border-[#3D3D55] shadow-pixel-sm">
 <div className="space-y-1">
 <div className="flex items-center justify-between text-xs text-[#4B4B6A]">
 <span className="truncate flex-1">待定</span>
 <span className="ml-1 font-bold stat-number min-w-[16px] text-right">-</span>
 </div>
 <div className="flex items-center justify-between text-xs text-[#4B4B6A]">
 <span className="truncate flex-1">待定</span>
 <span className="ml-1 font-bold stat-number min-w-[16px] text-right">-</span>
 </div>
 </div>
 </div>
 )
 }

 const isFinished = match.status === 'finished'
 const winner = isFinished && match.home_score != null && match.away_score != null
 ? match.home_score > match.away_score ? 'home' : match.away_score > match.home_score ? 'away' : null
 : null
 
 return (
 <div className="w-28 p-2 bg-[#1A1A25] border-2 border-[#2D2D44] shadow-pixel-sm hover:border-[#0D7377]/50 hover:-translate-y-1 transition-all">
 <div className="space-y-1">
 <div className={`flex items-center justify-between text-xs ${winner === 'home' ? 'text-emerald-400 font-medium' : 'text-white'}`}>
 <span className="truncate flex-1">{match.home_team.name}</span>
 <span className="ml-1 font-bold stat-number min-w-[16px] text-right">
 {isFinished ? match.home_score : '-'}
 </span>
 </div>
 <div className={`flex items-center justify-between text-xs ${winner === 'away' ? 'text-emerald-400 font-medium' : 'text-white'}`}>
 <span className="truncate flex-1">{match.away_team.name}</span>
 <span className="ml-1 font-bold stat-number min-w-[16px] text-right">
 {isFinished ? match.away_score : '-'}
 </span>
 </div>
 </div>
 </div>
 )
}

// 树状淘汰赛对阵组件
function KnockoutTreeBracket({ fixtures }: { fixtures: CupFixture[] }) {
 // 按阶段分组
 const fixturesByStage: Record<string, CupFixture[]> = {
 ROUND_32: [],
 ROUND_16: [],
 QUARTER: [],
 SEMI: [],
 FINAL: [],
 }
 
 fixtures.forEach(f => {
 if (f.cup_stage && fixturesByStage[f.cup_stage]) {
 fixturesByStage[f.cup_stage].push(f)
 }
 })

 // 确定树状图包含哪些阶段（从最早有数据的阶段开始，如果没有则从32强开始）
 const allStages = ['ROUND_32', 'ROUND_16', 'QUARTER', 'SEMI', 'FINAL'] as const
 const firstStageWithData = allStages.find(s => fixturesByStage[s].length > 0)
 const startStageIndex = firstStageWithData ? allStages.indexOf(firstStageWithData) : 0
 const stageOrder = allStages.slice(startStageIndex)
 
 if (stageOrder.length === 0) {
 return (
 <div className="text-center py-12">
 <GitBranch className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
 <p className="text-[#8B8BA7]">淘汰赛尚未开始</p>
 <p className="text-xs text-[#4B4B6A] mt-2">小组赛结束后将生成对阵</p>
 </div>
 )
 }

 // 计算每个阶段应该有多少场比赛
 const getExpectedMatchCount = (stage: string): number => {
 switch (stage) {
 case 'ROUND_32': return 16
 case 'ROUND_16': return 8
 case 'QUARTER': return 4
 case 'SEMI': return 2
 case 'FINAL': return 1
 default: return 0
 }
 }

 // 构建完整的对阵数据结构
 const buildBracketData = () => {
 const bracket: Record<string, (CupFixture | null)[]> = {}
 
 stageOrder.forEach(stage => {
 const expectedCount = getExpectedMatchCount(stage)
 const existingMatches = fixturesByStage[stage]
 
 // 创建完整数量的比赛槽位
 bracket[stage] = Array(expectedCount).fill(null)
 
 // 填充已有的比赛数据
 existingMatches.forEach((match, index) => {
 if (index < expectedCount) {
 bracket[stage][index] = match
 }
 })
 })
 
 return bracket
 }

 const bracketData = buildBracketData()
 const stageCount = stageOrder.length
 
 // 计算每个阶段的间距
 const getSpacing = (stageIndex: number) => {
 return 60 * Math.pow(2, stageCount - stageIndex - 1)
 }

 return (
 <div className="overflow-x-auto pb-4">
 <div className="inline-block">
 <div className="flex" style={{ minHeight: `${60 + 16 * 60}px` }}>
 {stageOrder.map((stage, stageIndex) => {
 const matches = bracketData[stage]
 const config = CUP_STAGE_CONFIG[stage]
 const spacing = getSpacing(stageIndex)
 const totalHeight = (matches.length - 1) * spacing + 40
 
 return (
 <div 
 key={stage} 
 className="flex flex-col items-center relative"
 style={{ width: '140px', minHeight: `${totalHeight}px` }}
 >
 {/* 阶段标题 */}
 <div className={`mb-4 px-3 py-1 rounded-none ${config.color} text-white text-xs font-medium whitespace-nowrap`}>
 {config.icon} {config.name}
 </div>
 
 {/* 比赛列表容器 */}
 <div className="relative flex-1" style={{ width: '100%', height: `${totalHeight}px` }}>
 {matches.map((match, matchIndex) => {
 const top = matchIndex * spacing
 
 return (
 <div
 key={`${stage}-${matchIndex}`}
 className="absolute left-1/2 -translate-x-1/2"
 style={{ top: `${top}px` }}
 >
 <TreeMatchCard match={match || undefined} showTBD={!match} />
 </div>
 )
 })}
 </div>
 
 {/* 连接线（除了最后一个阶段） */}
 {stageIndex < stageCount - 1 && (
 <svg 
 className="absolute pointer-events-none"
 style={{
 left: '120px',
 top: '40px',
 width: '40px',
 height: `${totalHeight}px`,
 }}
 >
 {matches.map((_, matchIndex) => {
 if (matchIndex % 2 !== 0) return null
 
 const y1 = matchIndex * spacing + 20
 const y2 = (matchIndex + 1) * spacing + 20
 const midY = (y1 + y2) / 2
 
 return (
 <g key={`line-${matchIndex}`}>
 <line x1="0" y1={y1} x2="10" y2={y1} stroke="#3D3D55" strokeWidth="1" />
 <line x1="0" y1={y2} x2="10" y2={y2} stroke="#3D3D55" strokeWidth="1" />
 <line x1="10" y1={y1} x2="10" y2={y2} stroke="#3D3D55" strokeWidth="1" />
 <line x1="10" y1={midY} x2="30" y2={midY} stroke="#3D3D55" strokeWidth="1" />
 <circle cx="10" cy={midY} r="2" fill="#0D7377" />
 </g>
 )
 })}
 </svg>
 )}
 </div>
 )
 })}
 </div>
 </div>
 
 {/* 图例 */}
 <div className="mt-4 flex items-center justify-center gap-6 text-xs text-[#8B8BA7]">
 <div className="flex items-center gap-2">
 <div className="w-3 h-3 bg-emerald-500" />
 <span>晋级球队</span>
 </div>
 <div className="flex items-center gap-2">
 <div className="w-3 h-3 bg-[#1A1A25] border border-dashed border-[#3D3D55]" />
 <span>待定</span>
 </div>
 </div>
 </div>
 )
}



function CupDetail() {
 const { id } = useParams<{ id: string }>()
 const navigate = useNavigate()
 const { cup, loading: cupLoading, error: cupError } = useCupDetail(id)
 
 // 根据杯赛类型设置默认 Tab：有小组赛的默认显示小组赛，否则显示淘汰赛
 const defaultTab: TabType = cup?.has_group_stage ? 'groups' : 'knockout'
 const [activeTab, setActiveTab] = useState<TabType>(defaultTab)
 const [selectedSeasonId, setSelectedSeasonId] = useState<string | undefined>(undefined)
 
 const { seasons, loading: seasonsLoading } = useSeasons()
 const { groups, loading: groupsLoading } = useCupGroups(id)
 const { fixtures, loading: fixturesLoading } = useCupFixtures(id)
 const { scorers, loading: scorersLoading } = useCupTopScorers(id, 10)
 const { assists, loading: assistsLoading } = useCupTopAssists(id, 10)
 const { cleanSheets, loading: cleanSheetsLoading } = useCupCleanSheets(id, 10)
 
 // 当杯赛数据加载后，如果没有小组赛，切换到淘汰赛；同时设置选中赛季
 useEffect(() => {
 if (cup) {
 if (!cup.has_group_stage && activeTab === 'groups') {
 setActiveTab('knockout')
 }
 if (!selectedSeasonId) {
 setSelectedSeasonId(cup.season_id)
 }
 }
 }, [cup, activeTab, selectedSeasonId])
 
 // 赛季切换：查找对应赛季同类型杯赛并跳转
 const handleSeasonChange = async (seasonId: string) => {
 if (!cup || seasonId === cup.season_id) return
 setSelectedSeasonId(seasonId)
 
 // 查找该赛季对应类型的杯赛
 try {
 const response = await api.get<{ id: string }>(`/cups/by-code/${cup.code}?season_id=${seasonId}`)
 if (response.success && response.data && response.data.id) {
 navigate(`/cups/${response.data.id}`)
 }
 } catch (err) {
 console.error('切换赛季失败:', err)
 }
 }
 
 if (cupLoading) {
 return (
 <div className="max-w-[1200px]">
 <div className="h-8 w-32 bg-[#1E1E2D] animate-pulse mb-4" />
 <div className="h-48 bg-[#1E1E2D] animate-pulse" />
 </div>
 )
 }
 
 if (!cup) {
 return (
 <div className="max-w-[1200px] text-center py-20">
 <Trophy className="w-16 h-16 text-[#4B4B6A] mx-auto mb-4" />
 <h2 className="text-xl font-bold text-white mb-2">杯赛未找到</h2>
 <p className="text-[#8B8BA7] mb-2">该杯赛不存在或已被删除</p>
 {cupError && (
 <p className="text-red-400 text-sm mb-6">错误: {cupError}</p>
 )}
 <Link to="/cups" className="btn-primary inline-flex items-center gap-2">
 <ChevronLeft className="w-4 h-4" />
 返回杯赛列表
 </Link>
 </div>
 )
 }

 const config = CUP_CONFIG[cup.code] || CUP_CONFIG.LIGHTNING_CUP
 const isLightningCup = cup.code === 'LIGHTNING_CUP'
 
 // 筛选淘汰赛比赛（包括闪电杯淘汰赛和杰尼杯比赛，不包括预选赛）
 const knockoutFixtures = fixtures.filter(f => 
 f.cup_stage && 
 f.cup_stage !== 'GROUP' && 
 f.cup_stage !== 'ROUND_48'
 )
 
 // 预选赛比赛（单独显示）
 const preliminaryFixtures = fixtures.filter(f => f.cup_stage === 'ROUND_48')

 return (
 <div className="max-w-[1200px]">
 {/* 返回按钮和所有杯赛链接 */}
 <div className="flex items-center justify-between mb-4">
 <Link 
 to="/cups"
 className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors"
 >
 <ChevronLeft className="w-4 h-4" />
 返回杯赛列表
 </Link>
 <Link 
 to="/cups/all"
 className="inline-flex items-center gap-1 text-sm text-[#0D7377] hover:text-white transition-colors"
 >
 <List className="w-4 h-4" />
 所有杯赛
 </Link>
 </div>

 {/* 杯赛信息头部 */}
 <div className="card mb-6 bg-[#0D4A4D]/30">
 <div className="flex items-start justify-between">
 <div className="flex items-center gap-4">
 <div className={`w-16 h-16 bg-${isLightningCup ? 'amber-500' : 'emerald-500'} flex items-center justify-center text-3xl shadow-pixel`}>
 {config.icon}
 </div>
 <div>
 <h1 className="text-2xl font-bold text-white">{cup.name}</h1>
 <div className="flex items-center gap-3 mt-2">
 <span className="text-sm text-[#8B8BA7]">第{cup.season_number}赛季</span>
 <span className="text-[#4B4B6A]">·</span>
 <span className={`text-sm ${cup.status === 'ongoing' ? 'text-emerald-400' : cup.status === 'finished' ? 'text-[#8B8BA7]' : 'text-amber-400'}`}>
 {cup.status === 'ongoing' ? '进行中' : cup.status === 'finished' ? '已结束' : '未开始'}
 </span>
 {cup.winner_team_name && (
 <>
 <span className="text-[#4B4B6A]">·</span>
 <span className="text-sm text-amber-400">🏆 {cup.winner_team_name}</span>
 </>
 )}
 </div>
 </div>
 </div>
 <div className="text-right hidden md:block">
 <div className="flex items-center gap-4 text-sm">
 <div className="flex items-center gap-1.5">
 <Users className="w-4 h-4 text-[#8B8BA7]" />
 <span className="text-[#8B8BA7]">{cup.total_teams} 支球队</span>
 </div>
 {cup.has_group_stage && (
 <div className="flex items-center gap-1.5">
 <Grid3X3 className="w-4 h-4 text-[#8B8BA7]" />
 <span className="text-[#8B8BA7]">{cup.group_count} 个小组</span>
 </div>
 )}
 </div>
 <p className="text-xs text-[#4B4B6A] mt-2">
 {isLightningCup ? '小组赛3轮 + 淘汰赛5轮' : '预选赛 + 淘汰赛5轮'}
 </p>
 </div>
 </div>
 </div>

 {/* Tab 导航 + 赛季选择器 */}
 <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
 <div className="flex flex-wrap gap-2">
 {cup.has_group_stage && (
 <TabButton active={activeTab === 'groups'} onClick={() => setActiveTab('groups')}>
 <div className="flex items-center gap-2">
 <Grid3X3 className="w-4 h-4" />
 小组赛
 </div>
 </TabButton>
 )}
 <TabButton active={activeTab === 'knockout'} onClick={() => setActiveTab('knockout')}>
 <div className="flex items-center gap-2">
 <GitBranch className="w-4 h-4" />
 淘汰赛
 </div>
 </TabButton>
 <TabButton active={activeTab === 'fixtures'} onClick={() => setActiveTab('fixtures')}>
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
 <TabButton active={activeTab === 'clean-sheets'} onClick={() => setActiveTab('clean-sheets')}>
 <div className="flex items-center gap-2">
 <Shield className="w-4 h-4" />
 零封榜
 </div>
 </TabButton>
 </div>
 
 {!seasonsLoading && seasons.length > 0 && (
 <SeasonSelector 
 seasons={seasons} 
 selectedSeasonId={selectedSeasonId} 
 onChange={handleSeasonChange} 
 />
 )}
 </div>

 {/* Tab 内容 */}
 <div className="card">
 {/* 小组赛 */}
 {activeTab === 'groups' && cup.has_group_stage && (
 <div>
 <div className="flex items-center justify-between mb-4">
 <h3 className="text-lg font-semibold">小组赛分组</h3>
 <div className="flex items-center gap-4 text-xs">
 <div className="flex items-center gap-1.5">
 <div className="w-3 h-3 bg-emerald-500" />
 <span className="text-[#8B8BA7]">晋级区（前2名）</span>
 </div>
 </div>
 </div>
 
 {groupsLoading ? (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {[1, 2, 3, 4].map(i => (
 <div key={i} className="h-48 bg-[#1E1E2D] animate-pulse" />
 ))}
 </div>
 ) : groups.length === 0 ? (
 <div className="text-center py-12">
 <Grid3X3 className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
 <p className="text-[#8B8BA7]">暂无小组赛分组数据</p>
 </div>
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {groups.map(group => (
 <GroupSection key={group.id} group={group} />
 ))}
 </div>
 )}
 </div>
 )}

 {/* 淘汰赛 */}
 {activeTab === 'knockout' && (
 <div>
 {/* 预选赛（如果有） */}
 {preliminaryFixtures.length > 0 && (
 <div className="mb-8">
 <div className="flex items-center gap-2 mb-4">
 <h3 className="text-lg font-semibold">预选赛</h3>
 <span className="text-xs text-[#8B8BA7]">({preliminaryFixtures.length} 场)</span>
 </div>
 {fixturesLoading ? (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {[1, 2].map(i => (
 <div key={i} className="h-32 bg-[#1E1E2D] animate-pulse" />
 ))}
 </div>
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {preliminaryFixtures.map(match => (
 <MatchCard key={match.id} match={match} />
 ))}
 </div>
 )}
 </div>
 )}
 
 {/* 树状图淘汰赛 */}
 <div>
 <h3 className="text-lg font-semibold mb-4">
 {cup.has_group_stage ? '淘汰赛对阵' : '正赛对阵'}
 </h3>
 {fixturesLoading ? (
 <div className="h-64 bg-[#1E1E2D] animate-pulse" />
 ) : knockoutFixtures.length === 0 && preliminaryFixtures.length === 0 ? (
 <div className="text-center py-12">
 <GitBranch className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
 <p className="text-[#8B8BA7]">淘汰赛尚未开始</p>
 <p className="text-xs text-[#4B4B6A] mt-2">
 {cup.has_group_stage ? '小组赛结束后将生成对阵' : '比赛即将开始'}
 </p>
 </div>
 ) : (
 <KnockoutTreeBracket fixtures={knockoutFixtures} />
 )}
 </div>
 </div>
 )}

 {/* 赛程 */}
 {activeTab === 'fixtures' && (
 <div>
 <h3 className="text-lg font-semibold mb-4">全部赛程</h3>
 {fixturesLoading ? (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {[1, 2, 3, 4].map(i => (
 <div key={i} className="h-32 bg-[#1E1E2D] animate-pulse" />
 ))}
 </div>
 ) : fixtures.length === 0 ? (
 <div className="text-center py-12">
 <Calendar className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
 <p className="text-[#8B8BA7]">暂无赛程数据</p>
 </div>
 ) : (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {fixtures.slice(0, 20).map(match => (
 <MatchCard key={match.id} match={match} />
 ))}
 </div>
 )}
 </div>
 )}

 {/* 射手榜 */}
 {activeTab === 'scorers' && (
 <div>
 <h3 className="text-lg font-semibold mb-4">射手榜</h3>
 {scorersLoading ? (
 <div className="space-y-2">
 {[1, 2, 3, 4, 5].map(i => (
 <div key={i} className="h-14 bg-[#1E1E2D] animate-pulse" />
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

 {/* 助攻榜 */}
 {activeTab === 'assists' && (
 <div>
 <h3 className="text-lg font-semibold mb-4">助攻榜</h3>
 {assistsLoading ? (
 <div className="space-y-2">
 {[1, 2, 3, 4, 5].map(i => (
 <div key={i} className="h-14 bg-[#1E1E2D] animate-pulse" />
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

 {/* 零封榜 */}
 {activeTab === 'clean-sheets' && (
 <div>
 <h3 className="text-lg font-semibold mb-4">零封榜</h3>
 {cleanSheetsLoading ? (
 <div className="space-y-2">
 {[1, 2, 3, 4, 5].map(i => (
 <div key={i} className="h-14 bg-[#1E1E2D] animate-pulse" />
 ))}
 </div>
 ) : cleanSheets.length === 0 ? (
 <div className="text-center py-12">
 <Shield className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
 <p className="text-[#8B8BA7]">暂无零封数据</p>
 </div>
 ) : (
 <div>
 {cleanSheets.map(cs => (
 <StatsRow 
 key={cs.player_id}
 rank={cs.rank}
 name={cs.player_name}
 team={cs.team_name}
 value={cs.clean_sheets}
 label="零封"
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

export default CupDetail
