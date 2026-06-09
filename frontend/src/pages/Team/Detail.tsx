import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  ChevronLeft,
  Trophy,
} from '../../components/ui/pixel-icons'
import { getPositionColor, type PlayerListItem, type PlayerState } from '../../types/player'
import { api } from '../../api/client'

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

const positionOrder = { GK: 0, DF: 1, MF: 2, FW: 3 }

const formLabel: Record<string, string> = {
  HOT: '火热',
  GOOD: '良好',
  NEUTRAL: '平稳',
  LOW: '低迷',
}

const availabilityLabel: Record<string, string> = {
  ACTIVE: '可用',
  INJURED: '伤停',
  SUSPENDED: '停赛',
  RETIRED: '退役',
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
  if (fitness >= 80) return 'bg-[#9ECF45]'
  if (fitness >= 55) return 'bg-amber-500'
  return 'bg-red-500'
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

  const leagueId = team?.league_id || team?.current_league_id

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
                        <td className={formColor[state?.visible_form || 'NEUTRAL']}>
                          {state ? `${formLabel[state.visible_form]} · ${availabilityLabel[state.availability] || state.availability}` : '-'}
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
    </div>
  )
}

export default TeamDetail
