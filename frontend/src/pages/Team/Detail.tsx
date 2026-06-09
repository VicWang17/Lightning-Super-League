import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  ChevronLeft,
  Trophy,
  ArrowUp,
  ArrowBigUpDash,
  ArrowBigDown,
  ArrowsHorizontal,
  Thermometer,
  SquareAlert,
  Skull,
  Users,
  Chart,
  Award,
  Target,
} from '../../components/ui/pixel-icons'
import { getPositionColor, type PlayerListItem, type PlayerState } from '../../types/player'
import { api } from '../../api/client'
import { useTeamHistory, useTeamHonors, useTeamRecords } from '../../hooks/useTeamOverview'
import {
  RecordCategory,
  RecordType,
  RECORD_TYPE_LABELS,
  RECORD_TYPES_BY_CATEGORY,
} from '../../types/records'
import { Card } from '../../components/ui/Card'

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
  { value: 'locker' as TeamTab, label: '更衣室', icon: Users },
  { value: 'history' as TeamTab, label: '历年战绩', icon: Chart },
  { value: 'honors' as TeamTab, label: '荣誉室', icon: Award },
  { value: 'records' as TeamTab, label: '球队纪录', icon: Target },
]

const positionOrder = { GK: 0, DF: 1, MF: 2, FW: 3 }

const formLabel: Record<string, string> = {
  HOT: '火热',
  GOOD: '良好',
  NEUTRAL: '平稳',
  LOW: '低迷',
}

const formColor: Record<string, string> = {
  HOT: 'text-red-400',
  GOOD: 'text-[#9ECF45]',
  NEUTRAL: 'text-[#8A927B]',
  LOW: 'text-amber-400',
}

function statValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : '-'
}

function ratingValue(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value.toFixed(1) : '-'
}

function fitnessTone(fitness?: number) {
  if (typeof fitness !== 'number') return 'bg-[#3A3F4A]'
  return 'bg-[#8A927B]'
}

