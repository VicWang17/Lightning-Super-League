import { useState, useEffect } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { Trophy, ChevronRight, Users, Sword as Swords, ChevronLeft } from '../../components/ui/pixel-icons'
import { LeagueBadge } from '../../components/league/LeagueBadge'
import { useLeagueSystems, useLeagues } from '../../hooks/useLeagues'
import api from '../../api/client'
import type { League } from '../../types/league'
import { PageHeader } from '../../components/ui/PageHeader'
import { SegmentedTabs } from '../../components/ui/SegmentedTabs'

// 用户球队类型
interface UserTeam {
 id: string
 name: string
 current_league_id?: string | null
}

// 联赛级别配置
const LEVEL_CONFIG = [
 { name: '超级联赛', color: 'bg-amber-500', bgColor: 'bg-[#12121A]', borderColor: 'border-amber-500/30' },
 { name: '甲级联赛', color: 'bg-slate-400', bgColor: 'bg-[#12121A]', borderColor: 'border-slate-400/30' },
 { name: '乙级联赛', color: 'bg-orange-600', bgColor: 'bg-[#12121A]', borderColor: 'border-orange-600/30' },
 { name: '丙级联赛', color: 'bg-stone-500', bgColor: 'bg-[#12121A]', borderColor: 'border-stone-500/30' },
]

// 联赛卡片组件
function LeagueCard({ league }: { league: League }) {
 const config = LEVEL_CONFIG[league.level - 1]
 
 return (
 <Link
 to={`/leagues/${league.id}`}
 className="group block"
 >
 <div className={`relative p-5 bg-[#12121A] border-2 ${config.borderColor} shadow-pixel-sm hover:-translate-y-1 transition-all duration-200 overflow-hidden`}>
 {/* 背景装饰 */}
 <div className="absolute top-0 right-0 w-32 h-32" />

 <div className="relative">
 <div className="flex items-start justify-between">
 <div className="flex items-center gap-3">
 <div className="w-12 h-12 bg-[#050609] border-2 border-white/10 flex items-center justify-center shadow-pixel">
 <LeagueBadge
 systemCode={league.system_code}
 level={league.level}
 title={`${league.name} 徽章`}
 />
 </div>
 <div>
 <h3 className="text-lg font-bold text-white group-hover:text-[#0D7377] transition-colors">
 {league.name}
 </h3>
 <div className="flex items-center gap-2 mt-1">
 <LeagueBadge systemCode={league.system_code} size="sm" title={`${league.system_name} 徽章`} />
 <span className="text-sm text-[#8B8BA7]">{league.system_name}</span>
 </div>
 </div>
 </div>
 <ChevronRight className="w-5 h-5 text-[#4B4B6A] group-hover:text-white transition-colors" />
 </div>
 
 <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
 <div className="flex items-center gap-4">
 <div className="flex items-center gap-1.5">
 <Users className="w-4 h-4 text-[#8B8BA7]" />
 <span className="text-sm text-[#8B8BA7]">{league.teams_count || 8} 支球队</span>
 </div>
 <div className="flex items-center gap-1.5">
 <Swords className="w-4 h-4 text-[#8B8BA7]" />
 <span className="text-sm text-[#8B8BA7]">14 轮比赛</span>
 </div>
 </div>
 <span className={`text-xs px-2 py-1 rounded-none bg-[#2D2D44] border-2 border-white/10`}>
 {league.level === 1 ? '顶级联赛' : `第${league.level}级别`}
 </span>
 </div>
 </div>
 </div>
 </Link>
 )
}

