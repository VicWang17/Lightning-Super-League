import { useState, useEffect } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import { ChevronRight } from '../../components/ui/pixel-icons'
import { LeagueBadge } from '../../components/league/LeagueBadge'
import { useLeagueSystems, useLeagues } from '../../hooks/useLeagues'
import api from '../../api/client'
import type { League } from '../../types/league'
import { PageHeader } from '../../components/ui/PageHeader'
import { SegmentedTabs } from '../../components/ui/SegmentedTabs'

interface UserTeam {
  id: string
  name: string
  current_league_id?: string | null
}

const LEVEL_LABELS = ['超级联赛', '甲级联赛', '乙级联赛', '丙级联赛']

function LevelTag({ level }: { level: number }) {
  const labels = LEVEL_LABELS
  return (
    <span className={clsx(
      'inline-flex items-center px-2 py-0.5 text-[10px] font-black border-2',
      level === 1 ? 'bg-[#FFC247] text-[#8B5A2B] border-[#1F5F43]' :
      level === 2 ? 'bg-[#E7F2D4] text-[#173126] border-[#1F5F43]' :
      level === 3 ? 'bg-[#59C7EE] text-[#173126] border-[#1F5F43]' :
      'bg-white text-[#466353] border-[#1F5F43]/40'
    )}>
      {labels[level - 1] || `第${level}级别`}
    </span>
  )
}

function LeagueCard({ league }: { league: League }) {
  return (
    <Link
      to={`/leagues/${league.id}`}
      className="group block"
    >
      <div className="fresh-ticket flex items-center gap-4 transition-all hover:-translate-y-0.5 hover:border-solid hover:border-[#1F5F43]">
        <div className="flex-shrink-0">
          <LeagueBadge
            systemCode={league.system_code}
            level={league.level}
            size="md"
            title={`${league.name} 徽章`}
          />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <h3 className="text-base font-black text-[#173126] group-hover:text-[#1F5F43] transition-colors truncate">
              {league.name}
            </h3>
            <LevelTag level={league.level} />
          </div>
          <div className="flex items-center gap-3 text-xs font-bold text-[#466353]">
            <span>{league.teams_count || 8} 支球队</span>
            <span>·</span>
            <span>14 轮比赛</span>
          </div>
        </div>
        <ChevronRight className="w-5 h-5 text-[#1F5F43]/40 group-hover:text-[#1F5F43] transition-colors flex-shrink-0" />
      </div>
    </Link>
  )
}

function SystemSection({ systemCode, systemName, description }: { systemCode: string; systemName: string; description?: string }) {
  const { leagues, loading } = useLeagues(systemCode)

  return (
    <section className="fresh-notice-board">
      <div className="flex items-center gap-3 mb-5 pl-5 pr-5">
        <LeagueBadge systemCode={systemCode} size="sm" title={`${systemName} 徽章`} />
        <div>
          <h2 className="text-xl font-black text-[#173126]">{systemName}</h2>
          {description && <p className="text-sm font-bold text-[#8B5A2B]">{description}</p>}
        </div>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-24 bg-[#FFF8DC]/80 animate-pulse border-2 border-dashed border-[#8B5A2B]/30" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          {leagues.map(league => (
            <LeagueCard key={league.id} league={league} />
          ))}
        </div>
      )}
    </section>
  )
}

function LeagueList() {
  const navigate = useNavigate()
  const { systems, loading: systemsLoading } = useLeagueSystems()
  const [selectedSystem, setSelectedSystem] = useState<string | null>(null)
  const [userLeagueId, setUserLeagueId] = useState<string | null>(null)
  const location = useLocation()

  const isAllLeaguesPage = location.pathname === '/leagues/all'

  useEffect(() => {
    api.get<UserTeam>('/teams/my-team').then(response => {
      if (response.success && response.data.current_league_id) {
        setUserLeagueId(response.data.current_league_id)
      }
    }).catch(() => {})
  }, [])

  if (!isAllLeaguesPage && userLeagueId) {
    return <Navigate to={`/leagues/${userLeagueId}`} replace />
  }

  const filteredSystems = selectedSystem
    ? systems.filter(s => s.code === selectedSystem)
    : systems

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
        title="联赛体系"
        subtitle="闪电超级联赛共有 4 个联赛体系，32 个联赛，256 支球队"
      />

      {systemsLoading ? (
        <div className="flex gap-3 mb-6">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={`tab-load-${i}`} className="h-10 w-24 bg-white/70 animate-pulse border-2 border-[#1F5F43]/20" />
          ))}
        </div>
      ) : (
        <SegmentedTabs
          tabs={[
            { value: 'all', label: '全部' },
            ...systems.map(system => ({
              value: system.code,
              label: system.name,
            })),
          ]}
          value={selectedSystem ?? 'all'}
          onChange={(value) => setSelectedSystem(value === 'all' ? null : value)}
        />
      )}

      <div className="space-y-8">
        {systemsLoading ? (
          <div className="space-y-8">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={`sys-load-${i}`}>
                <div className="h-8 w-32 bg-[#FFF8DC]/80 animate-pulse mb-4" />
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {Array.from({ length: 4 }).map((_, j) => (
                    <div key={`card-load-${i}-${j}`} className="h-24 bg-[#FFF8DC]/80 animate-pulse border-2 border-dashed border-[#8B5A2B]/30" />
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

      <section className="mt-10 pt-8 border-t-2 border-[#1F5F43]/20">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: '联赛体系', value: 4 },
            { label: '联赛', value: 32 },
            { label: '支球队', value: 256 },
            { label: '名球员', value: '4,608' },
          ].map((stat) => (
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

export default LeagueList
