import { Link, Navigate, useLocation } from 'react-router-dom'
import { 
  Trophy, 
  ChevronRight, 
  Users,
  Zap,
  Swords
} from 'lucide-react'
import { useCups, useMyTeamCup } from '../../hooks/useCups'
import type { CupCompetition } from '../../types/cup'
import { CUP_CONFIG } from '../../types/cup'

// 杯赛卡片组件
function CupCard({ cup }: { cup: CupCompetition }) {
  const config = CUP_CONFIG[cup.code] || CUP_CONFIG.LIGHTNING_CUP
  const isFinished = cup.status === 'finished'
  const isOngoing = cup.status === 'ongoing'
  
  return (
    <Link
      to={`/cups/${cup.id}`}
      className="group block"
    >
      <div className={`relative p-5 rounded-xl bg-gradient-to-br ${config.gradient} border border-white/10 hover:border-[#0D7377]/50 hover:scale-[1.02] transition-all duration-200 overflow-hidden`}>
        {/* 背景装饰 */}
        <div className="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-white/5 to-transparent rounded-bl-full" />
        
        {/* 状态标签 */}
        {isOngoing && (
          <div className="absolute top-3 right-3 px-2 py-0.5 rounded-full bg-[#0D7377] text-white text-xs font-medium animate-pulse">
            进行中
          </div>
        )}
        {isFinished && cup.winner_team_name && (
          <div className="absolute top-3 right-3 px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400 text-xs font-medium border border-amber-500/30">
            🏆 {cup.winner_team_name}
          </div>
        )}
        
        <div className="relative">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-3">
              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${cup.code === 'LIGHTNING_CUP' ? 'from-yellow-500 to-amber-500' : 'from-emerald-500 to-teal-500'} flex items-center justify-center text-2xl shadow-lg`}>
                {config.icon}
              </div>
              <div>
                <h3 className="text-lg font-bold text-white group-hover:text-[#0D7377] transition-colors">
                  {cup.name}
                </h3>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-lg ${config.color}`}>{config.icon}</span>
                  <span className="text-sm text-[#8B8BA7]">第{cup.season_number}赛季</span>
                </div>
              </div>
            </div>
            <ChevronRight className="w-5 h-5 text-[#4B4B6A] group-hover:text-white transition-colors" />
          </div>
          
          <div className="mt-4 pt-4 border-t border-white/10 flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-1.5">
                <Users className="w-4 h-4 text-[#8B8BA7]" />
                <span className="text-sm text-[#8B8BA7]">{cup.total_teams} 支球队</span>
              </div>
              <div className="flex items-center gap-1.5">
                <Swords className="w-4 h-4 text-[#8B8BA7]" />
                <span className="text-sm text-[#8B8BA7]">
                  {cup.has_group_stage ? '小组赛+淘汰赛' : '淘汰赛'}
                </span>
              </div>
            </div>
            <span className={`text-xs px-2 py-1 rounded-full bg-gradient-to-r ${config.gradient} border border-white/10`}>
              {cup.has_group_stage ? `${cup.group_count}个小组` : '单场淘汰'}
            </span>
          </div>
          
          <p className="mt-3 text-xs text-[#8B8BA7]">{config.description}</p>
        </div>
      </div>
    </Link>
  )
}

// 杯赛骨架屏组件
function CupCardSkeleton() {
  return (
    <div className="h-40 rounded-xl bg-[#1E1E2D] animate-pulse" />
  )
}

function CupList() {
  const { cups, loading: cupsLoading } = useCups()
  const { myCup, loading: myCupLoading } = useMyTeamCup()
  const location = useLocation()
  
  // 判断是否是"所有杯赛"页面
  const isAllCupsPage = location.pathname === '/cups/all'
  
  // 如果不是"所有杯赛"页面，且已获取到用户杯赛，直接导航到用户杯赛
  if (!isAllCupsPage && myCup && !myCupLoading) {
    return <Navigate to={`/cups/${myCup.id}`} replace />
  }

  return (
    <div className="max-w-[1200px]">
      {/* 页面标题 */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-[#0D7377] to-[#0A5A5D] flex items-center justify-center">
            <Trophy className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white">杯赛</h1>
        </div>
        <p className="text-[#8B8BA7] ml-13">
          闪电超级联赛杯赛系统，包含闪电杯和杰尼杯两项赛事
        </p>
      </div>

      {/* 我的杯赛快速入口 */}
      {myCup && !isAllCupsPage && (
        <div className="mb-8 p-4 rounded-xl bg-gradient-to-r from-[#0D7377]/20 to-transparent border border-[#0D7377]/30">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Zap className="w-5 h-5 text-[#0D7377]" />
              <span className="text-white font-medium">您正在参加 {myCup.name}</span>
            </div>
            <Link 
              to={`/cups/${myCup.id}`}
              className="px-4 py-2 rounded-lg bg-[#0D7377] text-white text-sm font-medium hover:bg-[#0A5A5D] transition-colors"
            >
              查看详情
            </Link>
          </div>
        </div>
      )}

      {/* 杯赛列表 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {cupsLoading ? (
          <>
            <CupCardSkeleton />
            <CupCardSkeleton />
          </>
        ) : cups.length === 0 ? (
          <div className="col-span-2 text-center py-12">
            <Trophy className="w-16 h-16 text-[#4B4B6A] mx-auto mb-4" />
            <h3 className="text-xl font-bold text-white mb-2">暂无杯赛</h3>
            <p className="text-[#8B8BA7]">当前赛季尚未创建杯赛</p>
          </div>
        ) : (
          cups.map(cup => (
            <CupCard key={cup.id} cup={cup} />
          ))
        )}
      </div>

      {/* 杯赛说明 */}
      <div className="mt-12 pt-8 border-t border-[#2D2D44]">
        <h3 className="text-lg font-semibold text-white mb-4">杯赛赛制说明</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="p-4 rounded-xl bg-[#12121A] border border-[#2D2D44]">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">⚡</span>
              <h4 className="font-medium text-white">闪电杯</h4>
            </div>
            <p className="text-sm text-[#8B8BA7]">
              超级联赛专属杯赛，64支顶级球队参赛。先进行16个小组的单循环小组赛，
              每组前2名晋级32强，随后进行5轮单场淘汰赛决出冠军。
            </p>
          </div>
          <div className="p-4 rounded-xl bg-[#12121A] border border-[#2D2D44]">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-xl">🏆</span>
              <h4 className="font-medium text-white">杰尼杯</h4>
            </div>
            <p className="text-sm text-[#8B8BA7]">
              次级联赛杯赛，192支球队参赛。先进行预选赛决出24支球队，
              与8支次级联赛种子队组成32强，随后进行5轮单场淘汰赛决出冠军。
            </p>
          </div>
        </div>
      </div>

      {/* 底部统计 */}
      <div className="mt-12 pt-8 border-t border-[#2D2D44]">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold stat-number text-[#0D7377]">2</div>
            <div className="text-sm text-[#8B8BA7] mt-1">杯赛项目</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold stat-number text-[#0D7377]">256</div>
            <div className="text-sm text-[#8B8BA7] mt-1">参赛球队</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold stat-number text-[#0D7377]">316</div>
            <div className="text-sm text-[#8B8BA7] mt-1">总场次</div>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold stat-number text-[#0D7377]">2</div>
            <div className="text-sm text-[#8B8BA7] mt-1">冠军奖杯</div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CupList
