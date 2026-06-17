import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import {
  Award,
  Calendar,
  Chart,
  ChevronLeft,
  Clock,
  PenSquare,
  Shield,
  Target,
  Trophy,
  User,
  Thermometer,
  SquareAlert,
  Skull,
  Medal,
} from '../../components/ui/pixel-icons'
import { ContractModal } from '../../components/players/ContractModal'
import {
  getPositionColor,
  type Player,
  type PlayerContract,
  type PlayerState,
  type PlayerHistoryResponse,
  type PlayerFeedback,
  type PlayerRecentMatch,
} from '../../types/player'
import { usePlayerAwards, usePlayerAwardSummary } from '../../hooks/useAwards'
import { AWARD_LABELS, AWARD_ICONS } from '../../types/awards'
import type { PlayerAward } from '../../types/awards'
import { api } from '../../api/client'

type ProfileTab = 'overview' | 'abilities' | 'career' | 'recent' | 'timeline' | 'records' | 'honors'

interface AttributeItem {
  key: keyof Player
  label: string
}

interface AttributeGroup {
  title: string
  subtitle: string
  items: AttributeItem[]
}

const TABS: { id: ProfileTab; label: string; icon: typeof User }[] = [
  { id: 'abilities', label: '能力', icon: Chart },
  { id: 'overview', label: '档案', icon: User },
  { id: 'career', label: '生涯', icon: Calendar },
  { id: 'recent', label: '近期比赛', icon: Clock },
  { id: 'timeline', label: '轨迹', icon: Trophy },
  { id: 'records', label: '纪录', icon: Award },
  { id: 'honors', label: '荣誉', icon: Medal },
]

const STATUS_NAMES: Record<string, string> = {
  ACTIVE: '可出场',
  INJURED: '伤病',
  SUSPENDED: '停赛',
  RETIRED: '退役',
}

function StatusBadge({ status, current_suspension }: { status: string; current_suspension?: Player['current_suspension'] }) {
  if (status === 'INJURED') {
    return (
      <span className="inline-flex items-center gap-1 text-red-400" title="伤病中，无法出场">
        <Thermometer className="h-4 w-4" />
        {STATUS_NAMES[status] || status}
      </span>
    )
  }
  if (status === 'SUSPENDED') {
    const detail = current_suspension
      ? `停赛中，剩余 ${current_suspension.matches_remaining} 场`
      : '停赛中，无法出场'
    return (
      <span className="inline-flex items-center gap-1 text-amber-400" title={detail}>
        <SquareAlert className="h-4 w-4" />
        {STATUS_NAMES[status] || status}
      </span>
    )
  }
  if (status === 'RETIRED') {
    return (
      <span className="inline-flex items-center gap-1 text-gray-500" title="已退役">
        <Skull className="h-4 w-4" />
        {STATUS_NAMES[status] || status}
      </span>
    )
  }
  return <span>{STATUS_NAMES[status] || status}</span>
}

const FORM_NAMES: Record<string, string> = {
  HOT: '火热',
  GOOD: '良好',
  NEUTRAL: '稳定',
  LOW: '低迷',
}


const FIELD_ATTRIBUTE_GROUPS: AttributeGroup[] = [
  {
    title: '终结与进攻',
    subtitle: '射门、禁区处理和无球威胁',
    items: [
      { key: 'sho', label: '射门' },
      { key: 'fin', label: '远射' },
      { key: 'hea', label: '头球' },
      { key: 'pk', label: '点球' },
      { key: 'fk', label: '任意球' },
    ],
  },
  {
    title: '控球与传递',
    subtitle: '组织推进和前场连接能力',
    items: [
      { key: 'pas', label: '传球' },
      { key: 'vis', label: '视野' },
      { key: 'dri', label: '盘带' },
      { key: 'con', label: '控球' },
      { key: 'cro', label: '传中' },
      { key: 'dec', label: '球商' },
    ],
  },
  {
    title: '身体与防守',
    subtitle: '对抗、覆盖和抢断质量',
    items: [
      { key: 'spd', label: '速度' },
      { key: 'acc', label: '爆发' },
      { key: 'str', label: '力量' },
      { key: 'sta', label: '体能' },
      { key: 'bal', label: '平衡' },
      { key: 'defe', label: '防守' },
      { key: 'tkl', label: '抢断' },
    ],
  },
]

