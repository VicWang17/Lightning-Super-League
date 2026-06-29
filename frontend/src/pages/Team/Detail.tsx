import { useEffect, useMemo, useState } from 'react'
import { Link, useParams, useNavigate } from 'react-router-dom'
import {
  ArrowUp,
  ArrowBigUpDash,
  ArrowBigDown,
  ArrowsHorizontal,
  Thermometer,
  SquareAlert,
  Skull,
} from '../../components/ui/pixel-icons'
import { getPositionColor, type PlayerListItem, type PlayerState } from '../../types/player'
import { api } from '../../api/client'
import { useTeamHistory, useTeamHonors, useTeamRecords } from '../../hooks/useTeamOverview'
import { RecordsBoard } from '../../components/records/RecordsBoard'
import { Card } from '../../components/ui/Card'
import { SegmentedTabs } from '../../components/ui/SegmentedTabs'
import PlayerActionBar from '../../components/transfer/PlayerActionBar'

interface TeamSummary {
  id: string
  name: string
  short_name?: string
  overall_rating?: number
  attack?: number
  midfield?: number
  defense?: number
  league_id?: string
  current_league_id?: string
  league_name?: string
}

type LockerPlayer = PlayerListItem

type TeamTab = 'locker' | 'history' | 'honors' | 'records'

const TEAM_TABS = [
  { value: 'locker' as TeamTab, label: '更衣室' },
  { value: 'history' as TeamTab, label: '历年战绩' },
  { value: 'honors' as TeamTab, label: '荣誉室' },
  { value: 'records' as TeamTab, label: '球队纪录' },
]

const positionOrder = { GK: 0, DF: 1, MF: 2, FW: 3 }

const formLabel: Record<string, string> = {
  HOT: '火热',
  GOOD: '良好',
  NEUTRAL: '平稳',
  LOW: '低迷',
}

const formColor: Record<string, string> = {
  HOT: 'text-[#FF6F59]',
  GOOD: 'text-[#1F5F43]',
  NEUTRAL: 'text-[#7b927f]',
  LOW: 'text-[#C77A00]',
}

const formOrder: Record<string, number> = {
  HOT: 3,
  GOOD: 2,
  NEUTRAL: 1,
  LOW: 0,
}

type SortField = 'squad_number' | 'position' | 'age' | 'ovr' | 'form' | 'fitness' | 'matches_played' | 'goals' | 'assists' | 'average_rating'
type SortDirection = 'asc' | 'desc'

interface SortConfig {
  field: SortField
  direction: SortDirection
}

function statValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : '-'
}

function ratingValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : '-'
}

function fitnessTone(fitness?: number) {
  if (typeof fitness !== 'number') return 'bg-[#8B5A2B]/40'
  if (fitness < 55) return 'bg-[#FF6F59]'
  if (fitness < 75) return 'bg-[#FFC247]'
  return 'bg-[#B9EF3F]'
}

function StatusIcon({ player }: { player: LockerPlayer }) {
  if (player.status === 'INJURED') {
    return (
      <span title="伤病中，无法出场">
        <Thermometer className="h-4 w-4 text-[#FF6F59]" />
      </span>
    )
  }
  if (player.status === 'SUSPENDED') {
    const detail = player.current_suspension
      ? `停赛中，剩余 ${player.current_suspension.matches_remaining} 场`
      : '停赛中，无法出场'
    return (
      <span title={detail}>
        <SquareAlert className="h-4 w-4 text-[#C77A00]" />
      </span>
    )
  }
  if (player.status === 'RETIRED') {
    return (
      <span title="已退役">
        <Skull className="h-4 w-4 text-[#466353]" />
      </span>
    )
  }
  return null
}

function TeamMetric({ label, value }: { label: string; value?: number }) {
  return (
    <div className="locker-metric">
      <span>{label}</span>
      <strong>{statValue(value)}</strong>
    </div>
  )
}

function PlayerAvatar({ player, size = 'sm' }: { player: LockerPlayer; size?: 'sm' | 'lg' }) {
  const sizeClass = size === 'lg' ? 'h-24 w-24' : 'h-10 w-10'

  return (
    <div className={`${sizeClass} overflow-hidden border-2 border-[#1F5F43]/30 bg-white`}>
      {player.avatar_url ? (
        <img src={`/${player.avatar_url}`} alt={player.name} className="h-full w-full object-cover" />
      ) : (
        <img src="/locker-room/jersey-placeholder-v1.png" alt="" className="h-full w-full object-cover" />
      )}
    </div>
  )
}