function StatusIcon({ player }: { player: LockerPlayer }) {
  if (player.status === 'INJURED') {
    return (
      <span title="伤病中，无法出场">
        <Thermometer className="h-4 w-4 text-red-400" />
      </span>
    )
  }
  if (player.status === 'SUSPENDED') {
    const detail = player.current_suspension
      ? `停赛中，剩余 ${player.current_suspension.matches_remaining} 场`
      : '停赛中，无法出场'
    return (
      <span title={detail}>
        <SquareAlert className="h-4 w-4 text-amber-400" />
      </span>
    )
  }
  if (player.status === 'RETIRED') {
    return (
      <span title="已退役">
        <Skull className="h-4 w-4 text-gray-500" />
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
    <div className={`${sizeClass} overflow-hidden border-2 border-[#242832] bg-[#0B0D12]`}>
      {player.avatar_url ? (
        <img src={`/${player.avatar_url}`} alt={player.name} className="h-full w-full object-cover" />
      ) : (
        <img src="/locker-room/jersey-placeholder-v1.png" alt="" className="h-full w-full object-cover" />
      )}
    </div>
  )
}

function TeamDetail() {
  const { id: routeTeamId } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<TeamTab>('locker')
  const [team, setTeam] = useState<TeamSummary | null>(null)
  const [players, setPlayers] = useState<LockerPlayer[]>([])
  const [playerStates, setPlayerStates] = useState<Record<string, PlayerState>>({})
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

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
    return [...players].sort((a, b) => {
      const positionDiff = positionOrder[a.position] - positionOrder[b.position]
      if (positionDiff !== 0) return positionDiff
      return b.ovr - a.ovr
    })
  }, [players])

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

  // 其他Tab数据
  const { history: teamHistory, loading: historyLoading } = useTeamHistory(teamId)
  const { honors: teamHonors, loading: honorsLoading } = useTeamHonors(teamId)
  const { records: teamRecords, loading: recordsLoading } = useTeamRecords(teamId)

  return (
    <div className="locker-room-page">
      <div className="mb-4 flex items-center justify-between gap-4">
        <Link
          to="/leagues"
          className="inline-flex items-center gap-1 text-sm font-bold text-[#7B8392] hover:text-white"
        >
          <ChevronLeft className="h-4 w-4" />
          返回联赛
        </Link>
        {leagueId && (
          <Link to={`/leagues/${leagueId}`} className="locker-link">
            <Trophy className="h-4 w-4" />
            {team?.league_name || '联赛'}
          </Link>
        )}
      </div>

      {/* Tab 导航 */}
      <div className="flex flex-wrap gap-2 mb-6">
        {TEAM_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-2 transition-all flex items-center gap-2',
              activeTab === tab.value
                ? 'bg-[#C6F135] text-[#0A0A0F] border-[#C6F135]'
                : 'bg-[#12121A] text-[#8B8BA7] border-[#2D2D44] hover:border-[#0D7377] hover:text-white'
            )}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'locker' && (
      <>
      <section className="locker-hero">
        <div>
          <h1 className="text-3xl font-black text-[var(--skin-text)]">{team?.name || '更衣室'}</h1>
        </div>
        <div className="locker-metrics">
          <TeamMetric label="总评" value={team?.overall_rating} />
          <TeamMetric label="进攻" value={team?.attack} />
          <TeamMetric label="中场" value={team?.midfield} />
          <TeamMetric label="防守" value={team?.defense} />
          <TeamMetric label="球员" value={players.length || undefined} />
        </div>
      </section>

      <section className="locker-layout">
        <main className="locker-board">
          <div className="locker-board-header">
            <div>
              <h2 className="text-xl font-black text-[var(--skin-text)]">球员名单</h2>
            </div>
            <span className="text-sm font-bold text-[#7B8392]">{players.length} 名球员</span>
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
                    <th>号码</th>
                    <th>位置</th>
                    <th>年龄</th>
                    <th>OVR</th>
                    <th>状态</th>
                    <th>体能</th>
                    <th>出场</th>
                    <th>进球</th>
                    <th>助攻</th>
                    <th>评分</th>
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
                              <Link to={`/players/${player.id}`} className="block truncate font-black text-[var(--skin-text)] hover:text-[var(--skin-accent)]">
                                {player.name}
                              </Link>
                              <p className="text-xs text-[#707A8A]">{player.team_id ? '一线队' : '未归属'}</p>
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
                        <td className="font-black text-[var(--skin-accent)]">{player.ovr}</td>
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
                  <h2 className="text-2xl font-black text-[var(--skin-text)]">{selectedPlayer.name}</h2>
                  <p className="text-sm font-bold text-[#7B8392]">
                    {selectedPlayer.squad_number ? `#${selectedPlayer.squad_number} · ` : ''}
                    {selectedPlayer.position} · {selectedPlayer.age}岁
                  </p>
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
                <div><span>黄牌</span><strong className="text-yellow-400">{statValue(selectedPlayer.yellow_cards)}</strong></div>
                <div><span>红牌</span><strong className="text-red-400">{statValue(selectedPlayer.red_cards)}</strong></div>
                <div><span>犯规</span><strong>{statValue(selectedPlayer.fouls)}</strong></div>
                <div><span>越位</span><strong>{statValue(selectedPlayer.offsides)}</strong></div>
              </div>

              <div className="locker-actions">
                <Link to={`/players/${selectedPlayer.id}`} className="btn-primary py-2 text-sm">球员详情</Link>
                <Link to={`/players/${selectedPlayer.id}/growth`} className="locker-action-secondary">成长曲线</Link>
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
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">历年战绩</h3>
          {historyLoading ? (
            <div className="space-y-2">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="h-12 bg-[#1E1E2D] animate-pulse" />
              ))}
            </div>
          ) : !teamHistory || teamHistory.seasons.length === 0 ? (
            <div className="text-center py-12">
              <Chart className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
              <p className="text-[#8B8BA7]">暂无历史战绩数据</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="text-left text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
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
                    <tr key={season.season_number} className="border-b border-[#2D2D44] hover:bg-[#1E1E2D]/50 transition-colors">
                      <td className="py-3 px-4 text-[#8B8BA7]">第 {season.season_number} 赛季</td>
                      <td className="py-3 px-4">{season.league_name}</td>
                      <td className="py-3 px-4 text-center">
                        <span className={`font-bold pixel-number ${season.position === 1 ? 'text-amber-400' : season.position <= 3 ? 'text-slate-300' : 'text-[#8B8BA7]'}`}>
                          {season.position}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-center stat-number">{season.played}</td>
                      <td className="py-3 px-4 text-center text-sm">
                        <span className="text-emerald-400">{season.won}</span>
                        <span className="text-[#4B4B6A]">/</span>
                        <span className="text-[#8B8BA7]">{season.drawn}</span>
                        <span className="text-[#4B4B6A]">/</span>
                        <span className="text-red-400">{season.lost}</span>
                      </td>
                      <td className="py-3 px-4 text-center stat-number text-emerald-400">{season.goals_for}</td>
                      <td className="py-3 px-4 text-center stat-number text-red-400">{season.goals_against}</td>
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
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">荣誉室</h3>
          {honorsLoading ? (
            <div className="space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-24 bg-[#1E1E2D] animate-pulse" />
              ))}
            </div>
          ) : !teamHonors || teamHonors.honors.length === 0 ? (
            <div className="text-center py-16">
              <Award className="w-16 h-16 text-[#4B4B6A] mx-auto mb-4" />
              <h4 className="text-xl font-bold text-white mb-2">还没有冠军奖杯</h4>
              <p className="text-[#8B8BA7] mb-2">这支球队尚未获得任何冠军荣誉</p>
              <p className="text-[#C6F135] text-sm font-medium">继续加油，冠军就在前方！🏆</p>
            </div>
          ) : (
            <div>
              <div className="flex items-center gap-6 mb-6 text-sm">
                <div className="flex items-center gap-2">
                  <Trophy className="w-4 h-4 text-amber-400" />
                  <span className="text-[#8B8BA7]">联赛冠军:</span>
                  <span className="font-bold text-white">{teamHonors.total_league_titles}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Award className="w-4 h-4 text-[#C6F135]" />
                  <span className="text-[#8B8BA7]">杯赛冠军:</span>
                  <span className="font-bold text-white">{teamHonors.total_cup_titles}</span>
                </div>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
                {teamHonors.honors.map((honor, idx) => (
                  <Card key={idx} className="bg-[#12121A] border-2 border-[#2D2D44] p-4 text-center hover:border-amber-500/50 transition-all">
                    <div className="text-3xl mb-2">{honor.honor_type === 'league_champion' ? '🏆' : '🥇'}</div>
                    <h4 className="font-bold text-white text-sm mb-1">{honor.competition_name}</h4>
                    <p className="text-xs text-[#8B8BA7]">第 {honor.season_number} 赛季</p>
                    {honor.competition_level && honor.competition_level > 0 && (
                      <span className="inline-block mt-2 px-2 py-0.5 text-[10px] bg-[#1E1E2D] border border-[#2D2D44] text-[#8B8BA7]">
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
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">球队纪录</h3>
          {recordsLoading ? (
            <div className="text-center py-16 text-[#8B8BA7]">加载中...</div>
          ) : !teamRecords ? (
            <div className="text-center py-12">
              <Target className="w-12 h-12 text-[#4B4B6A] mx-auto mb-3" />
              <p className="text-[#8B8BA7]">暂无纪录数据</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {RECORD_TYPES_BY_CATEGORY[RecordCategory.TEAM].map((type: RecordType) => {
                const record = teamRecords.team.find((r) => r.record_type === type)
                return record ? (
                  <Card key={type} className="bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all">
                    <div className="flex items-start gap-4">
                      <div className="shrink-0">
                        <div className="w-12 h-12 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30 flex items-center justify-center">
                          <Target className="w-6 h-6 text-[#0D7377]" />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="text-sm font-bold text-white truncate">{record.record_type_label}</h3>
                          <span className="text-lg font-bold stat-number pixel-number text-[#C6F135]">{record.record_value}</span>
                        </div>
                        <div className="mt-1 text-sm text-[#8B8BA7]">{record.holder_name}</div>
                        {record.season_number !== undefined && (
                          <div className="mt-1 text-xs text-[#4B4B6A]">第 {record.season_number} 赛季</div>
                        )}
                      </div>
                    </div>
                  </Card>
                ) : (
                  <Card key={type} className="bg-[#12121A] border-2 border-[#2D2D44]/60 opacity-60">
                    <div className="flex items-start gap-4">
                      <div className="shrink-0">
                        <div className="w-12 h-12 bg-[#0D4A4D]/20 border-2 border-[#0D7377]/20 flex items-center justify-center">
                          <Target className="w-6 h-6 text-[#0D7377]/50" />
                        </div>
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <h3 className="text-sm font-bold text-[#8B8BA7] truncate">{RECORD_TYPE_LABELS[type]}</h3>
                          <span className="text-lg font-bold stat-number pixel-number text-[#4B4B6A]">—</span>
                        </div>
                        <div className="mt-1 text-sm text-[#4B4B6A]">暂无该纪录</div>
                      </div>
                    </div>
                  </Card>
                )
              })}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

export default TeamDetail
