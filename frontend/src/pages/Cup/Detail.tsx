import { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import api from '../../api/client'
import { 
  Trophy, ChevronLeft, Calendar, Grid3x3 as Grid3X3, 
  GitBranch, ListBox as List, Target 
} from '../../components/ui/pixel-icons'
import { CupBadge } from '../../components/cup/CupBadge'
import { 
 useCupDetail, 
 useCupGroups, 
 useCupFixtures, 
 useCupLeaderboard
} from '../../hooks/useCups'
import { useCupAwards } from '../../hooks/useAwards'
import { DataKingsRow } from '../../components/awards'
import { useSeasons } from '../../hooks/useSeasons'
import type { CupFixture, CupGroup } from '../../types/cup'
import type { Season } from '../../types/season'
import type { LeaderboardType } from '../../types/leaderboard'
import { CUP_STAGE_CONFIG } from '../../types/cup'
import { LeaderboardSidebar, getLeaderboardFormat } from '../../components/leaderboard/LeaderboardSidebar'
import { LeaderboardTable } from '../../components/leaderboard/LeaderboardTable'
import { RecordsBoard } from '../../components/records/RecordsBoard'

type TabType = 'groups' | 'knockout' | 'fixtures' | 'stats' | 'records' | 'awards'

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
 className="appearance-none bg-[#1E1E2D] border-2 border-[#2D2D44] text-white text-sm px-4 py-2 pr-8 focus:outline-none focus:border-[#0D7377] focus:ring-1 focus:ring-[#0D7377] cursor-pointer"
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

type WinnerSide = 'home' | 'away' | null

function getWinnerSide(match: CupFixture | null): WinnerSide {
 if (!match || match.status !== 'finished') return null
 if (match.winner_team_id === match.home_team.id) return 'home'
 if (match.winner_team_id === match.away_team.id) return 'away'
 if (match.home_score == null || match.away_score == null) return null
 if (match.home_score > match.away_score) return 'home'
 if (match.away_score > match.home_score) return 'away'
 return null
}

function hasPenaltyScore(match: CupFixture) {
 return match.resolution === 'penalties' && match.penalty_score?.home != null && match.penalty_score?.away != null
}

function MatchScore({ match, className = '' }: { match: CupFixture; className?: string }) {
 return (
 <div>
 <div className={className}>
 {match.home_score ?? '-'}:{match.away_score ?? '-'}
 </div>
 {hasPenaltyScore(match) && (
 <div className="mt-0.5 text-[10px] font-black text-[#D6A619]">
 点球 {match.penalty_score!.home}:{match.penalty_score!.away}
 </div>
 )}
 </div>
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
 <MatchScore match={match} className={`text-2xl font-bold stat-number ${isLive ? 'text-red-400' : 'text-white'}`} />
 ) : (
 <div className="text-lg font-bold pixel-number text-[#4B4B6A]">VS</div>
 )}
 <p className="text-xs text-[#8B8BA7] mt-1">
 第{match.season_day}天
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

// 小组赛表格行组件
function GroupStandingRow({
 position,
 teamId,
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
 teamId: string
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
 <Link to={`/teams/${teamId}`} className="text-sm text-white hover:text-[#C6F135] transition-colors">
 {teamName}
 </Link>
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
 teamId={team.teamId}
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

// 淘汰赛比赛行
function KnockoutMatchRow({ match }: { match: CupFixture }) {
 const isFinished = match.status === 'finished'
 const isLive = match.status === 'ongoing'
 const winner = getWinnerSide(match)

 return (
 <div className="bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-sm hover:border-[#0D7377]/50 transition-colors">
 <div className="grid grid-cols-[minmax(0,1fr)_88px_minmax(0,1fr)] items-center gap-3 px-4 py-3">
 <div className={`min-w-0 ${winner === 'home' ? 'text-[#C6F135]' : 'text-white'}`}>
 <Link
 to={`/teams/${match.home_team.id}`}
 className="block truncate font-bold hover:text-[#C6F135] transition-colors"
 onClick={(e) => e.stopPropagation()}
 >
 {match.home_team.name}
 </Link>
 </div>

 <div className="text-center">
 {isFinished || isLive ? (
 <MatchScore match={match} className={`text-lg font-black stat-number ${isLive ? 'text-red-400' : 'text-white'}`} />
 ) : (
 <div className="text-xs font-black pixel-number text-[#4B4B6A]">VS</div>
 )}
 <div className="mt-1 text-[10px] font-bold text-[#4B4B6A]">第{match.season_day}天</div>
 </div>

 <div className={`min-w-0 text-right ${winner === 'away' ? 'text-[#C6F135]' : 'text-white'}`}>
 <Link
 to={`/teams/${match.away_team.id}`}
 className="block truncate font-bold hover:text-[#C6F135] transition-colors"
 onClick={(e) => e.stopPropagation()}
 >
 {match.away_team.name}
 </Link>
 </div>
 </div>
 {isLive && (
 <div className="border-t border-[#2D2D44] px-4 py-1 text-xs font-bold text-red-400">进行中</div>
 )}
 </div>
 )
}

// 赛程轮次列表
function CupScheduleList({ fixtures }: { fixtures: CupFixture[] }) {
 const fixturesByStage: Record<string, CupFixture[]> = {
 GROUP: [],
 ROUND_48: [],
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

 const stageOrder = ['GROUP', 'ROUND_48', 'ROUND_32', 'ROUND_16', 'QUARTER', 'SEMI', 'FINAL']
 const visibleStages = stageOrder.filter(stage => fixturesByStage[stage].length > 0)
 
 if (visibleStages.length === 0) {
 return (
 <div className="text-center py-12">
 <Calendar className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
 <p className="text-[#8B8BA7]">暂无赛程数据</p>
 </div>
 )
 }

 return (
 <div className="space-y-6">
 {visibleStages.map((stage, stageIndex) => {
 const config = CUP_STAGE_CONFIG[stage]
 const matches = fixturesByStage[stage]

 return (
 <section key={stage} className="border-2 border-[#2D2D44] bg-[#0B0D14] shadow-pixel-sm overflow-hidden">
 <div className="flex items-center justify-between border-b-2 border-[#2D2D44] bg-[#12121A] px-4 py-3">
 <div className="flex items-center gap-3">
 <div className={`h-6 w-2 ${config.color}`} />
 <h4 className="text-lg font-black text-white">{config.name}</h4>
 </div>
 <span className="text-xs font-bold text-[#8B8BA7]">{matches.length} 场</span>
 </div>
 <div className="divide-y divide-[#2D2D44]">
 {matches.map(match => (
 <KnockoutMatchRow key={match.id} match={match} />
 ))}
 </div>
 {stageIndex < visibleStages.length - 1 && (
 <div className="border-t border-[#2D2D44] px-4 py-2 text-xs text-[#4B4B6A]">
 下一阶段：{CUP_STAGE_CONFIG[visibleStages[stageIndex + 1]].name}
 </div>
 )}
 </section>
 )
 })}
 </div>
 )
}

function TeamMark({ name, muted = false }: { name: string; muted?: boolean }) {
 const letters = name
 .replace(/\s+/g, '')
 .slice(0, 2)
 .toUpperCase()

 return (
 <div className={`w-9 h-9 shrink-0 rounded-full border-2 flex items-center justify-center text-[11px] font-black ${
 muted
 ? 'bg-[#10131C] border-[#30334D] text-[#596070]'
 : 'bg-[#07191B] border-[#0D7377] text-[#7DE6DF]'
 }`}>
 {letters}
 </div>
 )
}

type BracketSlot = CupFixture | null

const EXPECTED_STAGE_MATCHES: Record<string, number> = {
 ROUND_32: 16,
 ROUND_16: 8,
 QUARTER: 4,
 SEMI: 2,
 FINAL: 1,
}

function getExpectedStageCount(stage: string, fallback: number) {
 return Math.max(EXPECTED_STAGE_MATCHES[stage] || fallback, fallback)
}

function BracketMatchPill({ match, final = false }: { match: BracketSlot; final?: boolean }) {
 const isPlaceholder = !match
 const isFinished = Boolean(match && match.status === 'finished')
 const winner = getWinnerSide(match)

 if (isPlaceholder) {
 return (
 <div className={`relative mx-auto ${
 final ? 'w-full max-w-[420px] px-3 py-2' : 'w-full max-w-[320px] px-2 py-1.5'
 }`}>
 <div className={`grid items-center gap-3 border-y-2 border-dashed ${
 final ? 'grid-cols-[minmax(0,1fr)_96px_minmax(0,1fr)] border-[#D6A619]/60 py-2' : 'grid-cols-[minmax(0,1fr)_88px_minmax(0,1fr)] border-[#30334D] py-1.5'
 }`}>
 <div className="flex min-w-0 items-center gap-2 text-[#596070]">
 <TeamMark name="待定" muted />
 <span className={`truncate font-black ${final ? 'text-base' : 'text-sm'}`}>待定</span>
 </div>
 <div className="text-center">
 <div className={`${final ? 'text-sm' : 'text-xs'} font-black pixel-number text-[#4B4B6A]`}>VS</div>
 <div className="mt-1 text-[10px] font-bold text-[#4B4B6A]">未定</div>
 </div>
 <div className="flex min-w-0 items-center justify-end gap-2 text-right text-[#596070]">
 <span className={`truncate font-black ${final ? 'text-base' : 'text-sm'}`}>待定</span>
 <TeamMark name="待定" muted />
 </div>
 </div>
 </div>
 )
 }

 return (
 <div className={`relative mx-auto ${
 final ? 'w-full max-w-[420px] px-3 py-2' : 'w-full max-w-[320px] px-2 py-1.5'
 }`}>
 <div className={`grid items-center gap-3 border-y-2 ${
 final ? 'grid-cols-[minmax(0,1fr)_96px_minmax(0,1fr)] border-[#D6A619] py-2' : 'grid-cols-[minmax(0,1fr)_88px_minmax(0,1fr)] border-[#30334D] py-1.5'
 }`}>
 <Link
 to={`/teams/${match.home_team.id}`}
 className={`flex min-w-0 items-center gap-2 hover:text-[#C6F135] transition-colors ${
 winner === 'home' ? 'text-white' : winner === 'away' ? 'text-[#69708A]' : 'text-[#E8EAD8]'
 }`}
 >
 <TeamMark name={match.home_team.name} muted={winner === 'away'} />
 <span className={`truncate font-black ${final ? 'text-base' : 'text-sm'}`}>{match.home_team.name}</span>
 </Link>

 <div className="text-center">
 {isFinished || match.status === 'ongoing' ? (
 <MatchScore match={match} className={`${final ? 'text-xl' : 'text-base'} font-black stat-number text-white`} />
 ) : (
 <div className={`${final ? 'text-sm' : 'text-xs'} font-black pixel-number text-[#4B4B6A]`}>VS</div>
 )}
 <div className="mt-1 text-[10px] font-bold text-[#4B4B6A]">第{match.season_day}天</div>
 </div>

 <Link
 to={`/teams/${match.away_team.id}`}
 className={`flex min-w-0 items-center justify-end gap-2 text-right hover:text-[#C6F135] transition-colors ${
 winner === 'away' ? 'text-white' : winner === 'home' ? 'text-[#69708A]' : 'text-[#E8EAD8]'
 }`}
 >
 <span className={`truncate font-black ${final ? 'text-base' : 'text-sm'}`}>{match.away_team.name}</span>
 <TeamMark name={match.away_team.name} muted={winner === 'home'} />
 </Link>
 </div>
 </div>
 )
}

function fillSlots(matches: CupFixture[], count: number): BracketSlot[] {
 return Array.from({ length: count }, (_, index) => matches[index] || null)
}

function getStageSlots(fixturesByStage: Record<string, CupFixture[]>, stage: string) {
 const matches = fixturesByStage[stage] || []
 return fillSlots(matches, getExpectedStageCount(stage, matches.length))
}

function getHalfSlots(fixturesByStage: Record<string, CupFixture[]>, stage: string, half: 'upper' | 'lower') {
 const slots = getStageSlots(fixturesByStage, stage)
 const splitAt = Math.ceil(slots.length / 2)
 return half === 'upper' ? slots.slice(0, splitAt) : slots.slice(splitAt)
}

function getWinnerTeamId(match: BracketSlot) {
 if (!match || match.status !== 'finished') return null
 if (match.winner_team_id) return match.winner_team_id
 if (match.home_score == null || match.away_score == null) return null
 if (match.home_score > match.away_score) return match.home_team.id
 if (match.away_score > match.home_score) return match.away_team.id
 return null
}

function matchIncludesTeam(match: CupFixture, teamIds: Set<string>) {
 return teamIds.has(match.home_team.id) || teamIds.has(match.away_team.id)
}

type BracketRow = { stage: string; matches: BracketSlot[] }

function buildRowsForHalf(
 fixturesByStage: Record<string, CupFixture[]>,
 stages: string[],
 half: 'upper' | 'lower',
 usedByStage: Record<string, Set<string>>
) {
 const rows: BracketRow[] = []
 if (stages.length === 0) return rows

 let previousSlots = getHalfSlots(fixturesByStage, stages[0], half)
 rows.push({ stage: stages[0], matches: previousSlots })

 for (let stageIndex = 1; stageIndex < stages.length; stageIndex += 1) {
 const stage = stages[stageIndex]
 const candidates = [...(fixturesByStage[stage] || [])]
 const fallbackSlots = getHalfSlots(fixturesByStage, stage, half)
 const used = usedByStage[stage] || new Set<string>()
 usedByStage[stage] = used
 const expectedCount = Math.max(1, Math.ceil(previousSlots.length / 2))
 const nextSlots: BracketSlot[] = []

 for (let slotIndex = 0; slotIndex < expectedCount; slotIndex += 1) {
 const sourceSlots = previousSlots.slice(slotIndex * 2, slotIndex * 2 + 2)
 const sourceWinnerIds = new Set(sourceSlots.map(getWinnerTeamId).filter(Boolean) as string[])
 const matchedByWinner = sourceWinnerIds.size > 0
 ? candidates.find(candidate => !used.has(candidate.id) && matchIncludesTeam(candidate, sourceWinnerIds))
 : undefined
 const fallbackMatch = fallbackSlots[slotIndex]
 const matched = matchedByWinner || (fallbackMatch && !used.has(fallbackMatch.id) ? fallbackMatch : undefined)

 if (matched) {
 used.add(matched.id)
 nextSlots.push(matched)
 } else {
 nextSlots.push(null)
 }
 }

 previousSlots = nextSlots
 rows.push({ stage, matches: previousSlots })
 }

 return rows
}

function buildBracketRows(fixturesByStage: Record<string, CupFixture[]>, stages: string[]) {
 const usedByStage: Record<string, Set<string>> = {}
 const upperRows = buildRowsForHalf(fixturesByStage, stages, 'upper', usedByStage)
 const lowerRows = buildRowsForHalf(fixturesByStage, stages, 'lower', usedByStage)
 return { upperRows, lowerRows }
}

function buildBranchPath(fromX: number, fromY: number, toX: number, toY: number) {
 const midY = (fromY + toY) / 2
 return `M ${fromX} ${fromY} V ${midY} H ${toX} V ${toY}`
}

function BracketHalf({
 half,
 rows: inputRows,
}: {
 half: 'upper' | 'lower'
 rows: BracketRow[]
}) {
 const rows = half === 'upper' ? inputRows : [...inputRows].reverse()

 if (rows.length === 0) return null

 const rowGap = 132
 const canvasHeight = rows.length === 1 ? 118 : (rows.length - 1) * rowGap + 118
 const nodeY = (index: number) => 54 + index * rowGap
 const nodeX = (index: number, count: number) => ((index + 0.5) / count) * 1000
 const paths: { d: string; key: string }[] = []

 for (let rowIndex = 0; rowIndex < rows.length - 1; rowIndex += 1) {
 const current = rows[rowIndex]
 const next = rows[rowIndex + 1]
 const currentCount = current.matches.length
 const nextCount = next.matches.length

 if (half === 'upper') {
 current.matches.forEach((_, matchIndex) => {
 const parentIndex = Math.min(Math.floor(matchIndex / 2), nextCount - 1)
 paths.push({
 key: `${current.stage}-${matchIndex}-${next.stage}-${parentIndex}`,
 d: buildBranchPath(
 nodeX(matchIndex, currentCount),
 nodeY(rowIndex) + 38,
 nodeX(parentIndex, nextCount),
 nodeY(rowIndex + 1) - 38
 ),
 })
 })
 } else {
 next.matches.forEach((_, childIndex) => {
 const parentIndex = Math.min(Math.floor(childIndex / 2), currentCount - 1)
 paths.push({
 key: `${current.stage}-${parentIndex}-${next.stage}-${childIndex}`,
 d: buildBranchPath(
 nodeX(parentIndex, currentCount),
 nodeY(rowIndex) + 38,
 nodeX(childIndex, nextCount),
 nodeY(rowIndex + 1) - 38
 ),
 })
 })
 }
 }

 return (
 <div className="relative" style={{ height: `${canvasHeight}px` }}>
 <svg
 className="absolute inset-0 h-full w-full pointer-events-none"
 viewBox={`0 0 1000 ${canvasHeight}`}
 preserveAspectRatio="none"
 shapeRendering="crispEdges"
 >
 {paths.map(path => (
 <path
 key={path.key}
 d={path.d}
 fill="none"
 stroke="#0D7377"
 strokeWidth="3"
 opacity="0.72"
 />
 ))}
 {paths.map(path => (
 <path
 key={`${path.key}-glow`}
 d={path.d}
 fill="none"
 stroke="#C6F135"
 strokeWidth="1"
 opacity="0.42"
 />
 ))}
 </svg>

 {rows.map((row, rowIndex) => {
 return (
 <div
 key={`${half}-${row.stage}`}
 className="absolute left-0 right-0"
 style={{ top: `${nodeY(rowIndex) - 34}px` }}
 >
 <div
 className="grid items-center gap-4"
 style={{ gridTemplateColumns: `repeat(${row.matches.length}, minmax(0, 1fr))` }}
 >
 {row.matches.map((match, matchIndex) => (
 <BracketMatchPill key={match?.id || `${half}-${row.stage}-${matchIndex}`} match={match} />
 ))}
 </div>
 </div>
 )
 })}
 </div>
 )
}

// 上下半区向决赛收拢的淘汰赛对阵
function KnockoutBracketTree({ fixtures }: { fixtures: CupFixture[] }) {
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

 const stageOrder = ['ROUND_32', 'ROUND_16', 'QUARTER', 'SEMI', 'FINAL']
 const visibleStages = stageOrder.filter(stage => fixturesByStage[stage].length > 0)
 const hasData = visibleStages.length > 0

 // 即使淘汰赛还没开始，也显示完整的对阵图（所有队伍显示为"待定"）
 const firstStageIndex = hasData
 ? stageOrder.findIndex(stage => fixturesByStage[stage].length > 0)
 : 0 // 无数据时从 ROUND_32 开始展示空树
 const bracketStages = stageOrder.slice(firstStageIndex, -1)
 const { upperRows, lowerRows } = buildBracketRows(fixturesByStage, bracketStages)

 return (
 <div className="relative overflow-hidden border-2 border-[#2D2D44] bg-[#080B11] px-4 py-6 shadow-pixel-sm">
 <div className="absolute inset-0 opacity-25 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:16px_16px]" />
 <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-[120px] font-black text-white/[0.025] md:text-[180px]">
 CUP
 </div>
 <div className="relative space-y-4">
 <BracketHalf half="upper" rows={upperRows} />

 <div className="flex justify-center">
 <svg width="120" height="42" viewBox="0 0 120 42" shapeRendering="crispEdges" className="pointer-events-none">
 <path d="M60 0 V42" fill="none" stroke="#0D7377" strokeWidth="3" opacity="0.75" />
 <path d="M60 0 V42" fill="none" stroke="#C6F135" strokeWidth="1" opacity="0.45" />
 </svg>
 </div>

 <div className="mx-auto max-w-[520px] border-2 border-[#D6A619] bg-[#0E111A]/95 px-4 py-3 shadow-pixel-sm">
 <div className="mb-2 flex items-center justify-center gap-3 text-sm font-black text-[#D6A619]">
 <span className="h-1 w-12 bg-[#D6A619]" />
 决赛
 <span className="h-1 w-12 bg-[#D6A619]" />
 </div>
 <BracketMatchPill match={fixturesByStage.FINAL[0] || null} final />
 </div>

 <div className="flex justify-center">
 <svg width="120" height="42" viewBox="0 0 120 42" shapeRendering="crispEdges" className="pointer-events-none">
 <path d="M60 0 V42" fill="none" stroke="#0D7377" strokeWidth="3" opacity="0.75" />
 <path d="M60 0 V42" fill="none" stroke="#C6F135" strokeWidth="1" opacity="0.45" />
 </svg>
 </div>

 <BracketHalf half="lower" rows={lowerRows} />
 </div>
 </div>
 )
}



function CupRecordsTab({ cupId }: { cupId: string | undefined }) {
  const [records, setRecords] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!cupId) return
    const fetchRecords = async () => {
      try {
        setLoading(true)
        const res = await api.get(`/cups/${cupId}/records`)
        if (res.success) {
          setRecords(res.data)
        }
      } catch (err) {
        console.error('Failed to fetch cup records:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchRecords()
  }, [cupId])

  return <RecordsBoard records={records} loading={loading} emptyText="暂无杯赛纪录" />
}

function CupDetail() {
 const { id } = useParams<{ id: string }>()
 const navigate = useNavigate()
 const { cup, loading: cupLoading, error: cupError } = useCupDetail(id)
 
 // 根据杯赛类型设置默认 Tab：有小组赛的默认显示小组赛，否则显示淘汰赛
 const defaultTab: TabType = cup?.has_group_stage ? 'groups' : 'knockout'
 const [activeTab, setActiveTab] = useState<TabType>(defaultTab)
 const [selectedSeasonId, setSelectedSeasonId] = useState<string | undefined>(undefined)
 const [leaderboardType, setLeaderboardType] = useState<LeaderboardType>('goals')
 const { awards: cupAwards, loading: awardsLoading } = useCupAwards(id, cup?.season_id)
 
 const { seasons, loading: seasonsLoading } = useSeasons()
 const { groups, loading: groupsLoading } = useCupGroups(id)
 const { fixtures, loading: fixturesLoading } = useCupFixtures(id)
 const { items: leaderboardItems, loading: leaderboardLoading } = useCupLeaderboard(id, leaderboardType, 20)
 
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
 <button 
 onClick={() => navigate(-1)}
 className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors"
 >
 <ChevronLeft className="w-4 h-4" />
 返回上一页
 </button>
 <Link 
 to="/cups/all"
 className="inline-flex items-center gap-1 text-sm text-[#0D7377] hover:text-white transition-colors"
 >
 <List className="w-4 h-4" />
 所有杯赛
 </Link>
 </div>

 {/* 杯赛信息头部 */}
 <div className="flex items-center gap-3 mb-6">
 <CupBadge code={cup.code} size="md" title={`${cup.name} 徽章`} />
 <h1 className="text-lg font-bold text-white">{cup.name}</h1>
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
 <TabButton active={activeTab === 'stats'} onClick={() => setActiveTab('stats')}>
 <div className="flex items-center gap-2">
 <Target className="w-4 h-4" />
 数据
 </div>
 </TabButton>
 <TabButton active={activeTab === 'records'} onClick={() => setActiveTab('records')}>
 <div className="flex items-center gap-2">
 <Target className="w-4 h-4" />
 杯赛纪录
 </div>
 </TabButton>
 <TabButton active={activeTab === 'awards'} onClick={() => setActiveTab('awards')}>
 <div className="flex items-center gap-2">
 <Trophy className="w-4 h-4" />
 杯赛奖项
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
 <div className="p-6">
 {/* 小组赛 */}
 {activeTab === 'groups' && cup.has_group_stage && (
 <div>
 <div className="flex justify-end mb-4">
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

 {/* 淘汰赛正赛 */}
 <div>
 {fixturesLoading ? (
 <div className="h-64 bg-[#1E1E2D] animate-pulse" />
 ) : (
 <KnockoutBracketTree fixtures={knockoutFixtures} />
 )}
 </div>
 </div>
 )}

 {/* 赛程 */}
 {activeTab === 'fixtures' && (
 <div>
 {fixturesLoading ? (
 <div className="space-y-4">
 {[1, 2, 3, 4].map(i => (
 <div key={i} className="h-28 bg-[#1E1E2D] animate-pulse" />
 ))}
 </div>
 ) : fixtures.length === 0 ? (
 <div className="text-center py-12">
 <Calendar className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
 <p className="text-[#8B8BA7]">暂无赛程数据</p>
 </div>
 ) : (
 <CupScheduleList fixtures={fixtures} />
 )}
 </div>
 )}

 {/* 数据 — 通用排行榜 */}
 {activeTab === 'stats' && (
 <div>
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

 {/* 杯赛纪录 */}
 {activeTab === 'records' && (
 <div>
 <CupRecordsTab cupId={id} />
 </div>
 )}

 {/* 杯赛奖项 */}
 {activeTab === 'awards' && (
 <div className="space-y-6">
   {awardsLoading ? (
     <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
       {[1, 2, 3, 4].map(i => <div key={i} className="h-32 bg-[#1E1E2D] animate-pulse" />)}
     </div>
   ) : (
     <>
       <section>
         <DataKingsRow
           goldenBoot={cupAwards?.golden_boot}
           playmaker={cupAwards?.playmaker}
           goldenGlove={cupAwards?.golden_glove}
           goldenWall={cupAwards?.golden_wall}
           size="lg"
           emptyText="该赛季暂无杯赛奖项数据"
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

export default CupDetail
