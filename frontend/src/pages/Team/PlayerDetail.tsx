import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
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
} from '../../components/ui/pixel-icons'
import { ContractModal } from '../../components/players/ContractModal'
import {
  POSITION_NAMES,
  getPositionColor,
  type Player,
  type PlayerContract,
  type PlayerState,
  type PlayerHistoryResponse,
} from '../../types/player'
import { api } from '../../api/client'

type ProfileTab = 'overview' | 'abilities' | 'career' | 'records'

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
  { id: 'records', label: '纪录', icon: Trophy },
]

const FOOT_NAMES: Record<string, string> = {
  RIGHT: '右脚',
  LEFT: '左脚',
  BOTH: '双脚',
}

const STATUS_NAMES: Record<string, string> = {
  ACTIVE: '可出场',
  INJURED: '伤病',
  SUSPENDED: '停赛',
  RETIRED: '退役',
}

const FORM_NAMES: Record<string, string> = {
  HOT: '火热',
  GOOD: '良好',
  NEUTRAL: '稳定',
  LOW: '低迷',
}

const ROLE_NAMES: Record<string, string> = {
  key_player: '核心球员',
  first_team: '一线队',
  rotation: '轮换',
  backup: '替补',
  hot_prospect: '希望之星',
  youngster: '青训球员',
  not_needed: '不在计划',
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

function metricPer90(value: number, minutes: number) {
  if (!minutes) return '0.00'
  return ((value / minutes) * 90).toFixed(2)
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
  const { id } = useParams<{ id: string }>()
  const [player, setPlayer] = useState<Player | null>(null)
  const [contract, setContract] = useState<PlayerContract | null>(null)
  const [playerState, setPlayerState] = useState<PlayerState | null>(null)
  const [history, setHistory] = useState<PlayerHistoryResponse | null>(null)
  const [activeTab, setActiveTab] = useState<ProfileTab>('abilities')
  const [showContractModal, setShowContractModal] = useState(false)
  const [loading, setLoading] = useState(true)

  const fetchData = async () => {
    if (!id) return
    setLoading(true)
    try {
      const [playerRes, contractRes, stateRes, historyRes] = await Promise.all([
        api.get<Player>(`/players/${id}`),
        api.get<PlayerContract>(`/players/${id}/contract`).catch(() => null),
        api.get<PlayerState>(`/players/${id}/state`).catch(() => null),
        api.get<PlayerHistoryResponse>(`/players/${id}/history`).catch(() => null),
      ])
      if (playerRes.success) setPlayer(playerRes.data)
      if (contractRes?.success) setContract(contractRes.data)
      if (stateRes?.success) setPlayerState(stateRes.data)
      if (historyRes?.success) setHistory(historyRes.data)
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

  const statusName = STATUS_NAMES[playerState?.availability || player.status] || '未知'
  const formName = FORM_NAMES[playerState?.visible_form || player.match_form] || '未知'
  const fitness = playerState?.fitness ?? player.fitness ?? 0
  const avatarSrc = player.avatar_url ? `/${player.avatar_url}` : '/locker-room/jersey-placeholder-v1.png'
  const backTo = player.team_id ? `/teams/${player.team_id}` : '/dashboard'
  const played = player.matches_played || 0
  const minutes = player.minutes_played || 0

  const overviewStats = [
    { label: '每90分钟进球', value: metricPer90(player.goals || 0, minutes) },
    { label: '每90分钟助攻', value: metricPer90(player.assists || 0, minutes) },
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
    .slice(0, 6)

  const weakAttributes = attributeGroups
    .flatMap(group => group.items.map(item => ({ ...item, value: getAbilityValue(player, item.key) })))
    .sort((a, b) => a.value - b.value)
    .slice(0, 4)

  const contractEnd = contract?.end_season_number ?? player.contract_end_season
  const releaseClause = contract?.release_clause ?? player.release_clause

  return (
    <div className="player-profile-page player-desk-page">
      <div className="player-profile-topbar player-desk-topbar">
        <Link to={backTo} className="profile-back-link">
          <ChevronLeft className="h-4 w-4" />
          返回球队
        </Link>
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
            <div className="dossier-vitals">
              <span>{POSITION_NAMES[player.position]}</span>
              <span>{player.age}岁</span>
              <span>{player.height}cm / {player.weight}kg</span>
              <span>{FOOT_NAMES[player.preferred_foot] || '-'}</span>
              <span>{statusName}</span>
            </div>
          </div>
          <div className="dossier-score">
            <span>OVR</span>
            <strong>{player.ovr}</strong>
          </div>
          <div className="dossier-score is-potential">
            <span>POT</span>
            <strong>{player.potential_letter}</strong>
          </div>
          <div className="dossier-status">
            <ProfileDataLine label="状态" value={formName} />
            <ProfileDataLine label="体能" value={`${fitness}%`} />
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
              <div className="desk-overview-grid">
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
                  <div className="profile-hints muted">这里按当前能力低项排序，不代表战术必然弱点。</div>
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
              <div className="profile-panel-heading">
                <div>
                  <h2>位置化能力</h2>
                </div>
                <strong>OVR {player.ovr}</strong>
              </div>
              <div className="ability-overview">
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
                <div className="ability-radar-notes">
                  <h3>能力概览</h3>
                  <p>雷达图按位置汇总能力，不替代下方 1-20 单项数值。颜色规则：白色为基础，绿色为可靠，金色为精英。</p>
                  <div>
                    <span><i className="is-basic" />1-10</span>
                    <span><i className="is-good" />11-15</span>
                    <span><i className="is-elite" />16-20</span>
                  </div>
                </div>
              </div>
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
                          <td>{row.team_name}</td>
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

          {activeTab === 'records' && (
            <section className="profile-panel">
              <div className="profile-panel-heading">
                <div>
                  <h2>生涯里程碑</h2>
                </div>
                <strong>{milestones.length}</strong>
              </div>
              {milestones.length > 0 ? (
                <div className="record-grid">
                  {milestones.map((m, i) => (
                    <div key={`${m.milestone_type}-${i}`} className="record-tile">
                      <span>{m.description}</span>
                      <strong>第 {m.season_number} 赛季</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="career-empty-note">暂无生涯里程碑</div>
              )}
            </section>
          )}
          </main>

          <aside className="player-intel-rail">
          <div className="intel-card-scene">
            <img src={avatarSrc} alt={player.name} />
            <div>
              <span>{POSITION_NAMES[player.position]}</span>
              <strong>{ROLE_NAMES[player.squad_role] || player.squad_role || '-'}</strong>
            </div>
          </div>
          <section className="profile-panel profile-status-panel">
            <div className="profile-panel-heading compact">
              <div>
                <h2>情报栏</h2>
              </div>
            </div>
            <div className="fitness-gauge">
              <div style={{ height: `${Math.max(0, Math.min(fitness, 100))}%` }} />
              <strong>{fitness}%</strong>
            </div>
            <ProfileDataLine label="可用状态" value={statusName} />
            <ProfileDataLine label="比赛状态" value={formName} />
            <ProfileDataLine label="趋势" value={playerState?.trend || '-'} />
            <ProfileDataLine label="市场价值" value={formatMoney(player.market_value)} />
            <ProfileDataLine label="工资" value={formatMoney(player.wage)} />
            <ProfileDataLine label="合同到期" value={contractEnd ? `第 ${contractEnd} 赛季` : '自由身'} />
            <ProfileDataLine label="解约金" value={formatMoney(releaseClause)} />
            {playerState?.hints?.length ? (
              <div className="profile-hints">
                {playerState.hints.map((hint, index) => <p key={index}>{hint}</p>)}
              </div>
            ) : (
              <div className="profile-hints muted">暂无状态提示</div>
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

function ProfileDataLine({ label, value }: { label: string; value: string | number }) {
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