function SortHeader({
  field,
  label,
  sort,
  onSort,
}: {
  field: SortField
  label: string
  sort: SortConfig
  onSort: (field: SortField) => void
}) {
  const isActive = sort.field === field
  return (
    <th
      className="cursor-pointer select-none hover:text-[#173126] transition-colors"
      onClick={() => onSort(field)}
    >
      <div className="flex items-center gap-1">
        {label}
        <span className="inline-flex flex-col items-center leading-none">
          <span className={`text-[8px] ${isActive && sort.direction === 'asc' ? 'text-[#1F5F43]' : 'text-[#8B5A2B]/40'}`}>▲</span>
          <span className={`text-[8px] -mt-1 ${isActive && sort.direction === 'desc' ? 'text-[#1F5F43]' : 'text-[#8B5A2B]/40'}`}>▼</span>
        </span>
      </div>
    </th>
  )
}

function TeamDetail() {
  const { id: routeTeamId } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<TeamTab>('locker')
  const [team, setTeam] = useState<TeamSummary | null>(null)
  const [players, setPlayers] = useState<LockerPlayer[]>([])
  const [playerStates, setPlayerStates] = useState<Record<string, PlayerState>>({})
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [sort, setSort] = useState<SortConfig>({ field: 'ovr', direction: 'desc' })
  const [myTeamId, setMyTeamId] = useState<string | null>(null)

  useEffect(() => {
    api.get<{ id: string }>('/teams/my-team').then(res => {
      if (res.success && res.data) setMyTeamId(res.data.id)
    })
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    async function load() {
      try {
        let teamId = routeTeamId
        let teamData: TeamSummary | null = null

        if (!teamId) {
          const myTeamRes = await api.get<TeamSummary>('/teams/my-team')
          if (myTeamRes.success && myTeamRes.data) {
            teamId = myTeamRes.data.id
            teamData = myTeamRes.data
          }
        } else {
          const detailRes = await api.get<TeamSummary>(`/teams/${teamId}`).catch(() => null)
          if (detailRes?.success && detailRes.data) {
            teamData = detailRes.data
          }
        }

        if (!teamId) {
          if (!cancelled) {
            setTeam(null)
            setPlayers([])
            setPlayerStates({})
          }
          return
        }

        const [playersRes, statesRes] = await Promise.all([
          api.get<{ items: LockerPlayer[]; total: number; page: number; page_size: number }>(`/teams/${teamId}/players?page=1&page_size=100`),
          api.get<{ team_id: string; players: PlayerState[] }>(`/teams/${teamId}/player-states`).catch(() => null),
        ])

        if (!cancelled) {
          setTeam(teamData)

          if (playersRes.success) {
            const loadedPlayers = playersRes.data.items || []
            setPlayers(loadedPlayers)
            setSelectedPlayerId((current) => current || loadedPlayers[0]?.id || null)
          }

          if (statesRes?.success) {
            const stateMap: Record<string, PlayerState> = {}
            statesRes.data.players.forEach((state) => {
              stateMap[state.player_id] = state
            })
            setPlayerStates(stateMap)
          }
        }
      } catch (error) {
        console.error('加载球队更衣室失败:', error)
        if (!cancelled) {
          setTeam(null)
          setPlayers([])
          setPlayerStates({})
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    load()
    return () => {
      cancelled = true
    }
  }, [routeTeamId])

  const sortedPlayers = useMemo(() => {
    const list = [...players]
    const { field, direction } = sort
    const dir = direction === 'asc' ? 1 : -1

    list.sort((a, b) => {
      let cmp = 0

      switch (field) {
        case 'position':
          cmp = positionOrder[a.position] - positionOrder[b.position]
          break
        case 'squad_number':
          cmp = (a.squad_number || 0) - (b.squad_number || 0)
          break
        case 'age':
          cmp = a.age - b.age
          break
        case 'ovr':
          cmp = a.ovr - b.ovr
          break
        case 'form': {
          const stateA = playerStates[a.id]
          const stateB = playerStates[b.id]
          const formA = stateA ? (formOrder[stateA.visible_form] ?? -1) : -1
          const formB = stateB ? (formOrder[stateB.visible_form] ?? -1) : -1
          cmp = formA - formB
          break
        }
        case 'fitness': {
          const fitA = playerStates[a.id]?.fitness ?? 0
          const fitB = playerStates[b.id]?.fitness ?? 0
          cmp = fitA - fitB
          break
        }
        case 'matches_played':
          cmp = (a.matches_played || 0) - (b.matches_played || 0)
          break
        case 'goals':
          cmp = (a.goals || 0) - (b.goals || 0)
          break
        case 'assists':
          cmp = (a.assists || 0) - (b.assists || 0)
          break
        case 'average_rating':
          cmp = (a.average_rating || 0) - (b.average_rating || 0)
          break
        default:
          cmp = 0
      }

      // 如果主排序字段相等，按 OVR 降序作为次要排序
      if (cmp === 0) {
        cmp = b.ovr - a.ovr
      }

      return cmp * dir
    })

    return list
  }, [players, sort, playerStates])

  const selectedPlayer = sortedPlayers.find((player) => player.id === selectedPlayerId) || sortedPlayers[0] || null
  const selectedState = selectedPlayer ? playerStates[selectedPlayer.id] : null

  const squadSummary = useMemo(() => {
    const counts = { GK: 0, DF: 0, MF: 0, FW: 0 }
    let totalOvr = 0
    let fatigueRisk = 0
    let youngPlayers = 0

    players.forEach((player) => {
      counts[player.position] += 1
      totalOvr += player.ovr
      if (player.age <= 21) youngPlayers += 1
      const state = playerStates[player.id]
      if (state && state.fitness < 55) fatigueRisk += 1
    })

    return {
      counts,
      avgOvr: players.length ? Math.round(totalOvr / players.length) : undefined,
      fatigueRisk,
      youngPlayers,
    }
  }, [players, playerStates])

  const teamId = team?.id
  const leagueId = team?.league_id || team?.current_league_id

  const handleSort = (field: SortField) => {
    setSort((prev) => {
      if (prev.field === field) {
        return { field, direction: prev.direction === 'asc' ? 'desc' : 'asc' }
      }
      return { field, direction: 'desc' }
    })
  }

  // 其他Tab数据
  const { history: teamHistory, loading: historyLoading } = useTeamHistory(teamId)
  const { honors: teamHonors, loading: honorsLoading } = useTeamHonors(teamId)
  const { records: teamRecords, loading: recordsLoading } = useTeamRecords(teamId)

  return (
    <div className="locker-room-page">
      <div className="mb-4 flex items-center justify-between gap-4">
        <button
          onClick={() => navigate(-1)}
          className="text-sm font-bold text-[#466353] hover:text-[#173126]"
        >
          返回上一页
        </button>
        {leagueId && (
          <Link to={`/leagues/${leagueId}`} className="locker-link">
            {team?.league_name || '联赛'}
          </Link>
        )}
      </div>

      <SegmentedTabs
        tabs={TEAM_TABS}
        value={activeTab}
        onChange={(v) => setActiveTab(v as TeamTab)}
      />

      {activeTab === 'locker' && (
      <>
      <section className="locker-layout">
        <main className="locker-board">
          <div className="locker-board-header">
            <span className="ml-auto text-sm font-bold text-[#466353]">{players.length} 名球员</span>
          </div>

          {loading ? (
            <div className="locker-empty">加载球员中...</div>
          ) : sortedPlayers.length === 0 ? (
            <div className="locker-empty">后端暂未返回球员列表。</div>
          ) : (
            <div className="locker-table-wrap">
              <table className="locker-table">
                <thead>
                  <tr>
                    <th>球员</th>
                    <SortHeader field="squad_number" label="号码" sort={sort} onSort={handleSort} />
                    <SortHeader field="position" label="位置" sort={sort} onSort={handleSort} />
                    <SortHeader field="age" label="年龄" sort={sort} onSort={handleSort} />
                    <SortHeader field="ovr" label="OVR" sort={sort} onSort={handleSort} />
                    <SortHeader field="form" label="状态" sort={sort} onSort={handleSort} />
                    <SortHeader field="fitness" label="体能" sort={sort} onSort={handleSort} />
                    <SortHeader field="matches_played" label="出场" sort={sort} onSort={handleSort} />
                    <SortHeader field="goals" label="进球" sort={sort} onSort={handleSort} />
                    <SortHeader field="assists" label="助攻" sort={sort} onSort={handleSort} />
                    <SortHeader field="average_rating" label="评分" sort={sort} onSort={handleSort} />
                  </tr>
                </thead>
                <tbody>
                  {sortedPlayers.map((player) => {
                    const state = playerStates[player.id]
                    const active = selectedPlayer?.id === player.id
                    return (
                      <tr
                        key={player.id}
                        className={active ? 'is-selected' : ''}
                        onClick={() => setSelectedPlayerId(player.id)}
                      >
                        <td>
                          <div className="flex items-center gap-3">
                            <PlayerAvatar player={player} />
                            <div className="min-w-0">
                              <Link to={`/players/${player.id}`} className="block truncate font-black text-[#173126] hover:text-[#1F5F43]">
                                {player.name}
                              </Link>
                              {player.short_description ? (
                                <p className="text-xs font-medium text-[#8B5A2B] truncate">{player.short_description}</p>
                              ) : (
                                <p className="text-xs text-[#7b927f]">{player.team_id ? '一线队' : '未归属'}</p>
                              )}
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className="squad-number-chip">
                            {player.squad_number || '-'}
                          </span>
                        </td>
                        <td>
                          <span className={`position-chip ${getPositionColor(player.position)}`}>{player.position}</span>
                        </td>
                        <td>{player.age}</td>
                        <td className="font-black text-[#1F5F43]">{player.ovr}</td>
                        <td>
                          <div className="flex items-center gap-1.5">
                            <StatusIcon player={player} />
                            {state ? (
                              <span className={formColor[state.visible_form]} title={formLabel[state.visible_form]}>
                                {state.visible_form === 'HOT' && <ArrowBigUpDash className="h-4 w-4" />}
                                {state.visible_form === 'GOOD' && <ArrowUp className="h-4 w-4" />}
                                {state.visible_form === 'NEUTRAL' && <ArrowsHorizontal className="h-4 w-4" />}
                                {state.visible_form === 'LOW' && <ArrowBigDown className="h-4 w-4" />}
                              </span>
                            ) : (
                              '-'
                            )}
                          </div>
                        </td>
                        <td>
                          <div className="fitness-cell">
                            <div className="fitness-track">
                              <div className={fitnessTone(state?.fitness)} style={{ width: `${state?.fitness ?? 0}%` }} />
                            </div>
                            <span>{statValue(state?.fitness)}</span>
                          </div>
                        </td>
                        <td>{statValue(player.matches_played)}</td>
                        <td>{statValue(player.goals)}</td>
                        <td>{statValue(player.assists)}</td>
                        <td>{ratingValue(player.average_rating)}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </main>

        <aside className="locker-detail">
          {selectedPlayer ? (
            <>
              <div className="locker-detail-top">
                <PlayerAvatar player={selectedPlayer} size="lg" />
                <div>
                  <h2 className="text-2xl font-black text-[#173126]">{selectedPlayer.name}</h2>
                  <p className="text-sm font-bold text-[#466353]">
                    {selectedPlayer.squad_number ? `#${selectedPlayer.squad_number} · ` : ''}
                    {selectedPlayer.position} · {selectedPlayer.age}岁
                  </p>
                  {selectedPlayer.short_description && (
                    <p className="mt-1 text-sm font-black text-[#8B5A2B]">{selectedPlayer.short_description}</p>
                  )}
                </div>
              </div>

              <div className="selected-player-grid">
                <TeamMetric label="OVR" value={selectedPlayer.ovr} />
                <div className="locker-metric">
                  <span>潜力</span>
                  <strong>{selectedPlayer.potential_letter}</strong>
                </div>
                <TeamMetric label="体能" value={selectedState?.fitness} />
                <div className="locker-metric">
                  <span>状态</span>
                  <strong>{selectedState ? formLabel[selectedState.visible_form] : '-'}</strong>
                </div>
              </div>

              <div className="selected-season">
                <h3>本赛季</h3>
                <div>
                  <span>出场</span>
                  <strong>{statValue(selectedPlayer.matches_played)}</strong>
                </div>
                <div>
                  <span>进球</span>
                  <strong>{statValue(selectedPlayer.goals)}</strong>
                </div>
                <div>
                  <span>助攻</span>
                  <strong>{statValue(selectedPlayer.assists)}</strong>
                </div>
                <div>
                  <span>评分</span>
                  <strong>{ratingValue(selectedPlayer.average_rating)}</strong>
                </div>
              </div>

              <div className="selected-season">
                <h3>进攻</h3>
                <div><span>射门</span><strong>{statValue(selectedPlayer.shots)}</strong></div>
                <div><span>射正</span><strong>{statValue(selectedPlayer.shots_on_target)}</strong></div>
                <div><span>盘带</span><strong>{statValue(selectedPlayer.dribbles)}</strong></div>
                <div><span>头球</span><strong>{statValue(selectedPlayer.headers)}</strong></div>
              </div>

              <div className="selected-season">
                <h3>传球</h3>
                <div><span>传球</span><strong>{statValue(selectedPlayer.passes)}</strong></div>
                <div><span>关键传</span><strong>{statValue(selectedPlayer.key_passes)}</strong></div>
                <div><span>传中</span><strong>{statValue(selectedPlayer.crosses)}</strong></div>
                <div><span>助攻</span><strong>{statValue(selectedPlayer.assists)}</strong></div>
              </div>

              <div className="selected-season">
                <h3>防守</h3>
                <div><span>抢断</span><strong>{statValue(selectedPlayer.tackles)}</strong></div>
                <div><span>拦截</span><strong>{statValue(selectedPlayer.interceptions)}</strong></div>
                <div><span>解围</span><strong>{statValue(selectedPlayer.clearances)}</strong></div>
                <div><span>封堵</span><strong>{statValue(selectedPlayer.blocks)}</strong></div>
              </div>

              {selectedPlayer.position === 'GK' && (
                <div className="selected-season">
                  <h3>门将</h3>
                  <div><span>扑救</span><strong>{statValue(selectedPlayer.saves)}</strong></div>
                  <div><span>零封</span><strong>{statValue(selectedPlayer.clean_sheets)}</strong></div>
                </div>
              )}

              <div className="selected-season">
                <h3>纪律</h3>
                <div><span>黄牌</span><strong className="text-[#C77A00]">{statValue(selectedPlayer.yellow_cards)}</strong></div>
                <div><span>红牌</span><strong className="text-[#FF6F59]">{statValue(selectedPlayer.red_cards)}</strong></div>
                <div><span>犯规</span><strong>{statValue(selectedPlayer.fouls)}</strong></div>
                <div><span>越位</span><strong>{statValue(selectedPlayer.offsides)}</strong></div>
              </div>

              <div className="locker-actions">
                <Link to={`/players/${selectedPlayer.id}`} className="btn-primary py-2 text-sm">球员详情</Link>
                <Link to={`/players/${selectedPlayer.id}/growth`} className="locker-action-secondary">成长曲线</Link>
                <PlayerActionBar player={selectedPlayer} myTeamId={myTeamId} />
              </div>
            </>
          ) : (
            <div className="locker-empty">选择一名球员查看柜位详情。</div>
          )}
        </aside>
      </section>

      <section className="squad-strip">
        <div>
          <span>门将</span>
          <strong>{squadSummary.counts.GK}</strong>
        </div>
        <div>
          <span>后卫</span>
          <strong>{squadSummary.counts.DF}</strong>
        </div>
        <div>
          <span>中场</span>
          <strong>{squadSummary.counts.MF}</strong>
        </div>
        <div>
          <span>前锋</span>
          <strong>{squadSummary.counts.FW}</strong>
        </div>
        <div>
          <span>平均 OVR</span>
          <strong>{statValue(squadSummary.avgOvr)}</strong>
        </div>
        <div>
          <span>U21</span>
          <strong>{squadSummary.youngPlayers}</strong>
        </div>
        <div>
          <span>疲劳风险</span>
          <strong>{squadSummary.fatigueRisk}</strong>
        </div>
      </section>
      </>
      )}

      {activeTab === 'history' && (
        <div >
          {historyLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 bg-[#FFF8DC]/80 animate-pulse" />
              ))}
            </div>
          ) : !teamHistory || teamHistory.seasons.length === 0 ? (
            <div className="text-center py-12">
              <p className="text-[#466353]">暂无历史战绩数据</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-[#466353] border-b border-[#1F5F43]/20">
                    <th className="py-2 px-4 font-medium">赛季</th>
                    <th className="py-2 px-4 font-medium">联赛</th>
                    <th className="py-2 px-4 font-medium text-center">排名</th>
                    <th className="py-2 px-4 font-medium text-center">赛</th>
                    <th className="py-2 px-4 font-medium text-center">胜/平/负</th>
                    <th className="py-2 px-4 font-medium text-center">进球</th>
                    <th className="py-2 px-4 font-medium text-center">失球</th>
                    <th className="py-2 px-4 font-medium text-center">净胜</th>
                    <th className="py-2 px-4 font-medium text-center">积分</th>
                  </tr>
                </thead>
                <tbody>
                  {teamHistory.seasons.map((season) => (
                    <tr key={season.season_number} className="border-b border-[#1F5F43]/20 hover:bg-[#FFF8DC]/60 transition-colors">
                      <td className="py-3 px-4 text-[#466353]">第 {season.season_number} 赛季</td>
                      <td className="py-3 px-4">{season.league_name}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`font-bold pixel-number ${season.position === 1 ? 'text-[#FF6F59]' : season.position <= 3 ? 'text-[#173126]' : 'text-[#466353]'}`}>
                          {season.position}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center stat-number">{season.played}</td>
                      <td className="py-3 px-4 text-center text-sm">
                        <span className="text-[#1F5F43]">{season.won}</span>
                        <span className="text-[#8B5A2B]/40">/</span>
                        <span className="text-[#466353]">{season.drawn}</span>
                        <span className="text-[#8B5A2B]/40">/</span>
                        <span className="text-[#FF6F59]">{season.lost}</span>
                      </td>
                      <td className="py-3 px-4 text-center stat-number text-[#1F5F43]">{season.goals_for}</td>
                      <td className="py-3 px-4 text-center stat-number text-[#FF6F59]">{season.goals_against}</td>
                      <td className="py-3 px-4 text-center stat-number">{season.goal_difference > 0 ? '+' : ''}{season.goal_difference}</td>
                      <td className="py-3 px-4 text-center">
                        <span className="font-bold pixel-number text-lg">{season.points}</span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {activeTab === 'honors' && (
        <div >
          {honorsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-24 bg-[#FFF8DC]/80 animate-pulse" />
              ))}
            </div>
          ) : !teamHonors || teamHonors.honors.length === 0 ? (
            <div className="text-center py-16">
              <h4 className="text-xl font-bold text-[#173126] mb-2">还没有冠军奖杯</h4>
              <p className="text-[#466353] mb-2">这支球队尚未获得任何冠军荣誉</p>
              <p className="text-[#1F5F43] text-sm font-medium">继续加油，冠军就在前方！🏆</p>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-6 mb-6 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-[#466353]">联赛冠军:</span>
                  <span className="font-bold text-[#173126]">{teamHonors.total_league_titles}</span>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[#466353]">杯赛冠军:</span>
                  <span className="font-bold text-[#173126]">{teamHonors.total_cup_titles}</span>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {teamHonors.honors.map((honor, idx) => (
                  <Card key={idx} className="bg-white/70 border-2 border-[#1F5F43]/20 p-4 text-center hover:border-[#FF6F59] transition-all">
                    <div className="text-3xl mb-2">{honor.honor_type === 'league_champion' ? '🏆' : '🥇'}</div>
                    <h4 className="font-bold text-[#173126] text-sm mb-1">{honor.competition_name}</h4>
                    <p className="text-xs text-[#466353]">第 {honor.season_number} 赛季</p>
                    {honor.competition_level && honor.competition_level > 0 && (
                      <span className="inline-block mt-2 px-2 py-0.5 text-[10px] bg-[#FFF8DC]/80 border border-[#1F5F43]/20 text-[#466353]">
                        L{honor.competition_level}
                      </span>
                    )}
                  </Card>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {activeTab === 'records' && (
        <div >
          <RecordsBoard records={teamRecords} loading={recordsLoading} emptyText="暂无球队纪录" />
        </div>
      )}
    </div>
  )
}

export default TeamDetail