// 体系区块组件
function SystemSection({ systemCode, systemName, description }: { systemCode: string; systemName: string; description?: string }) {
 const { leagues, loading } = useLeagues(systemCode)
 
 return (
 <div className="mb-8">
 <div className="flex items-center gap-3 mb-4">
 <div className="w-10 h-10 bg-[#050609] border-2 border-white/10 flex items-center justify-center shadow-pixel-sm">
 <LeagueBadge systemCode={systemCode} size="sm" title={`${systemName} 徽章`} />
 </div>
 <div>
 <h2 className="text-xl font-bold text-white">{systemName}</h2>
 {description && <p className="text-sm text-[#8B8BA7]">{description}</p>}
 </div>
 </div>
 
 {loading ? (
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {[1, 2, 3, 4].map(i => (
 <div key={i} className="h-32 bg-[#1E1E2D] animate-pulse" />
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
 )
}

function LeagueList() {
 const navigate = useNavigate()
 const { systems, loading: systemsLoading } = useLeagueSystems()
 const [selectedSystem, setSelectedSystem] = useState<string | null>(null)
 const [userLeagueId, setUserLeagueId] = useState<string | null>(null)
 const location = useLocation()
 
 // 判断是否是"所有联赛"页面
 const isAllLeaguesPage = location.pathname === '/leagues/all'
 
 // 获取用户球队所在联赛ID
 useEffect(() => {
 console.log('[LeagueList] 开始获取用户球队信息...')
 api.get<UserTeam>('/teams/my-team').then(response => {
 console.log('[LeagueList] API 响应:', response)
 if (response.success && response.data.current_league_id) {
 console.log('[LeagueList] 设置 league_id:', response.data.current_league_id)
 setUserLeagueId(response.data.current_league_id)
 } else {
 console.log('[LeagueList] 没有 current_league_id, response:', response)
 }
 }).catch(error => {
 console.error('[LeagueList] 获取球队信息失败:', error)
 })
 }, [])
 
 // 如果不是"所有联赛"页面，且已获取到联赛ID，直接导航到当前联赛
 console.log('[LeagueList] 检查重定向: isAllLeaguesPage=', isAllLeaguesPage, 'userLeagueId=', userLeagueId)
 if (!isAllLeaguesPage && userLeagueId) {
 console.log('[LeagueList] 执行重定向到:', `/leagues/${userLeagueId}`)
 return <Navigate to={`/leagues/${userLeagueId}`} replace />
 }
 
 const filteredSystems = selectedSystem 
 ? systems.filter(s => s.code === selectedSystem)
 : systems

 return (
 <div className="max-w-[1200px]">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
      >
        <ChevronLeft className="w-4 h-4" />
        返回上一页
      </button>
 <PageHeader
 icon={Trophy}
 title="联赛体系"
 subtitle="闪电超级联赛共有 4 个联赛体系，32 个联赛，256 支球队"
 />

 {/* 体系筛选 */}
 {systemsLoading ? (
 <div className="flex gap-3 mb-8">
 {[1, 2, 3, 4].map(i => (
 <div key={i} className="h-10 w-24 bg-surface-hover animate-pulse" />
 ))}
 </div>
 ) : (
 <SegmentedTabs
 tabs={[
 { value: 'all', label: '全部' },
 ...systems.map(system => ({
 value: system.code,
 label: system.name,
 icon: () => (
 <LeagueBadge
 systemCode={system.code}
 size="sm"
 title={`${system.name} 徽章`}
 />
 ),
 })),
 ]}
 value={selectedSystem ?? 'all'}
 onChange={(value) => setSelectedSystem(value === 'all' ? null : value)}
 />
 )}

 {/* 联赛列表 */}
 <div className="space-y-8">
 {systemsLoading ? (
 <div className="space-y-8">
 {[1, 2].map(i => (
 <div key={i}>
 <div className="h-8 w-32 bg-[#1E1E2D] animate-pulse mb-4" />
 <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
 {[1, 2, 3, 4].map(j => (
 <div key={j} className="h-32 bg-[#1E1E2D] animate-pulse" />
 ))}
 </div>
 </div>
 ))}
 </div>
 ) : (
 filteredSystems.map(system => (
 <SystemSection
 key={system.code}
 systemCode={system.code}
 systemName={system.name}
 description={system.description}
 />
 ))
 )}
 </div>

 {/* 底部统计 */}
 <div className="mt-12 pt-8 border-t border-[#2D2D44]">
 <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
 <div className="text-center">
 <div className="text-3xl font-bold pixel-number text-[#0D7377]">4</div>
 <div className="text-sm text-[#8B8BA7] mt-1">联赛体系</div>
 </div>
 <div className="text-center">
 <div className="text-3xl font-bold pixel-number text-[#0D7377]">32</div>
 <div className="text-sm text-[#8B8BA7] mt-1">联赛</div>
 </div>
 <div className="text-center">
 <div className="text-3xl font-bold pixel-number text-[#0D7377]">256</div>
 <div className="text-sm text-[#8B8BA7] mt-1">支球队</div>
 </div>
 <div className="text-center">
 <div className="text-3xl font-bold pixel-number text-[#0D7377]">4,608</div>
 <div className="text-sm text-[#8B8BA7] mt-1">名球员</div>
 </div>
 </div>
 </div>
 </div>
 )
}

export default LeagueList
