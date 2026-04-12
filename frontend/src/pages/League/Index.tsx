import { useState, useEffect } from 'react'
import { Link, Navigate, useLocation } from 'react-router-dom'
import { 
  Trophy, 
  ChevronRight, 
  Users,
  Swords
} from 'lucide-react'
import { useLeagueSystems, useLeagues } from '../../hooks/useLeagues'
import api from '../../api/client'
import type { League } from '../../types/league'

// 用户球队类型
interface UserTeam {
  id: string
  name: string
  current_league_id?: string | null
}

// 联赛级别配置
const LEVEL_CONFIG = [
  { name: '超级联赛', color: 'from-amber-500 to-yellow-400', bgColor: 'from-amber-500/20 to-amber-600/5', borderColor: 'border-amber-500/30', icon: '👑' },
  { name: '甲级联赛', color: 'from-slate-300 to-slate-400', bgColor: 'from-slate-400/20 to-slate-500/5', borderColor: 'border-slate-400/30', icon: '🥈' },
  { name: '乙级联赛', color: 'from-orange-500 to-orange-600', bgColor: 'from-orange-600/20 to-orange-700/5', borderColor: 'border-orange-600/30', icon: '🥉' },
  { name: '丙级联赛', color: 'from-stone-400 to-stone-500', bgColor: 'from-stone-500/20 to-stone-600/5', borderColor: 'border-stone-500/30', icon: '🏅' },
]

// 体系图标和颜色
const SYSTEM_CONFIG: Record<string, { icon: string; color: string; gradient: string }> = {
  EAST: { icon: '🐉', color: 'text-red-400', gradient: 'from-red-500/20 to-orange-500/5' },
  WEST: { icon: '🏜️', color: 'text-amber-400', gradient: 'from-amber-500/20 to-yellow-500/5' },
  SOUTH: { icon: '🌴', color: 'text-emerald-400', gradient: 'from-emerald-500/20 to-teal-500/5' },
  NORTH: { icon: '⚔️', color: 'text-blue-400', gradient: 'from-blue-500/20 to-indigo-500/5' },
}

// 联赛卡片组件
function LeagueCard({ league }: { league: League }) {
  const config = LEVEL_CONFIG[league.level - 1]
  const systemConfig = SYSTEM_CONFIG[league.system_code] || SYSTEM_CONFIG.EAST
  
  return (
    <Link
      to={`/leagues/${league.id}`}
      className="group block"
    >
      <div className={`relative p-5 rounded-xl bg-gradient-to-br ${config.bgColor} border ${config.borderColor} hover:scale-[1.02] transition-all duration-200 overflow-hidden`}>
        {/* 背景装饰 */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-white/5 to-transparent rounded-bl-full" />
        
        <div className="relative">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${config.color} flex items-center justify-center text-2xl shadow-lg`}>
                {config.icon}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white group-hover:text-[#0D7377] transition-colors">
                  {league.name}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-lg ${systemConfig.color}`}>{systemConfig.icon}</span>
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
            <span className={`text-xs px-2 py-1 rounded-full bg-gradient-to-r ${systemConfig.gradient} border border-white/10`}>
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
  const config = SYSTEM_CONFIG[systemCode] || SYSTEM_CONFIG.EAST
  
  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-4">
        <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${config.gradient} border border-white/10 flex items-center justify-center text-xl`}>
          {config.icon}
        </div>
        <div>
          <h2 className="text-xl font-bold text-white">{systemName}</h2>
          {description && <p className="text-sm text-[#8B8BA7]">{description}</p>}
        </div>
      </div>
      
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-32 rounded-xl bg-[#1E1E2D] animate-pulse" />
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
      {/* 页面标题 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#0D7377] to-[#0A5A5D] flex items-center justify-center">
            <Trophy className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">所有联赛</h1>
        </div>
        <p className="text-[#8B8BA7] ml-13">
          闪电超级联赛共有 4 个联赛体系，32 个联赛，256 支球队
        </p>
      </div>

      {/* 体系筛选 */}
      {systemsLoading ? (
        <div className="flex gap-3 mb-8">
          {[1, 2, 3, 4].map(i => (
            <div key={i} className="h-10 w-24 rounded-lg bg-[#1E1E2D] animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="flex flex-wrap gap-3 mb-8">
          <button
            onClick={() => setSelectedSystem(null)}
            className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 ${
              selectedSystem === null
                ? 'bg-[#0D7377] text-white shadow-lg shadow-[#0D7377]/25'
                : 'bg-[#1E1E2D] text-[#8B8BA7] hover:text-white border border-[#2D2D44] hover:border-[#0D7377]/50'
            }`}
          >
            全部
          </button>
          {systems.map(system => (
            <button
              key={system.code}
              onClick={() => setSelectedSystem(system.code)}
              className={`px-4 py-2 rounded-lg font-medium transition-all duration-200 flex items-center gap-2 ${
                selectedSystem === system.code
                  ? 'bg-[#0D7377] text-white shadow-lg shadow-[#0D7377]/25'
                  : 'bg-[#1E1E2D] text-[#8B8BA7] hover:text-white border border-[#2D2D44] hover:border-[#0D7377]/50'
              }`}
            >
              <span>{SYSTEM_CONFIG[system.code]?.icon || '🏟️'}</span>
              {system.name}
            </button>
          ))}
        </div>
      )}

      {/* 联赛列表 */}
      <div className="space-y-8">
        {systemsLoading ? (
          <div className="space-y-8">
            {[1, 2].map(i => (
              <div key={i}>
                <div className="h-8 w-32 rounded bg-[#1E1E2D] animate-pulse mb-4" />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[1, 2, 3, 4].map(j => (
                    <div key={j} className="h-32 rounded-xl bg-[#1E1E2D] animate-pulse" />
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
            <div className="text-3xl font-bold stat-number text-[#0D7377]">4</div>
            <div className="text-sm text-[#8B8BA7] mt-1">联赛体系</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold stat-number text-[#0D7377]">32</div>
            <div className="text-sm text-[#8B8BA7] mt-1">联赛</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold stat-number text-[#0D7377]">256</div>
            <div className="text-sm text-[#8B8BA7] mt-1">支球队</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold stat-number text-[#0D7377]">4,608</div>
            <div className="text-sm text-[#8B8BA7] mt-1">名球员</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default LeagueList