const GK_ATTRIBUTE_GROUPS: AttributeGroup[] = [
  {
    title: '门将技术',
    subtitle: '扑救、反应和出击选择',
    items: [
      { key: 'sav', label: '扑救' },
      { key: 'ref', label: '反应' },
      { key: 'pos', label: '站位' },
      { key: 'rus', label: '出击' },
      { key: 'com', label: '镇定' },
      { key: 'dec', label: '球商' },
    ],
  },
  {
    title: '身体与脚下',
    subtitle: '覆盖范围和后场出球',
    items: [
      { key: 'spd', label: '速度' },
      { key: 'acc', label: '爆发' },
      { key: 'str', label: '力量' },
      { key: 'sta', label: '体能' },
      { key: 'pas', label: '传球' },
      { key: 'fk', label: '任意球' },
      { key: 'pk', label: '点球' },
    ],
  },
]

function formatNumber(value?: number | null, fallback = '-') {
  return value === undefined || value === null ? fallback : String(value)
}

function formatMoney(value?: number | null) {
  if (!value) return '-'
  if (value >= 1000000) return `€${(value / 1000000).toFixed(1)}M`
  return `€${Math.round(value / 1000)}K`
}

function getAbilityValue(player: Player, key: keyof Player) {
  const nested = player.abilities?.[key as keyof NonNullable<Player['abilities']>]
  const direct = player[key]
  return typeof nested === 'number' ? nested : typeof direct === 'number' ? direct : 0
}

function metricPer50(value: number, minutes: number) {
  if (!minutes) return '0.00'
  return ((value / minutes) * 50).toFixed(2)
}

