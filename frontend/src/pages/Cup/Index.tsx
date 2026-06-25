import { useState, useEffect } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ChevronRight } from '../../components/ui/pixel-icons'
import { CupBadge } from '../../components/cup/CupBadge'
import { useCups } from '../../hooks/useCups'
import api from '../../api/client'
import type { CupCompetition } from '../../types/cup'
import { CUP_CONFIG, getCupBaseCode } from '../../types/cup'
import { PageHeader } from '../../components/ui/PageHeader'
import Button from '../../components/ui/Button'

function StatusTag({ cup }: { cup: CupCompetition }) {
  if (cup.status === 'ongoing') {
    return (
      <span className="px-2 py-0.5 text-[10px] font-black bg-[#59C7EE] text-[#173126] border border-[#1F5F43] animate-pulse">
        进行中
      </span>
    )
  }
  if (cup.status === 'finished' && cup.winner_team_name) {
    return (
      <span className="px-2 py-0.5 text-[10px] font-black bg-[#FFC247] text-[#8B5A2B] border border-[#1F5F43]">
        冠军 {cup.winner_team_name}
      </span>
    )
  }
  return null
}

function CupCard({ cup }: { cup: CupCompetition }) {
  const config = CUP_CONFIG[getCupBaseCode(cup.code)] || CUP_CONFIG.LIGHTNING_CUP

  return (
    <Link to={`/cups/${cup.id}`} className="group block">
      <div className="fresh-ticket flex items-center gap-4 transition-all hover:-translate-y-0.5 hover:border-solid hover:border-[#1F5F43]">
        <div className="flex-shrink-0">
          <CupBadge code={cup.code} size="md" title={`${cup.name} 徽章`} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <h3 className="text-base font-black text-[#173126] group-hover:text-[#1F5F43] transition-colors truncate">
              {cup.name}
            </h3>
            <StatusTag cup={cup} />
          </div>
          <div className="flex items-center gap-3 text-xs font-bold text-[#466353]">
            <span>第{cup.season_number}赛季</span>
            <span>·</span>
            <span>{cup.total_teams} 支球队</span>
            <span>·</span>
            <span>{cup.has_group_stage ? '小组赛+淘汰赛' : '淘汰赛'}</span>
          </div>
          <p className="mt-2 text-xs font-bold text-[#7b927f] line-clamp-2">{config.description}</p>
        </div>
        <ChevronRight className="w-5 h-5 text-[#1F5F43]/40 group-hover:text-[#1F5F43] transition-colors flex-shrink-0" />
      </div>
    </Link>
  )
}

function CupCardSkeleton() {
  return <div className="h-28 bg-[#FFF8DC]/80 animate-pulse border-2 border-dashed border-[#8B5A2B]/30" />
}

function CupList() {
  const navigate = useNavigate()
  const { cups, loading: cupsLoading } = useCups()
  const [myCup, setMyCup] = useState<CupCompetition | null>(null)
  const [myCupId, setMyCupId] = useState<string | null>(null)
  const location = useLocation()

  const isAllCupsPage = location.pathname === '/cups/all'

  useEffect(() => {
    api.get<CupCompetition>('/cups/my-team').then(response => {
      if (response.success && response.data) {
        setMyCup(response.data)
        setMyCupId(response.data.id)
      }
    }).catch(() => {})
  }, [])

  if (!isAllCupsPage && myCupId) {
    return <Navigate to={`/cups/${myCupId}`} replace />
  }

  return (
    <div className="fresh-page-shell space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm font-bold text-[#466353] hover:text-[#173126] transition-colors"
      >
        <ChevronRight className="w-4 h-4 rotate-180" />
        返回上一页
      </button>

      <PageHeader
        title="杯赛一览"
        subtitle="闪电超级联赛杯赛系统，包含闪电杯和杰尼杯两项赛事"
      />

      {myCup && !isAllCupsPage && (
        <div className="fresh-filter-strip items-center justify-between">
          <span className="text-sm font-black text-[#173126]">您正在参加 {myCup.name}</span>
          <Link to={`/cups/${myCup.id}`}>
            <Button size="sm">查看详情</Button>
          </Link>
        </div>
      )}

      <section className="fresh-notice-board">
        <div className="flex items-center gap-3 mb-5 pl-5 pr-5">
          <CupBadge code="LIGHTNING_CUP" size="sm" title="杯赛徽章" />
          <h2 className="text-xl font-black text-[#173126]">本赛季杯赛</h2>
        </div>

        {cupsLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <CupCardSkeleton />
            <CupCardSkeleton />
          </div>
        ) : cups.length === 0 ? (
          <div className="text-center py-10">
            <h3 className="text-lg font-black text-[#173126] mb-1">暂无杯赛</h3>
            <p className="text-sm font-bold text-[#466353]">当前赛季尚未创建杯赛</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {cups.map(cup => (
              <CupCard key={cup.id} cup={cup} />
            ))}
          </div>
        )}
      </section>

      <section className="fresh-ticket">
        <h3 className="text-lg font-black text-[#173126] mb-4">杯赛赛制说明</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { code: 'LIGHTNING_CUP' as const, title: '闪电杯', desc: '超级联赛专属杯赛，64支顶级球队参赛。先进行16个小组的单循环小组赛，每组前2名晋级32强，随后进行5轮单场淘汰赛决出冠军。' },
            { code: 'JENNY_CUP' as const, title: '杰尼杯', desc: '次级联赛杯赛，192支球队参赛。先进行预选赛决出24支球队，与8支次级联赛种子队组成32强，随后进行5轮单场淘汰赛决出冠军。' },
          ].map(item => (
            <div key={item.code} className="p-4 bg-white/60 border-2 border-[#1F5F43]/20 hover:border-[#1F5F43] transition-colors">
              <div className="flex items-center gap-2 mb-2">
                <CupBadge code={item.code} size="sm" title={`${item.title} 徽章`} />
                <h4 className="font-black text-[#173126]">{item.title}</h4>
              </div>
              <p className="text-sm font-bold text-[#466353]">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-10 pt-8 border-t-2 border-[#1F5F43]/20">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '杯赛项目', value: 2 },
            { label: '参赛球队', value: 256 },
            { label: '总场次', value: 316 },
            { label: '冠军奖杯', value: 2 },
          ].map(stat => (
            <div key={stat.label} className="fresh-stat-tile text-center">
              <span>{stat.label}</span>
              <strong className="font-pixel text-2xl">{stat.value}</strong>
            </div>
          ))}
        </div>
      </section>
    </div>
  )
}

export default CupList