function formatMatchDate(dateStr: string) {
  const d = new Date(dateStr)
  if (Number.isNaN(d.getTime())) return dateStr
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function getAbilityTone(value: number) {
  if (value >= 16) return 'is-elite'
  if (value >= 11) return 'is-good'
  return 'is-basic'
}

function getRadarPoint(value: number, index: number, total: number) {
  const angle = (Math.PI * 2 * index) / total - Math.PI / 2
  const radius = 44 * (Math.max(0, Math.min(value, 20)) / 20)
  const x = 50 + Math.cos(angle) * radius
  const y = 50 + Math.sin(angle) * radius
  return `${x.toFixed(2)},${y.toFixed(2)}`
}

function PlayerDetail() {
  const navigate = useNavigate()
  const { id } = useParams<{ id: string }>()
  const [player, setPlayer] = useState<Player | null>(null)
  const [contract, setContract] = useState<PlayerContract | null>(null)
  const [playerState, setPlayerState] = useState<PlayerState | null>(null)
  const [history, setHistory] = useState<PlayerHistoryResponse | null>(null)
  const [feedbacks, setFeedbacks] = useState<PlayerFeedback[]>([])
  const [recentMatches, setRecentMatches] = useState<PlayerRecentMatch[]>([])
  const [activeTab, setActiveTab] = useState<ProfileTab>('abilities')
  const [showContractModal, setShowContractModal] = useState(false)
  const [loading, setLoading] = useState(true)

  const { awards: playerAwards, loading: awardsLoading } = usePlayerAwards(id)
  const { summary: awardSummary } = usePlayerAwardSummary(id)

  const fetchData = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [playerRes, contractRes, stateRes, historyRes, feedbackRes, recentRes] = await Promise.all([
        api.get<Player>(`/players/${id}`),
        api.get<PlayerContract>(`/players/${id}/contract`).catch(() => null),
        api.get<PlayerState>(`/players/${id}/state`).catch(() => null),
        api.get<PlayerHistoryResponse>(`/players/${id}/history`).catch(() => null),
        api.get<PlayerFeedback[]>(`/players/${id}/feedback`).catch(() => null),
        api.getPlayerRecentMatches(id, 20).catch(() => null),
      ])
      if (playerRes.success) setPlayer(playerRes.data)
      if (contractRes?.success) setContract(contractRes.data)
      if (stateRes?.success) setPlayerState(stateRes.data)
      if (historyRes?.success) setHistory(historyRes.data)
      if (feedbackRes?.success) setFeedbacks(feedbackRes.data)
      if (recentRes?.success) setRecentMatches(recentRes.data)
    } catch {
      setPlayer(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [id])

  useEffect(() => {
    setActiveTab('abilities')
  }, [id])

  const attributeGroups = useMemo(
    () => (player?.position === 'GK' ? GK_ATTRIBUTE_GROUPS : FIELD_ATTRIBUTE_GROUPS),
    [player?.position]
  )

  if (loading) {
    return <div className="player-profile-page player-profile-empty">正在读取球员档案...</div>
  }

  if (!player) {
    return <div className="player-profile-page player-profile-empty">球员未找到</div>
  }

  const formName = FORM_NAMES[playerState?.visible_form || player.match_form] || '未知'
  const fitness = playerState?.fitness ?? player.fitness ?? 0
  const avatarSrc = player.avatar_url ? `/${player.avatar_url}` : '/locker-room/jersey-placeholder-v1.png'
  const played = player.matches_played || 0
  const minutes = player.minutes_played || 0

  const overviewStats = [
    { label: '每50分钟进球', value: metricPer50(player.goals || 0, minutes) },
    { label: '每50分钟助攻', value: metricPer50(player.assists || 0, minutes) },
    { label: '射正率', value: `${formatNumber(player.shot_accuracy, '0')}%` },
    { label: '传球成功率', value: `${formatNumber(player.pass_accuracy, '0')}%` },
    { label: '抢断成功率', value: `${formatNumber(player.tackle_accuracy, '0')}%` },
    { label: '场均触球', value: played ? ((player.touches || 0) / played).toFixed(1) : '0.0' },
  ]

  const seasons = history?.seasons ?? []
  const milestones = history?.milestones ?? []

  const highlightedAttributes = attributeGroups
    .flatMap(group => group.items.map(item => ({ ...item, value: getAbilityValue(player, item.key) })))
    .sort((a, b) => b.value - a.value)
    .slice(0, 5)

  const weakAttributes = attributeGroups
    .flatMap(group => group.items.map(item => ({ ...item, value: getAbilityValue(player, item.key) })))
    .sort((a, b) => a.value - b.value)
    .slice(0, 5)

  const personalRecords = (() => {
    if (!history) return []
    const recs: { label: string; value: string; season?: number }[] = []
    const s = history.seasons

    if (history.summary) {
      recs.push({ label: '生涯总出场', value: String(history.summary.total_matches) })
      recs.push({ label: '生涯总进球', value: String(history.summary.total_goals) })
      recs.push({ label: '生涯总助攻', value: String(history.summary.total_assists) })
      recs.push({ label: '生涯场均评分', value: history.summary.overall_average_rating?.toFixed(2) ?? '-' })
    }

    if (s.length > 0) {
      const maxGoals = s.reduce((a, b) => (a.goals > b.goals ? a : b))
      recs.push({ label: '单赛季最多进球', value: String(maxGoals.goals), season: maxGoals.season_number })

      const maxAssists = s.reduce((a, b) => (a.assists > b.assists ? a : b))
      recs.push({ label: '单赛季最多助攻', value: String(maxAssists.assists), season: maxAssists.season_number })

      const maxRating = s.reduce((a, b) => ((a.average_rating || 0) > (b.average_rating || 0) ? a : b))
      recs.push({ label: '单赛季最高评分', value: maxRating.average_rating?.toFixed(2) ?? '-', season: maxRating.season_number })

      const maxApps = s.reduce((a, b) => (a.matches_played > b.matches_played ? a : b))
      recs.push({ label: '单赛季最多出场', value: String(maxApps.matches_played), season: maxApps.season_number })

      const maxMinutes = s.reduce((a, b) => (a.minutes_played > b.minutes_played ? a : b))
      recs.push({ label: '单赛季最多分钟', value: String(maxMinutes.minutes_played), season: maxMinutes.season_number })

      const maxSaves = s.reduce((a, b) => ((a.saves || 0) > (b.saves || 0) ? a : b))
      if (maxSaves.saves > 0) {
        recs.push({ label: '单赛季最多扑救', value: String(maxSaves.saves), season: maxSaves.season_number })
      }

      const maxCS = s.reduce((a, b) => ((a.clean_sheets || 0) > (b.clean_sheets || 0) ? a : b))
      if (maxCS.clean_sheets > 0) {
        recs.push({ label: '单赛季最多零封', value: String(maxCS.clean_sheets), season: maxCS.season_number })
      }
    }

    return recs
  })()

  const contractEnd = contract?.end_season_number ?? player.contract_end_season
  const releaseClause = contract?.release_clause ?? player.release_clause

  return (
    <div className="player-profile-page player-desk-page">
      <div className="player-profile-topbar player-desk-topbar">
        <button type="button" onClick={() => navigate(-1)} className="profile-back-link">
          <ChevronLeft className="h-4 w-4" />
          返回上一页
        </button>
        {player.team_id && (
          <button className="profile-contract-btn" onClick={() => setShowContractModal(true)}>
            <PenSquare className="h-4 w-4" />
            {contract ? '合同处理' : '签约'}
          </button>
        )}
      </div>

      <div className="dossier-card-shell">
        <section className="player-dossier-strip">
          <div className="dossier-avatar">
            <img src={avatarSrc} alt={player.name} />
          </div>
          <div className="dossier-identity">
            <div className="dossier-name-row">
              <h1>{player.name}</h1>
              <span className={`profile-position ${getPositionColor(player.position)}`}>{player.position}</span>
              <span className="profile-number">#{player.squad_number || player.preferred_number || '-'}</span>
            </div>
            {player.short_description && (
              <div className="dossier-tagline">{player.short_description}</div>
            )}
            <div className="dossier-vitals">
              {player.team_id ? (
                <Link
                  to={`/teams/${player.team_id}`}
                  className="dossier-team-link"
                  title="查看球队"
                >
                  {player.team_name || '未知球队'}
                </Link>
              ) : (
                <span>自由球员</span>
              )}
              <span className="dossier-vitals-sep">·</span>
              <span>{player.age}岁</span>
              <span className="dossier-vitals-sep">·</span>
              <span>{player.height}cm</span>
              <span className="dossier-vitals-sep">·</span>
              <StatusBadge status={player.status} current_suspension={player.current_suspension} />
            </div>
          </div>
          <div className="dossier-ovr-block">
            <div className="dossier-ovr-big">{player.ovr}</div>
            <span className={`potential-badge potential-badge--${(player.potential_letter || 'D').toLowerCase()}`}>
              {player.potential_letter}
            </span>
          </div>
        </section>

        <nav className="player-profile-tabs player-workbench-tabs dossier-bookmarks" aria-label="球员详情标签">
            {TABS.map(tab => {
              const Icon = tab.icon
              return (
                <button
                  key={tab.id}
                  className={activeTab === tab.id ? 'is-active' : ''}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon className="h-4 w-4" />
                  {tab.label}
                </button>
              )
            })}
        </nav>

        <div className="player-workbench">
          <main className="player-workbench-main">

          {activeTab === 'overview' && (
            <section className="profile-panel profile-main-panel">
              <div className="profile-panel-heading">
                <div>
                  <h2>总览判断</h2>
                </div>
                <strong>{played} 场 · {minutes} 分钟</strong>
              </div>
              <div className="desk-overview-grid has-radar">
                <div className="desk-radar-card">
                  <h3><Chart className="h-4 w-4" />能力概览</h3>
                  <AbilityRadar
                    values={[
                      { label: '进攻', value: player.position === 'GK' ? getAbilityValue(player, 'sav') : Math.round((getAbilityValue(player, 'sho') + getAbilityValue(player, 'fin')) / 2) },
                      { label: '传控', value: Math.round((getAbilityValue(player, 'pas') + getAbilityValue(player, 'con') + getAbilityValue(player, 'vis')) / 3) },
                      { label: '速度', value: Math.round((getAbilityValue(player, 'spd') + getAbilityValue(player, 'acc')) / 2) },
                      { label: '身体', value: Math.round((getAbilityValue(player, 'str') + getAbilityValue(player, 'sta') + getAbilityValue(player, 'bal')) / 3) },
                      { label: '防守', value: player.position === 'GK' ? getAbilityValue(player, 'pos') : Math.round((getAbilityValue(player, 'defe') + getAbilityValue(player, 'tkl')) / 2) },
                      { label: '心智', value: Math.round((getAbilityValue(player, 'dec') + getAbilityValue(player, 'com')) / 2) },
                    ]}
                  />
                </div>
                <div className="desk-ability-summary">
                  <h3><Chart className="h-4 w-4" />最强能力</h3>
                  {highlightedAttributes.map(item => (
                    <AbilityRow key={String(item.key)} label={item.label} value={item.value} />
                  ))}
                </div>
                <div className="desk-ability-summary">
                  <h3><Target className="h-4 w-4" />需要关注</h3>
                  {weakAttributes.map(item => (
                    <AbilityRow key={String(item.key)} label={item.label} value={item.value} />
                  ))}
                </div>
              </div>
              <div className="performance-strip desk-performance-strip">
                {overviewStats.map(item => (
                  <div key={item.label}>
                    <span>{item.label}</span>
                    <strong>{item.value}</strong>
                  </div>
                ))}
              </div>
              <div className="profile-stat-columns">
                <div>
                  <h3><Target className="h-4 w-4" />进攻</h3>
                  <ProfileDataLine label="射门 / 射正" value={`${player.shots || 0} / ${player.shots_on_target || 0}`} />
                  <ProfileDataLine label="进球 / 助攻" value={`${player.goals || 0} / ${player.assists || 0}`} />
                  <ProfileDataLine label="盘带 / 成功" value={`${player.dribbles || 0} / ${player.dribbles_succ || 0}`} />
                  <ProfileDataLine label="关键传球" value={formatNumber(player.key_passes)} />
                </div>
                <div>
                  <h3><Shield className="h-4 w-4" />防守</h3>
                  <ProfileDataLine label="抢断 / 成功" value={`${player.tackles || 0} / ${player.tackles_succ || 0}`} />
                  <ProfileDataLine label="拦截" value={formatNumber(player.interceptions)} />
                  <ProfileDataLine label="解围" value={formatNumber(player.clearances)} />
                  <ProfileDataLine label="封堵" value={formatNumber(player.blocks)} />
                </div>
                <div>
                  <h3><Clock className="h-4 w-4" />负荷</h3>
                  <ProfileDataLine label="出场时间" value={`${minutes} 分钟`} />
                  <ProfileDataLine label="黄牌 / 红牌" value={`${player.yellow_cards || 0} / ${player.red_cards || 0}`} />
                  <ProfileDataLine label="犯规 / 被犯规" value={`${player.fouls || 0} / ${player.fouls_drawn || 0}`} />
                  <ProfileDataLine label="失误" value={formatNumber(player.turnovers)} />
                </div>
              </div>
            </section>
          )}

          {activeTab === 'abilities' && (
            <section className="profile-panel">
              <div className="ability-board">
                {attributeGroups.map(group => (
                  <div key={group.title} className="ability-cluster">
                    <div className="ability-cluster-title">
                      <h3>{group.title}</h3>
                      <p>{group.subtitle}</p>
                    </div>
                    {group.items.map(item => {
                      const value = getAbilityValue(player, item.key)
                      return <AbilityRow key={String(item.key)} label={item.label} value={value} />
                    })}
                  </div>
                ))}
              </div>
              {player.skills?.length ? (
                <div className="signature-skills">
                  <h3><Award className="h-4 w-4" />招牌技能</h3>
                  <div>
                    {player.skills.map((skill, index) => (
                      <span key={`${skill.skill_id}-${index}`}>{skill.skill_id}<em>{skill.quality || skill.rarity}</em></span>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="signature-skills muted">暂无招牌技能</div>
              )}
            </section>
          )}

          {activeTab === 'career' && (
            <section className="profile-panel">
              <div className="profile-panel-heading">
                <div>
                  <h2>生涯赛季</h2>
                </div>
                <strong>{seasons.length} 个赛季</strong>
              </div>
              <div className="career-table-wrap">
                {seasons.length > 0 ? (
                  <table className="career-table">
                    <thead>
                      <tr>
                        <th>赛季</th>
                        <th>球队</th>
                        <th>出场</th>
                        <th>进球</th>
                        <th>助攻</th>
                        <th>评分</th>
                      </tr>
                    </thead>
                    <tbody>
                      {seasons.map(row => (
                        <tr key={row.season_number}>
                          <td>第 {row.season_number} 赛季</td>
                          <td>
                            {row.team_id ? (
                              <Link to={`/teams/${row.team_id}`} className="text-[var(--skin-accent)] hover:underline">
                                {row.team_name}
                              </Link>
                            ) : (
                              row.team_name
                            )}
                          </td>
                          <td>{row.matches_played}</td>
                          <td>{row.goals}</td>
                          <td>{row.assists}</td>
                          <td>{row.average_rating || '-'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="career-empty-note">暂无生涯数据</div>
                )}
              </div>
            </section>
          )}

          {activeTab === 'recent' && (
            <section className="profile-panel">
              <div className="profile-panel-heading">
                <div>
                  <h2>近期比赛</h2>
                </div>
                <strong>{recentMatches.length} 场</strong>
              </div>
              <div className="career-table-wrap">
                {recentMatches.length > 0 ? (
                  <table className="career-table">
                    <thead>
                      <tr>
                        <th>日期</th>
                        <th>赛事</th>
                        <th>对阵</th>
                        <th>结果</th>
                        <th>评分</th>
                        <th>时间</th>
                        <th>进球</th>
                        <th>助攻</th>
                        <th>射门</th>
                        <th>传球</th>
                        <th>抢断(成功)</th>
                        <th>扑救</th>
                        <th>牌</th>
                      </tr>
                    </thead>
                    <tbody>
                      {recentMatches.map((m) => {
                        const isHome = m.side === 'home'
                        const teamName = isHome ? m.home_team_name : m.away_team_name
                        const oppName = isHome ? m.away_team_name : m.home_team_name
                        const resultClass =
                          m.result === 'win'
                            ? 'text-emerald-400'
                            : m.result === 'loss'
                            ? 'text-red-400'
                            : 'text-amber-400'
                        const resultLabel = m.result === 'win' ? '胜' : m.result === 'loss' ? '负' : '平'
                        return (
                          <tr key={m.fixture_id}>
                            <td>{formatMatchDate(m.match_date)}</td>
                            <td>
                              <span className="text-xs text-[#707A8A]">{m.competition}</span>
                            </td>
                            <td>
                              <Link
                                to={`/match/${m.fixture_id}`}
                                className="text-xs hover:text-[var(--skin-accent)] transition-colors"
                                title="查看比赛详情"
                              >
                                <span className="hover:underline">{teamName}</span>
                                {' '}
                                <span className="font-medium">{m.home_score}-{m.away_score}</span>
                                {' '}
                                <span className="hover:underline">{oppName}</span>
                              </Link>
                            </td>
                            <td className={resultClass}>{resultLabel}</td>
                            <td>{m.rating ? m.rating.toFixed(1) : '-'}</td>
                            <td>{m.minutes_played}'</td>
                            <td>{m.goals}</td>
                            <td>{m.assists}</td>
                            <td>
                              {m.shots}
                              {m.shots_on_target > 0 ? `(${m.shots_on_target})` : ''}
                            </td>
                            <td>
                              {m.passes}
                              {m.key_passes > 0 ? `(${m.key_passes})` : ''}
                            </td>
                            <td>
                              {m.tackles}
                              {m.tackles_succ > 0 ? `(${m.tackles_succ})` : ''}
                            </td>
                            <td>{m.saves > 0 ? m.saves : '-'}</td>
                            <td>
                              {m.yellow_cards > 0 && <span className="text-amber-400">黄{m.yellow_cards}</span>}
                              {m.red_cards > 0 && <span className="text-red-400">红{m.red_cards}</span>}
                              {m.yellow_cards === 0 && m.red_cards === 0 && '-'}
                            </td>
                          </tr>
                        )
                      })}
                    </tbody>
                  </table>
                ) : (
                  <div className="career-empty-note">暂无近期比赛数据</div>
                )}
              </div>
            </section>
          )}

          {activeTab === 'timeline' && (
            <section className="profile-panel">
              <div className="profile-panel-heading">
                <div>
                  <h2>生涯轨迹</h2>
                </div>
                <strong>{milestones.length}</strong>
              </div>
              {milestones.length > 0 ? (
                <div className="career-timeline">
                  {milestones.map((m, i) => (
                    <div key={`${m.milestone_type}-${i}`} className="timeline-node">
                      <div className="timeline-event">
                        <span className="timeline-season">第 {m.season_number} 赛季</span>
                        <strong className="timeline-desc">{m.description}</strong>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="career-empty-note">暂无生涯轨迹</div>
              )}
            </section>
          )}

          {activeTab === 'records' && (
            <section className="profile-panel">
              <div className="profile-panel-heading">
                <div>
                  <h2>生涯纪录</h2>
                </div>
                <strong>{personalRecords.length} 项</strong>
              </div>
              {personalRecords.length > 0 ? (
                <div className="record-grid">
                  {personalRecords.map((r, i) => (
                    <div key={i} className="record-tile">
                      <span>{r.label}</span>
                      <strong>{r.value}</strong>
                      {r.season && <p>第 {r.season} 赛季</p>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="career-empty-note">暂无生涯纪录</div>
              )}
            </section>
          )}

          {activeTab === 'honors' && (
            <section className="profile-panel">
              <div className="profile-panel-heading">
                <div>
                  <h2>荣誉室</h2>
                </div>
                <strong>{awardSummary?.total_awards || 0} 项</strong>
              </div>

              {/* 荣誉统计摘要 */}
              {awardSummary && (
                <div className="performance-strip desk-performance-strip mb-6">
                  {awardSummary.mvp_count > 0 && (
                    <div><span>本场最佳</span><strong>{awardSummary.mvp_count}</strong></div>
                  )}
                  {awardSummary.team_of_season_count > 0 && (
                    <div><span>最佳阵容</span><strong>{awardSummary.team_of_season_count}</strong></div>
                  )}
                  {awardSummary.best_position_count > 0 && (
                    <div><span>最佳位置</span><strong>{awardSummary.best_position_count}</strong></div>
                  )}
                  {awardSummary.golden_boot_count > 0 && (
                    <div><span>金靴奖</span><strong>{awardSummary.golden_boot_count}</strong></div>
                  )}
                  {awardSummary.playmaker_count > 0 && (
                    <div><span>助攻王</span><strong>{awardSummary.playmaker_count}</strong></div>
                  )}
                  {awardSummary.golden_glove_count > 0 && (
                    <div><span>金手套</span><strong>{awardSummary.golden_glove_count}</strong></div>
                  )}
                  {awardSummary.golden_wall_count > 0 && (
                    <div><span>金墙奖</span><strong>{awardSummary.golden_wall_count}</strong></div>
                  )}
                  {awardSummary.season_best_player_count > 0 && (
                    <div><span>足球先生</span><strong>{awardSummary.season_best_player_count}</strong></div>
                  )}
                </div>
              )}

              {awardsLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3].map(i => <div key={i} className="h-16 bg-[#1E1E2D] animate-pulse" />)}
                </div>
              ) : playerAwards.length === 0 ? (
                <div className="career-empty-note">暂无荣誉</div>
              ) : (
                <div className="space-y-4">
                  {playerAwards.map((award) => (
                    <PlayerHonorCard key={award.id} award={award} />
                  ))}
                </div>
              )}
            </section>
          )}
          </main>

          <aside className="player-intel-rail">
            <section className="intel-panel">
              <div className="intel-panel-header">
                <h3>情报栏</h3>
              </div>
              {feedbacks.length > 0 && (
                <div className="player-voice">
                  <div className="player-voice-bubble">
                    <p>{feedbacks[0].content}</p>
                  </div>
                  <span className="player-voice-name">—— {player.name}</span>
                </div>
              )}
              <div className="intel-data-rows">
                <div className="intel-row">
                  <span>可用状态</span>
                  <strong><StatusBadge status={player.status} current_suspension={player.current_suspension} /></strong>
                </div>
                <div className="intel-row">
                  <span>比赛状态</span>
                  <strong className={`fm-text--${(playerState?.visible_form || player.match_form || 'NEUTRAL').toLowerCase()}`}>{formName}</strong>
                </div>
                <div className="intel-row">
                  <span>体能</span>
                  <strong className={`fm-text--fitness${fitness >= 80 ? '-good' : fitness >= 50 ? '-mid' : '-bad'}`}>{fitness}%</strong>
                </div>
                <div className="intel-row">
                  <span>趋势</span>
                  <strong>{playerState?.trend || '-'}</strong>
                </div>
                <div className="intel-divider" />
                <div className="intel-row">
                  <span>市场价值</span>
                  <strong className="intel-value-default">{formatMoney(player.market_value)}</strong>
                </div>
                <div className="intel-row">
                  <span>工资</span>
                  <strong className="intel-value-default">{formatMoney(player.wage)}</strong>
                </div>
                <div className="intel-row">
                  <span>合同到期</span>
                  <strong className="intel-value-default">{contractEnd ? `第 ${contractEnd} 赛季` : '自由身'}</strong>
                </div>
                <div className="intel-row">
                  <span>解约金</span>
                  <strong className="intel-value-default">{formatMoney(releaseClause)}</strong>
                </div>
              </div>
              {playerState?.hints?.length ? (
                <div className="intel-hints">
                  {playerState.hints.map((hint, index) => <p key={index}>{hint}</p>)}
                </div>
              ) : (
                <div className="intel-hints muted">暂无状态提示</div>
              )}
            </section>
          </aside>
        </div>
      </div>

      {showContractModal && player.team_id && (
        <ContractModal
          player={player}
          teamId={player.team_id}
          existingContract={contract}
          onClose={() => setShowContractModal(false)}
          onSuccess={fetchData}
        />
      )}
    </div>
  )
}

function PlayerHonorCard({ award }: { award: PlayerAward }) {
  const icon = AWARD_ICONS[award.award_type]
  const label = AWARD_LABELS[award.award_type]
  const isSeasonBest = award.award_type === 'season_best_player'

  return (
    <div className={`flex items-center gap-4 p-3 border transition-all ${
      isSeasonBest ? 'border-[#C6F135]/30 bg-[#C6F135]/5' : 'border-[#2D2D44] bg-[#0B0D14] hover:border-[#0D7377]/30'
    }`}>
      <span className="text-2xl shrink-0">{icon}</span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className={`text-sm font-bold ${isSeasonBest ? 'text-[#C6F135]' : 'text-white'}`}>
            {label}
          </span>
          <span className="text-xs text-[#4B4B6A]">
            第 {award.season_number} 赛季
          </span>
        </div>
        {award.description && (
          <p className="text-xs text-[#8B8BA7] mt-0.5 truncate">{award.description}</p>
        )}
        {award.metadata && (
          <div className="flex flex-wrap gap-2 mt-1 text-xs text-[#8B8BA7]">
            {award.metadata.rating !== undefined && (
              <span>评分 {award.metadata.rating.toFixed(1)}</span>
            )}
            {award.metadata.matches !== undefined && (
              <span>· {award.metadata.matches}场</span>
            )}
            {award.metadata.goals !== undefined && award.metadata.goals > 0 && (
              <span>· {award.metadata.goals}球</span>
            )}
            {award.metadata.assists !== undefined && award.metadata.assists > 0 && (
              <span>· {award.metadata.assists}助</span>
            )}
            {award.metadata.primary_value !== undefined && (
              <span>· {award.metadata.primary_value}</span>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

function ProfileDataLine({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="profile-data-line">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function AbilityRow({ label, value }: { label: string; value: number }) {
  return (
    <div className="ability-row">
      <span>{label}</span>
      <div>
        <i style={{ width: `${Math.max(0, Math.min(value, 20)) * 5}%` }} />
      </div>
      <strong className={`pixel-number ${getAbilityTone(value)}`}>{value}</strong>
    </div>
  )
}

function AbilityRadar({ values }: { values: { label: string; value: number }[] }) {
  const points = values.map((item, index) => getRadarPoint(item.value, index, values.length)).join(' ')
  const rings = [20, 35, 50, 65, 80].map(size => {
    const radius = 44 * (size / 100)
    return values.map((_, index) => {
      const angle = (Math.PI * 2 * index) / values.length - Math.PI / 2
      return `${(50 + Math.cos(angle) * radius).toFixed(2)},${(50 + Math.sin(angle) * radius).toFixed(2)}`
    }).join(' ')
  })

  return (
    <div className="ability-radar-card">
      <svg viewBox="0 0 100 100" role="img" aria-label="能力雷达图">
        {rings.map((ring, index) => <polygon key={index} points={ring} className="radar-ring" />)}
        {values.map((_, index) => (
          <line
            key={index}
            x1="50"
            y1="50"
            x2={getRadarPoint(20, index, values.length).split(',')[0]}
            y2={getRadarPoint(20, index, values.length).split(',')[1]}
            className="radar-axis"
          />
        ))}
        <polygon points={points} className="radar-shape" />
        {values.map((item, index) => {
          const [x, y] = getRadarPoint(20, index, values.length).split(',').map(Number)
          return (
            <text key={item.label} x={x} y={y} className="radar-label">
              {item.label}
            </text>
          )
        })}
      </svg>
      <div className="radar-value-list">
        {values.map(item => (
          <span key={item.label}>
            {item.label}
            <strong className={`pixel-number ${getAbilityTone(item.value)}`}>{item.value}</strong>
          </span>
        ))}
      </div>
    </div>
  )
}

export default PlayerDetail
