import { useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { api } from '../../api/client'
import type { PlayerAbility, PlayerListItem, PlayerPosition } from '../../types/player'
import type {
  TacticsSetup,
  TeamInstructions,
  InPossessionInstructions,
  TransitionInstructions,
  OutOfPossessionInstructions,
  GoalkeeperDistributionInstructions,
  PlayerInstruction,
  SituationalRule,
  SituationalRuleCondition,
  SituationalRuleOverride,
} from '../../types/tactics'
import {
  Chart,
  Check,
  Download,
  Fire,
  Flag,
  Shield,
  Sword,
  Target,
  Users,
  Zap,
  Cancel,
  Delete,
  Settings2,
  ChevronDown,
} from '../../components/ui/pixel-icons'

type FormationId = 'F01' | 'F02' | 'F03' | 'F04' | 'F05' | 'F06' | 'F07' | 'F08'
type SelectionSource = 'starter' | 'bench'
type TabId = 'personnel' | 'tactics' | 'setpiece' | 'substitution'

type TacticKey = keyof TacticsSetup
type TacticalPlayer = PlayerListItem & { fitness?: number; match_form?: string }
type StarterSlot = ReturnType<typeof getSlots>[number] & { player?: TacticalPlayer }

const TABS: Array<{ id: TabId; label: string }> = [
  { id: 'personnel', label: '人员调整' },
  { id: 'tactics', label: '战术设计' },
  { id: 'setpiece', label: '定位球' },
  { id: 'substitution', label: '换人策略' },
]

const formations: Array<{
  id: FormationId
  name: string
  shape: string
  tag: string
  desc: string
  requirements: { DF: number; MF: number; FW: number }
  lanes: [number, number, number]
  tone: string
}> = [
  { id: 'F01', name: '标准均衡', shape: '2-3-2', tag: '基准', desc: '中路和两翼都保留稳定人数，容错最高。', requirements: { DF: 2, MF: 3, FW: 2 }, lanes: [72, 78, 66], tone: 'text-[#9ECF45]' },
  { id: 'F02', name: '前场压迫', shape: '2-2-3', tag: '高压', desc: '前场三人压迫，适合体能充足的进攻组。', requirements: { DF: 2, MF: 2, FW: 3 }, lanes: [86, 66, 52], tone: 'text-[#D75A4A]' },
  { id: 'F03', name: '强攻风暴', shape: '1-3-3', tag: '强攻', desc: '压上中前场，后场风险明显提高。', requirements: { DF: 1, MF: 3, FW: 3 }, lanes: [92, 74, 36], tone: 'text-[#F97316]' },
  { id: 'F04', name: '钢铁防线', shape: '3-2-2', tag: '稳守', desc: '三后卫保护禁区，反击时依赖前场效率。', requirements: { DF: 3, MF: 2, FW: 2 }, lanes: [58, 64, 88], tone: 'text-[#63B3FF]' },
  { id: 'F05', name: '全员冲锋', shape: '1-2-4', tag: '搏命', desc: '四名前锋压制禁区，体能和失误代价很高。', requirements: { DF: 1, MF: 2, FW: 4 }, lanes: [98, 70, 24], tone: 'text-[#EF4444]' },
  { id: 'F06', name: '深度防守', shape: '3-3-1', tag: '低位', desc: '低位密集防守，适合保护领先或疲劳阵容。', requirements: { DF: 3, MF: 3, FW: 1 }, lanes: [42, 70, 96], tone: 'text-[#60A5FA]' },
  { id: 'F07', name: '菱形控球', shape: '2-4-1', tag: '控球', desc: '中场四人控制节奏，依赖传球与决策。', requirements: { DF: 2, MF: 4, FW: 1 }, lanes: [64, 94, 70], tone: 'text-[#50D1C8]' },
  { id: 'F08', name: '双翼展开', shape: '1-4-2', tag: '边路', desc: '中场与前场拉开宽度，制造传中和转移。', requirements: { DF: 1, MF: 4, FW: 2 }, lanes: [84, 76, 42], tone: 'text-[#D7A94A]' },
]

function defaultSituationalRules(): SituationalRule[] {
  return [
    {
      id: 'rule-behind-late',
      name: '落后追分',
      enabled: true,
      condition: { minute_gte: 40, goal_diff_lte: -1 },
      override: { tempo: 4, shooting_frequency: 4, defensive_line_height: 4, pressing_intensity: 4 },
    },
    {
      id: 'rule-ahead-late',
      name: '领先稳守',
      enabled: true,
      condition: { minute_gte: 40, goal_diff_gte: 1 },
      override: { tempo: 1, defensive_line_height: 1, after_possession_won: 'hold_shape' },
    },
  ]
}

function legacyToTeamInstructions(legacy: TacticsSetup): TeamInstructions {
  const buildUpStyle = legacy.passing_style >= 3 ? 'short' : legacy.passing_style <= 1 ? 'direct' : 'balanced'
  const attackRoute = legacy.attack_width >= 3 ? 'both_wings' : legacy.attack_width <= 1 ? 'center' : 'mixed'
  const afterLost = legacy.pressing_intensity >= 3 ? 'counter_press' : 'balanced'
  const afterWon = legacy.attack_tempo >= 3 ? 'counter' : legacy.attack_tempo <= 1 ? 'hold_shape' : 'balanced'
  const marking = legacy.marking_strategy === 0 ? 'zonal' : legacy.marking_strategy >= 2 ? 'man' : 'mixed'
  return {
    legacy_team_sliders: legacy,
    in_possession: {
      build_up_style: buildUpStyle,
      chance_creation: 'balanced',
      attack_route: attackRoute,
      width: legacy.attack_width,
      tempo: legacy.attack_tempo,
      passing_risk: 2,
      crossing_frequency: legacy.crossing_strategy,
      dribble_frequency: 2,
      shooting_frequency: legacy.shooting_mentality,
    },
    transition: {
      after_possession_lost: afterLost,
      after_possession_won: afterWon,
      counter_directness: legacy.attack_tempo,
      reset_under_pressure: 2,
    },
    out_of_possession: {
      defensive_line_height: legacy.defensive_line_height,
      pressing_intensity: legacy.pressing_intensity,
      pressing_trigger: 'bad_touch',
      compactness: legacy.defensive_compactness,
      marking,
      tackling_aggression: legacy.tackling_aggression,
      offside_trap: legacy.offside_trap,
    },
    goalkeeper_distribution: {
      distribution_target: 'mixed',
      distribution_length: 'balanced',
      release_speed: 'balanced',
    },
    player_instructions: [],
    situational_rules: defaultSituationalRules(),
  }
}

const presets: Array<{ id: string; name: string; desc: string; icon: typeof Target; teamInstructions: TeamInstructions }> = [
  {
    id: 'balanced',
    name: '均衡默认',
    desc: '观察对手，线间距离保持稳定。',
    icon: Target,
    teamInstructions: legacyToTeamInstructions({ passing_style: 2, attack_width: 2, attack_tempo: 2, defensive_line_height: 2, crossing_strategy: 2, shooting_mentality: 2, playmaker_focus: 0, pressing_intensity: 2, defensive_compactness: 1, marking_strategy: 0, offside_trap: 0, tackling_aggression: 1 }),
  },
  {
    id: 'high_press',
    name: '高位逼抢',
    desc: '压上防线，前场夺回球权。',
    icon: Zap,
    teamInstructions: legacyToTeamInstructions({ passing_style: 2, attack_width: 2, attack_tempo: 3, defensive_line_height: 4, crossing_strategy: 2, shooting_mentality: 3, playmaker_focus: 0, pressing_intensity: 4, defensive_compactness: 1, marking_strategy: 2, offside_trap: 2, tackling_aggression: 3 }),
  },
  {
    id: 'possession',
    name: '控球推进',
    desc: '短传和组织核心，降低草率射门。',
    icon: Chart,
    teamInstructions: legacyToTeamInstructions({ passing_style: 4, attack_width: 2, attack_tempo: 1, defensive_line_height: 3, crossing_strategy: 1, shooting_mentality: 1, playmaker_focus: 2, pressing_intensity: 2, defensive_compactness: 2, marking_strategy: 1, offside_trap: 1, tackling_aggression: 1 }),
  },
  {
    id: 'counter',
    name: '极速反击',
    desc: '回收阵型后快速纵向推进。',
    icon: Fire,
    teamInstructions: legacyToTeamInstructions({ passing_style: 1, attack_width: 2, attack_tempo: 4, defensive_line_height: 1, crossing_strategy: 2, shooting_mentality: 2, playmaker_focus: 0, pressing_intensity: 1, defensive_compactness: 2, marking_strategy: 0, offside_trap: 0, tackling_aggression: 1 }),
  },
  {
    id: 'deep_defense',
    name: '深度防反',
    desc: '低位压缩空间，优先降低失球风险。',
    icon: Shield,
    teamInstructions: legacyToTeamInstructions({ passing_style: 1, attack_width: 1, attack_tempo: 2, defensive_line_height: 0, crossing_strategy: 2, shooting_mentality: 2, playmaker_focus: 0, pressing_intensity: 0, defensive_compactness: 2, marking_strategy: 0, offside_trap: 0, tackling_aggression: 0 }),
  },
  {
    id: 'wide_attack',
    name: '边路冲击',
    desc: '宽度和传中拉满，适合高点前锋。',
    icon: Flag,
    teamInstructions: legacyToTeamInstructions({ passing_style: 2, attack_width: 4, attack_tempo: 3, defensive_line_height: 2, crossing_strategy: 4, shooting_mentality: 3, playmaker_focus: 0, pressing_intensity: 2, defensive_compactness: 1, marking_strategy: 0, offside_trap: 0, tackling_aggression: 2 }),
  },
  {
    id: 'all_out',
    name: '全力进攻',
    desc: '高节奏高射门，适合必须进球的阶段。',
    icon: Sword,
    teamInstructions: legacyToTeamInstructions({ passing_style: 1, attack_width: 3, attack_tempo: 4, defensive_line_height: 3, crossing_strategy: 3, shooting_mentality: 4, playmaker_focus: 0, pressing_intensity: 3, defensive_compactness: 0, marking_strategy: 1, offside_trap: 1, tackling_aggression: 3 }),
  },
]

const tacticFields: Array<{
  key: TacticKey
  label: string
  left: string
  right: string
  max: number
  group: '进攻组织' | '防守结构'
}> = [
  { key: 'passing_style', label: '传球倾向', left: '直塞', right: '短传', max: 4, group: '进攻组织' },
  { key: 'attack_width', label: '进攻宽度', left: '收窄', right: '拉边', max: 4, group: '进攻组织' },
  { key: 'attack_tempo', label: '进攻节奏', left: '控速', right: '快打', max: 4, group: '进攻组织' },
  { key: 'crossing_strategy', label: '传中策略', left: '少传', right: '频繁', max: 4, group: '进攻组织' },
  { key: 'shooting_mentality', label: '射门心态', left: '耐心', right: '果断', max: 4, group: '进攻组织' },
  { key: 'playmaker_focus', label: '核心组织', left: '自由', right: '集中', max: 4, group: '进攻组织' },
  { key: 'defensive_line_height', label: '防线高度', left: '低位', right: '压上', max: 4, group: '防守结构' },
  { key: 'pressing_intensity', label: '逼抢强度', left: '回收', right: '压迫', max: 4, group: '防守结构' },
  { key: 'defensive_compactness', label: '防线收缩', left: '展开', right: '密集', max: 2, group: '防守结构' },
  { key: 'marking_strategy', label: '盯防策略', left: '区域', right: '盯人', max: 2, group: '防守结构' },
  { key: 'offside_trap', label: '越位陷阱', left: '保守', right: '主动', max: 2, group: '防守结构' },
  { key: 'tackling_aggression', label: '对抗强度', left: '克制', right: '凶狠', max: 3, group: '防守结构' },
]

const storageKey = 'lsl:tactics:v2'
const legacyStorageKey = 'lsl:tactics:v1'

const clamp = (value: number, max: number) => Math.min(max, Math.max(0, value))

const positionTone: Record<PlayerPosition, { bg: string; ink: string; ring: string; label: string; token: string; marker: string; fill: string }> = {
  GK: { bg: 'bg-[#E2B84B]', ink: 'text-[#2B1B08]', ring: 'border-[#7B5514]', label: '门将', token: '/tactics/token-gk-pixel-v6.png', marker: '/tactics/avatar-marker-gk-football-pixel-v1.png', fill: '#C49A32' },
  DF: { bg: 'bg-[#63A9E8]', ink: 'text-[#071626]', ring: 'border-[#164C7C]', label: '后卫', token: '/tactics/token-df-pixel-v6.png', marker: '/tactics/avatar-marker-df-football-pixel-v1.png', fill: '#5086AE' },
  MF: { bg: 'bg-[#72D0BB]', ink: 'text-[#06231C]', ring: 'border-[#1F7160]', label: '中场', token: '/tactics/token-mf-pixel-v6.png', marker: '/tactics/avatar-marker-mf-football-pixel-v1.png', fill: '#56A694' },
  FW: { bg: 'bg-[#E97762]', ink: 'text-[#2B0905]', ring: 'border-[#8E2E20]', label: '前锋', token: '/tactics/token-fw-pixel-v6.png', marker: '/tactics/avatar-marker-fw-football-pixel-v1.png', fill: '#BE5848' },
}

const formationRows: Record<FormationId, Array<{ position: PlayerPosition; count: number; y: number }>> = {
  F01: [{ position: 'GK', count: 1, y: 88 }, { position: 'DF', count: 2, y: 68 }, { position: 'MF', count: 3, y: 49 }, { position: 'FW', count: 2, y: 25 }],
  F02: [{ position: 'GK', count: 1, y: 88 }, { position: 'DF', count: 2, y: 68 }, { position: 'MF', count: 2, y: 50 }, { position: 'FW', count: 3, y: 24 }],
  F03: [{ position: 'GK', count: 1, y: 88 }, { position: 'DF', count: 1, y: 68 }, { position: 'MF', count: 3, y: 49 }, { position: 'FW', count: 3, y: 23 }],
  F04: [{ position: 'GK', count: 1, y: 88 }, { position: 'DF', count: 3, y: 68 }, { position: 'MF', count: 2, y: 48 }, { position: 'FW', count: 2, y: 25 }],
  F05: [{ position: 'GK', count: 1, y: 88 }, { position: 'DF', count: 1, y: 69 }, { position: 'MF', count: 2, y: 50 }, { position: 'FW', count: 4, y: 23 }],
  F06: [{ position: 'GK', count: 1, y: 88 }, { position: 'DF', count: 3, y: 67 }, { position: 'MF', count: 3, y: 47 }, { position: 'FW', count: 1, y: 24 }],
  F07: [{ position: 'GK', count: 1, y: 88 }, { position: 'DF', count: 2, y: 69 }, { position: 'MF', count: 4, y: 47 }, { position: 'FW', count: 1, y: 24 }],
  F08: [{ position: 'GK', count: 1, y: 88 }, { position: 'DF', count: 1, y: 70 }, { position: 'MF', count: 4, y: 49 }, { position: 'FW', count: 2, y: 24 }],
}

function getSlots(formationId: FormationId) {
  return formationRows[formationId].flatMap((row) => {
    const spacing = row.count > 1 ? 62 / (row.count - 1) : 0
    const start = row.count > 1 ? 19 : 50
    return Array.from({ length: row.count }, (_, index) => ({
      id: `${row.position}-${index}`,
      position: row.position,
      x: start + spacing * index,
      y: row.y + (row.position === 'MF' && row.count === 4 && index % 2 === 0 ? 3 : 0),
    }))
  })
}

function pickInitialLineup(players: TacticalPlayer[], formationId: FormationId) {
  const used = new Set<string>()
  return getSlots(formationId).map((slot) => {
    const candidates = players
      .filter((player) => player.position === slot.position && !used.has(player.id))
      .sort(sortPlayersForLineup)
    const fallback = players
      .filter((player) => !used.has(player.id))
      .sort(sortPlayersForLineup)
    const player = candidates[0] || fallback[0]
    if (player) used.add(player.id)
    return player?.id || null
  })
}

function sortPlayersForLineup(a: TacticalPlayer, b: TacticalPlayer) {
  return playerScore(b) - playerScore(a)
}

function playerScore(player: TacticalPlayer) {
  return player.ovr + (player.fitness || 75) * 0.12 + getMatchFormScore(player.match_form)
}

function getMatchFormScore(form?: string) {
  if (form === 'HOT') return 8
  if (form === 'GOOD') return 4
  if (form === 'LOW') return -6
  return 0
}

function formatForm(form?: string) {
  if (form === 'HOT') return '火热'
  if (form === 'GOOD') return '良好'
  if (form === 'LOW') return '低迷'
  return '普通'
}

function readStoredSetup() {
  const raw = localStorage.getItem(storageKey) || localStorage.getItem(legacyStorageKey)
  if (!raw) return null
  try {
    const parsed = JSON.parse(raw) as {
      formationId?: FormationId
      teamInstructions?: TeamInstructions
      tactics?: TacticsSetup
      preset?: string
      starterIds?: Array<string | null>
    }
    if (!parsed.teamInstructions && parsed.tactics) {
      parsed.teamInstructions = legacyToTeamInstructions(parsed.tactics)
    }
    if (parsed.teamInstructions) {
      parsed.teamInstructions = {
        ...parsed.teamInstructions,
        player_instructions: parsed.teamInstructions.player_instructions || [],
        situational_rules: parsed.teamInstructions.situational_rules || defaultSituationalRules(),
      }
    }
    return parsed
  } catch {
    localStorage.removeItem(storageKey)
    localStorage.removeItem(legacyStorageKey)
    return null
  }
}

function formatRate(numerator: number, denominator: number) {
  if (!denominator) return '0%'
  return `${Math.round((numerator / denominator) * 100)}%`
}

function getPositionStats(player: TacticalPlayer) {
  if (player.position === 'FW') {
    return [
      { label: '射正率', value: formatRate(player.shots_on_target, player.shots) },
      { label: '盘带成功率', value: formatRate(player.dribbles_succ, player.dribbles) },
      { label: '头球成功率', value: formatRate(player.headers_succ, player.headers) },
    ]
  }
  if (player.position === 'MF') {
    return [
      { label: '传球成功率', value: formatRate(player.passes_succ, player.passes) },
      { label: '传中成功率', value: formatRate(player.crosses_succ, player.crosses) },
      { label: '盘带成功率', value: formatRate(player.dribbles_succ, player.dribbles) },
    ]
  }
  if (player.position === 'DF') {
    return [
      { label: '抢断成功率', value: formatRate(player.tackles_succ, player.tackles) },
      { label: '拦截', value: player.interceptions },
      { label: '解围', value: player.clearances },
    ]
  }
  return [
    { label: '零封率', value: formatRate(player.clean_sheets, player.matches_played) },
    { label: '传球成功率', value: formatRate(player.passes_succ, player.passes) },
    { label: '解围', value: player.clearances },
  ]
}

const abilityOrder: Array<{ key: keyof PlayerAbility; label: string }> = [
  { key: 'sho', label: '射门' },
  { key: 'pas', label: '传球' },
  { key: 'dri', label: '盘带' },
  { key: 'spd', label: '速度' },
  { key: 'str', label: '力量' },
  { key: 'sta', label: '体能' },
  { key: 'acc', label: '爆发' },
  { key: 'hea', label: '头球' },
  { key: 'bal', label: '平衡' },
  { key: 'defe', label: '防守' },
  { key: 'tkl', label: '抢断' },
  { key: 'vis', label: '视野' },
  { key: 'cro', label: '传中' },
  { key: 'con', label: '控球' },
  { key: 'fin', label: '远射' },
  { key: 'com', label: '镇定' },
  { key: 'sav', label: '扑救' },
  { key: 'ref', label: '反应' },
  { key: 'pos', label: '站位' },
  { key: 'rus', label: '出击' },
  { key: 'dec', label: '球商' },
  { key: 'fk', label: '任意球' },
  { key: 'pk', label: '点球' },
]

function abilityTone(value: number) {
  if (value >= 16) return 'text-[#E8C84A]'
  if (value >= 11) return 'text-[#FFF8DE]'
  return 'text-[#786F5A]'
}

function FormationMiniShape({ formationId }: { formationId: FormationId }) {
  const rows = formationRows[formationId]
  return (
    <div className="relative aspect-[3/4] w-full">
      {rows.flatMap((row) =>
        Array.from({ length: row.count }, (_, i) => {
          const spacing = row.count > 1 ? 100 / (row.count + 1) : 50
          const left = row.count > 1 ? spacing * (i + 1) : 50
          return (
            <div
              key={`${row.position}-${i}`}
              className={clsx(
                'absolute h-1 w-1 rounded-full',
                row.position === 'GK' && 'bg-[#E2B84B]',
                row.position === 'DF' && 'bg-[#63A9E8]',
                row.position === 'MF' && 'bg-[#72D0BB]',
                row.position === 'FW' && 'bg-[#E97762]',
              )}
              style={{ left: `${left}%`, top: `${row.y}%`, transform: 'translate(-50%, -50%)' }}
            />
          )
        })
      )}
    </div>
  )
}

function TacticSlider({
  field,
  value,
  onChange,
}: {
  field: typeof tacticFields[number]
  value: number
  onChange: (key: TacticKey, value: number) => void
}) {
  return (
    <div className="border-2 border-[#3B3425] bg-[#16120B]/88 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm font-black text-[#EFE8CE]">{field.label}</span>
        <span className="stat-number text-sm text-[#D5B15E]">{value}/{field.max}</span>
      </div>
      <input
        type="range"
        min={0}
        max={field.max}
        step={1}
        value={value}
        onChange={(event) => onChange(field.key, Number(event.target.value))}
        className="w-full accent-[#D5B15E]"
      />
      <div className="mt-1 flex items-center justify-between text-[11px] font-bold text-[#786F5A]">
        <span>{field.left}</span>
        <span>{field.right}</span>
      </div>
    </div>
  )
}

const defaultPlayerInstruction = (playerId: string): PlayerInstruction => ({
  player_id: playerId,
  carry_ball: 2,
  passing_risk: 2,
  shooting_frequency: 2,
  crossing_frequency: 2,
  pressing_intensity: 2,
  hold_position: 2,
  forward_runs: 2,
})

function getPlayerInstruction(teamInstructions: TeamInstructions, playerId: string): PlayerInstruction {
  return (
    teamInstructions.player_instructions.find((instruction) => instruction.player_id === playerId) ||
    defaultPlayerInstruction(playerId)
  )
}

function updatePlayerInstruction(
  teamInstructions: TeamInstructions,
  playerId: string,
  patch: Partial<PlayerInstruction>,
): TeamInstructions {
  const existing = teamInstructions.player_instructions.find((instruction) => instruction.player_id === playerId)
  const next: PlayerInstruction = existing
    ? { ...existing, ...patch }
    : { ...defaultPlayerInstruction(playerId), ...patch }

  const isDefault =
    next.carry_ball === 2 &&
    next.passing_risk === 2 &&
    next.shooting_frequency === 2 &&
    next.crossing_frequency === 2 &&
    next.pressing_intensity === 2 &&
    next.hold_position === 2 &&
    next.forward_runs === 2

  let playerInstructions = teamInstructions.player_instructions
  if (isDefault) {
    playerInstructions = playerInstructions.filter((instruction) => instruction.player_id !== playerId)
  } else {
    playerInstructions = playerInstructions.map((instruction) =>
      instruction.player_id === playerId ? next : instruction,
    )
    if (!playerInstructions.some((instruction) => instruction.player_id === playerId)) {
      playerInstructions = [...playerInstructions, next]
    }
  }

  return { ...teamInstructions, player_instructions: playerInstructions }
}

const instructionFields: Array<{
  key: keyof Omit<PlayerInstruction, 'player_id'>
  label: string
  left: string
  right: string
}> = [
  { key: 'carry_ball', label: '持球推进', left: '少', right: '多' },
  { key: 'passing_risk', label: '传球冒险', left: '稳妥', right: '激进' },
  { key: 'shooting_frequency', label: '射门频率', left: '少', right: '多' },
  { key: 'crossing_frequency', label: '传中频率', left: '少', right: '多' },
  { key: 'pressing_intensity', label: '压迫强度', left: '保守', right: '积极' },
  { key: 'hold_position', label: '保持位置', left: '自由', right: '死守' },
  { key: 'forward_runs', label: '前插跑位', left: '少', right: '多' },
]

function PlayerPanel({
  player,
  slot,
  onClear,
  teamInstructions,
  onInstructionChange,
}: {
  player: TacticalPlayer
  slot?: StarterSlot
  onClear?: () => void
  teamInstructions: TeamInstructions
  onInstructionChange: (next: TeamInstructions) => void
}) {
  const navigate = useNavigate()
  const tone = positionTone[player.position]
  const instruction = getPlayerInstruction(teamInstructions, player.id)
  const fitnessColor = player.fitness >= 80 ? 'bg-[#7CB342]' : player.fitness >= 50 ? 'bg-[#E6B800]' : 'bg-[#D75A4A]'
  const formColor = player.match_form === 'HOT' ? 'text-[#E8C84A]' : player.match_form === 'GOOD' ? 'text-[#7CB342]' : player.match_form === 'LOW' ? 'text-[#D75A4A]' : 'text-[#A99E83]'

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-3">
        <div className={clsx('relative h-16 w-16 shrink-0 overflow-hidden rounded-full border-4', tone.ring)}>
          {player.avatar_url ? (
            <img
              src={`/${player.avatar_url}`}
              alt={player.name}
              className="h-full w-full object-cover object-top [image-rendering:pixelated]"
            />
          ) : (
            <img
              src={tone.token}
              alt=""
              className="absolute inset-0 h-full w-full object-contain [image-rendering:pixelated]"
            />
          )}
        </div>
        <div className="min-w-0 flex-1">
          <button
            type="button"
            onClick={() => navigate(`/players/${player.id}`)}
            className="block text-left transition-opacity hover:opacity-85"
          >
            <h3 className="truncate text-base font-black text-[#FFF8DE]">{player.name}</h3>
          </button>
          <p className="mt-1 text-sm font-black text-[#D5B15E]">{player.age}岁 · {tone.label}</p>
          {slot && (
            <p className="mt-0.5 text-[11px] font-black text-[#9ECF45]">
              当前首发 · 位置 {slot.position}-{slot.id.split('-')[1] ? Number(slot.id.split('-')[1]) + 1 : 1}
            </p>
          )}
        </div>
        {onClear && (
          <button
            type="button"
            onClick={onClear}
            className="grid h-7 w-7 shrink-0 place-items-center border-2 border-[#3B3425] bg-[#0D0B07] text-[#786F5A] hover:text-[#FFF8DE]"
          >
            <Cancel className="h-3.5 w-3.5" />
          </button>
        )}
      </div>

      <div className="space-y-2 border-2 border-[#3B3425] bg-[#0D0B07] p-3">
        <div className="flex items-center justify-between">
          <span className="text-xs font-black text-[#786F5A]">体能</span>
          <span className="text-xs font-black text-[#FFF8DE]">{player.fitness}%</span>
        </div>
        <div className="h-2 border border-[#3B3425] bg-[#1A1610]">
          <div className={clsx('h-full', fitnessColor)} style={{ width: `${player.fitness}%` }} />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs font-black text-[#786F5A]">状态</span>
          <span className={clsx('text-xs font-black', formColor)}>{formatForm(player.match_form)}</span>
        </div>
      </div>

      <div className="border-2 border-[#3B3425] bg-[#0D0B07] p-3">
        <p className="mb-2 text-[10px] font-black text-[#786F5A]">赛季数据</p>
        <div className="grid grid-cols-3 gap-y-1.5 text-xs">
          <span className="font-black text-[#786F5A]">出场 <span className="text-[#FFF8DE]">{player.matches_played}</span></span>
          <span className="font-black text-[#786F5A]">进球 <span className="text-[#FFF8DE]">{player.goals}</span></span>
          <span className="font-black text-[#786F5A]">助攻 <span className="text-[#FFF8DE]">{player.assists}</span></span>
          <span className="font-black text-[#786F5A]">场均 <span className="text-[#D5B15E]">{player.average_rating.toFixed(1)}</span></span>
          <span className="font-black text-[#786F5A]">黄牌 <span className="text-yellow-400">{player.yellow_cards}</span></span>
          <span className="font-black text-[#786F5A]">红牌 <span className="text-red-400">{player.red_cards}</span></span>
          {getPositionStats(player).map((stat) => (
            <span key={stat.label} className="font-black text-[#786F5A]">{stat.label} <span className="text-[#FFF8DE]">{stat.value}</span></span>
          ))}
        </div>
      </div>

      <div className="border-2 border-[#3B3425] bg-[#0D0B07] p-3">
        <p className="mb-2 text-[10px] font-black text-[#786F5A]">能力值</p>
        <div className="grid grid-cols-3 gap-1.5">
          {abilityOrder.map((ability) => {
            const value = player.abilities[ability.key]
            return (
              <div key={ability.key} className="border border-[#3B3425] bg-[#15110A] py-1 text-center">
                <p className="text-[9px] font-black text-[#786F5A]">{ability.label}</p>
                <p className={clsx('font-["Press_Start_2P"] text-[11px] font-black', abilityTone(value))}>{value}</p>
              </div>
            )
          })}
        </div>
      </div>

      <div className="border-2 border-[#3B3425] bg-[#0D0B07] p-3">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-[10px] font-black text-[#786F5A]">个人战术指令</p>
          <button
            type="button"
            onClick={() => onInstructionChange(updatePlayerInstruction(teamInstructions, player.id, defaultPlayerInstruction(player.id)))}
            className="text-[9px] font-black text-[#D5B15E] hover:text-[#FFF8DE]"
          >
            重置默认
          </button>
        </div>
        <div className="space-y-3">
          {instructionFields.map((field) => (
            <div key={field.key} className="space-y-1">
              <div className="flex items-center justify-between text-[10px] font-black">
                <span className="text-[#FFF8DE]">{field.label}</span>
                <span className='font-["Press_Start_2P"] text-[#D5B15E]'>{instruction[field.key]}</span>
              </div>
              <input
                type="range"
                min={0}
                max={4}
                step={1}
                value={instruction[field.key]}
                onChange={(event) =>
                  onInstructionChange(
                    updatePlayerInstruction(teamInstructions, player.id, { [field.key]: Number(event.target.value) }),
                  )
                }
                className="h-1.5 w-full cursor-pointer appearance-none rounded-none border border-[#3B3425] bg-[#1A1610] accent-[#D5B15E]"
              />
              <div className="flex justify-between text-[9px] font-black text-[#786F5A]">
                <span>{field.left}</span>
                <span>{field.right}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function FormationSelect({
  value,
  onChange,
}: {
  value: FormationId
  onChange: (id: FormationId) => void
}) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const current = formations.find((f) => f.id === value)!

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 border-2 border-[#3B3425] bg-[#15110A] px-3 py-2 text-left transition-colors hover:border-[#D5B15E]/55"
      >
        <div className="h-10 w-8 shrink-0">
          <FormationMiniShape formationId={current.id} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-black text-[#FFF8DE]">{current.shape}</p>
        </div>
        <ChevronDown className={clsx('h-4 w-4 shrink-0 text-[#786F5A] transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 border-2 border-[#3B3425] bg-[#15110A] p-2 shadow-pixel">
          <div className="grid grid-cols-2 gap-2">
            {formations.map((formation) => (
              <button
                key={formation.id}
                type="button"
                onClick={() => {
                  onChange(formation.id)
                  setOpen(false)
                }}
                className={clsx(
                  'flex flex-col items-center gap-1 border-2 p-2 text-center transition-all',
                  value === formation.id
                    ? 'border-[#D5B15E] bg-[#2A1E0E]'
                    : 'border-[#3B3425] bg-[#0D0B07] hover:border-[#D5B15E]/55',
                )}
              >
                <div className="h-8 w-full">
                  <FormationMiniShape formationId={formation.id} />
                </div>
                <p className="text-[11px] font-black text-[#FFF8DE]">{formation.shape}</p>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function PresetSelect({
  value,
  onChange,
}: {
  value: string
  onChange: (id: string) => void
}) {
  const [open, setOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement>(null)
  const current = presets.find((p) => p.id === value)
  const CurrentIcon = current?.icon || Target

  useEffect(() => {
    function onClick(event: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(event.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 border-2 border-[#3B3425] bg-[#15110A] px-3 py-2 text-left transition-colors hover:border-[#D5B15E]/55"
      >
        <div className="grid h-8 w-8 shrink-0 place-items-center border border-[#3B3425] bg-[#0D0B07]">
          <CurrentIcon className="h-4 w-4 text-[#D5B15E]" />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs font-black text-[#FFF8DE]">{current?.name || '自定义'}</p>
          <p className="text-[10px] font-bold text-[#786F5A]">{current?.desc || '手动调整'}</p>
        </div>
        <ChevronDown className={clsx('h-4 w-4 shrink-0 text-[#786F5A] transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute left-0 right-0 top-full z-30 mt-1 border-2 border-[#3B3425] bg-[#15110A] p-2 shadow-pixel">
          <div className="space-y-1">
            {presets.map((preset) => {
              const Icon = preset.icon
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => {
                    onChange(preset.id)
                    setOpen(false)
                  }}
                  className={clsx(
                    'flex w-full items-center gap-2 border-2 p-2 text-left transition-all',
                    value === preset.id
                      ? 'border-[#D5B15E] bg-[#2A1E0E]'
                      : 'border-[#3B3425] bg-[#0D0B07] hover:border-[#D5B15E]/55',
                  )}
                >
                  <div className="grid h-7 w-7 shrink-0 place-items-center border border-[#3B3425] bg-[#15110A]">
                    <Icon className="h-3.5 w-3.5 text-[#D5B15E]" />
                  </div>
                  <div className="min-w-0">
                    <p className="text-[11px] font-black text-[#FFF8DE]">{preset.name}</p>
                    <p className="text-[10px] font-bold text-[#786F5A]">{preset.desc}</p>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}

function BenchPlayerRow({
  player,
  selected,
  onClick,
  onDragStart,
}: {
  player: TacticalPlayer
  selected: boolean
  onClick: () => void
  onDragStart: (event: React.DragEvent<HTMLButtonElement>) => void
}) {
  const tone = positionTone[player.position]
  const fitnessColor = player.fitness >= 80 ? 'bg-[#7CB342]' : player.fitness >= 50 ? 'bg-[#E6B800]' : 'bg-[#D75A4A]'

  return (
    <button
      type="button"
      draggable
      onClick={onClick}
      onDragStart={onDragStart}
      className={clsx(
        'flex w-full items-center gap-3 border-2 p-2 text-left transition-all',
        selected
          ? 'border-[#D5B15E] bg-[#2A1E0E]'
          : 'border-[#3B3425] bg-[#15110A] hover:border-[#D5B15E]/55',
      )}
    >
      <div className={clsx('relative h-10 w-10 shrink-0 overflow-hidden rounded-full border-2', tone.ring)}>
        {player.avatar_url ? (
          <img src={`/${player.avatar_url}`} alt={player.name} className="h-full w-full object-cover object-top [image-rendering:pixelated]" />
        ) : (
          <img src={tone.token} alt="" className="absolute inset-0 h-full w-full object-contain [image-rendering:pixelated]" />
        )}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-black text-[#FFF8DE]">{player.name}</p>
        <p className="text-[10px] font-bold text-[#786F5A]">{tone.label} · OVR {player.ovr}</p>
        <div className="mt-1.5 h-1 border border-[#3B3425] bg-[#1A1610]">
          <div className={clsx('h-full', fitnessColor)} style={{ width: `${player.fitness}%` }} />
        </div>
      </div>
    </button>
  )
}

function TacticsDesignPanel({
  tactics,
  activePreset,
  onTacticChange,
  onPreset,
}: {
  tactics: TacticsSetup
  activePreset: string
  onTacticChange: (key: TacticKey, value: number) => void
  onPreset: (id: string) => void
}) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Settings2 className="h-4 w-4 text-[#D5B15E]" />
          <h2 className="font-black text-[#FFF8DE]">战术控制台</h2>
        </div>
        {activePreset === 'custom' && (
          <button
            type="button"
            onClick={() => onPreset('balanced')}
            className="text-[10px] font-black text-[#D5B15E] hover:text-[#FFF8DE]"
          >
            重置
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        {(['进攻组织', '防守结构'] as const).map((group) => (
          <div key={group} className="border-2 border-[#3B3425] bg-[#0D0B07] p-3 shadow-pixel">
            <div className="mb-2 flex items-center gap-2">
              {group === '进攻组织' ? <Sword className="h-3.5 w-3.5 text-[#E97762]" /> : <Shield className="h-3.5 w-3.5 text-[#63A9E8]" />}
              <h3 className="text-xs font-black text-[#EFE8CE]">{group}</h3>
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              {tacticFields.filter((field) => field.group === group).map((field) => (
                <TacticSlider key={field.key} field={field} value={tactics[field.key]} onChange={onTacticChange} />
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function PhaseSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: { value: T; label: string }[]
  onChange: (value: T) => void
}) {
  return (
    <div className="border-2 border-[#3B3425] bg-[#16120B]/88 p-3">
      <label className="mb-2 block text-sm font-black text-[#EFE8CE]">{label}</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value as T)}
        className="w-full border-2 border-[#3B3425] bg-[#0D0B07] px-2 py-1.5 text-xs font-black text-[#FFF8DE] focus:border-[#D5B15E] focus:outline-none"
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-[#0D0B07]">
            {opt.label}
          </option>
        ))}
      </select>
    </div>
  )
}

function PhaseSlider({
  label,
  value,
  max,
  onChange,
}: {
  label: string
  value: number
  max: number
  onChange: (value: number) => void
}) {
  return (
    <div className="border-2 border-[#3B3425] bg-[#16120B]/88 p-3">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm font-black text-[#EFE8CE]">{label}</span>
        <span className="stat-number text-sm text-[#D5B15E]">{value}/{max}</span>
      </div>
      <input
        type="range"
        min={0}
        max={max}
        step={1}
        value={value}
        onChange={(event) => onChange(Number(event.target.value))}
        className="w-full accent-[#D5B15E]"
      />
    </div>
  )
}

function PhaseTacticsPanel({
  teamInstructions,
  onChange,
}: {
  teamInstructions: TeamInstructions
  onChange: (next: TeamInstructions) => void
}) {
  const updateInPossession = (patch: Partial<InPossessionInstructions>) =>
    onChange({ ...teamInstructions, in_possession: { ...teamInstructions.in_possession, ...patch } })
  const updateTransition = (patch: Partial<TransitionInstructions>) =>
    onChange({ ...teamInstructions, transition: { ...teamInstructions.transition, ...patch } })
  const updateOutOfPossession = (patch: Partial<OutOfPossessionInstructions>) =>
    onChange({ ...teamInstructions, out_of_possession: { ...teamInstructions.out_of_possession, ...patch } })
  const updateGk = (patch: Partial<GoalkeeperDistributionInstructions>) =>
    onChange({ ...teamInstructions, goalkeeper_distribution: { ...teamInstructions.goalkeeper_distribution, ...patch } })

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Settings2 className="h-4 w-4 text-[#D5B15E]" />
        <h2 className="font-black text-[#FFF8DE]">阶段战术</h2>
      </div>

      <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
        <div className="border-2 border-[#3B3425] bg-[#0D0B07] p-3 shadow-pixel">
          <div className="mb-2 flex items-center gap-2">
            <Sword className="h-3.5 w-3.5 text-[#E97762]" />
            <h3 className="text-xs font-black text-[#EFE8CE]">持球进攻</h3>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <PhaseSelect
              label="进攻路线"
              value={teamInstructions.in_possession.attack_route}
              options={[
                { value: 'left', label: '左路' },
                { value: 'center', label: '中路' },
                { value: 'right', label: '右路' },
                { value: 'both_wings', label: '两翼' },
                { value: 'mixed', label: '混合' },
              ]}
              onChange={(v) => updateInPossession({ attack_route: v })}
            />
            <PhaseSelect
              label="推进方式"
              value={teamInstructions.in_possession.build_up_style}
              options={[
                { value: 'short', label: '短传推进' },
                { value: 'balanced', label: '均衡' },
                { value: 'direct', label: '直接推进' },
                { value: 'long_ball', label: '长传冲吊' },
              ]}
              onChange={(v) => updateInPossession({ build_up_style: v })}
            />
            <PhaseSlider label="传球风险" value={teamInstructions.in_possession.passing_risk} max={4} onChange={(v) => updateInPossession({ passing_risk: v })} />
            <PhaseSlider label="传中频率" value={teamInstructions.in_possession.crossing_frequency} max={4} onChange={(v) => updateInPossession({ crossing_frequency: v })} />
            <PhaseSlider label="盘带频率" value={teamInstructions.in_possession.dribble_frequency} max={4} onChange={(v) => updateInPossession({ dribble_frequency: v })} />
            <PhaseSlider label="射门频率" value={teamInstructions.in_possession.shooting_frequency} max={4} onChange={(v) => updateInPossession({ shooting_frequency: v })} />
          </div>
        </div>

        <div className="border-2 border-[#3B3425] bg-[#0D0B07] p-3 shadow-pixel">
          <div className="mb-2 flex items-center gap-2">
            <Zap className="h-3.5 w-3.5 text-[#D7A94A]" />
            <h3 className="text-xs font-black text-[#EFE8CE]">转换阶段</h3>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <PhaseSelect
              label="丢球后"
              value={teamInstructions.transition.after_possession_lost}
              options={[
                { value: 'counter_press', label: '立即反抢' },
                { value: 'balanced', label: '均衡' },
                { value: 'regroup', label: '回防落位' },
              ]}
              onChange={(v) => updateTransition({ after_possession_lost: v })}
            />
            <PhaseSelect
              label="得球后"
              value={teamInstructions.transition.after_possession_won}
              options={[
                { value: 'counter', label: '快速反击' },
                { value: 'balanced', label: '均衡' },
                { value: 'hold_shape', label: '稳住阵型' },
              ]}
              onChange={(v) => updateTransition({ after_possession_won: v })}
            />
            <PhaseSlider label="反击直接性" value={teamInstructions.transition.counter_directness} max={4} onChange={(v) => updateTransition({ counter_directness: v })} />
          </div>
        </div>

        <div className="border-2 border-[#3B3425] bg-[#0D0B07] p-3 shadow-pixel">
          <div className="mb-2 flex items-center gap-2">
            <Shield className="h-3.5 w-3.5 text-[#63A9E8]" />
            <h3 className="text-xs font-black text-[#EFE8CE]">无球防守</h3>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <PhaseSelect
              label="逼抢触发"
              value={teamInstructions.out_of_possession.pressing_trigger}
              options={[
                { value: 'passive', label: '被动' },
                { value: 'bad_touch', label: '停球失误' },
                { value: 'wide_trap', label: '边路逼抢' },
                { value: 'center_trap', label: '中路合围' },
                { value: 'always', label: '持续高压' },
              ]}
              onChange={(v) => updateOutOfPossession({ pressing_trigger: v })}
            />
            <PhaseSelect
              label="盯防方式"
              value={teamInstructions.out_of_possession.marking}
              options={[
                { value: 'zonal', label: '区域防守' },
                { value: 'mixed', label: '混合' },
                { value: 'man', label: '人盯人' },
              ]}
              onChange={(v) => updateOutOfPossession({ marking: v })}
            />
            <PhaseSlider label="防线紧凑度" value={teamInstructions.out_of_possession.compactness} max={4} onChange={(v) => updateOutOfPossession({ compactness: v })} />
          </div>
        </div>

        <div className="border-2 border-[#3B3425] bg-[#0D0B07] p-3 shadow-pixel">
          <div className="mb-2 flex items-center gap-2">
            <Target className="h-3.5 w-3.5 text-[#E2B84B]" />
            <h3 className="text-xs font-black text-[#EFE8CE]">门将出球</h3>
          </div>
          <div className="grid gap-2 sm:grid-cols-2">
            <PhaseSelect
              label="出球目标"
              value={teamInstructions.goalkeeper_distribution.distribution_target}
              options={[
                { value: 'center_backs', label: '中后卫' },
                { value: 'fullbacks', label: '边后卫' },
                { value: 'midfield', label: '中场' },
                { value: 'target_forward', label: '支点前锋' },
                { value: 'mixed', label: '混合' },
              ]}
              onChange={(v) => updateGk({ distribution_target: v })}
            />
            <PhaseSelect
              label="出球距离"
              value={teamInstructions.goalkeeper_distribution.distribution_length}
              options={[
                { value: 'short', label: '短传' },
                { value: 'balanced', label: '均衡' },
                { value: 'long', label: '长传' },
              ]}
              onChange={(v) => updateGk({ distribution_length: v })}
            />
            <PhaseSelect
              label="出球速度"
              value={teamInstructions.goalkeeper_distribution.release_speed}
              options={[
                { value: 'slow', label: '慢速落位' },
                { value: 'balanced', label: '均衡' },
                { value: 'quick', label: '快速发动' },
              ]}
              onChange={(v) => updateGk({ release_speed: v })}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

function newRuleId() {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }
  return `rule-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`
}

const situationalConditionFields: Array<{
  key: keyof SituationalRuleCondition
  label: string
  min: number
  max: number
}> = [
  { key: 'minute_gte', label: '时间≥', min: 0, max: 120 },
  { key: 'minute_lt', label: '时间<', min: 0, max: 120 },
  { key: 'goal_diff_lte', label: '比分差≤', min: -20, max: 20 },
  { key: 'goal_diff_gte', label: '比分差≥', min: -20, max: 20 },
  { key: 'team_stamina_avg_lte', label: '平均体能≤', min: 0, max: 100 },
]

const situationalOverrideFields: Array<{
  key: keyof SituationalRuleOverride
  label: string
  type: 'slider' | 'select'
  max?: number
  options?: { value: string; label: string }[]
}> = [
  { key: 'tempo', label: '节奏', type: 'slider', max: 4 },
  { key: 'width', label: '宽度', type: 'slider', max: 4 },
  { key: 'passing_risk', label: '传球冒险', type: 'slider', max: 4 },
  { key: 'crossing_frequency', label: '传中频率', type: 'slider', max: 4 },
  { key: 'shooting_frequency', label: '射门频率', type: 'slider', max: 4 },
  { key: 'defensive_line_height', label: '防线高度', type: 'slider', max: 4 },
  { key: 'pressing_intensity', label: '逼抢强度', type: 'slider', max: 4 },
  {
    key: 'after_possession_won',
    label: '得球后',
    type: 'select',
    options: [
      { value: 'counter', label: '快速反击' },
      { value: 'balanced', label: '均衡' },
      { value: 'hold_shape', label: '稳住阵型' },
    ],
  },
  {
    key: 'after_possession_lost',
    label: '丢球后',
    type: 'select',
    options: [
      { value: 'counter_press', label: '立即反抢' },
      { value: 'balanced', label: '均衡' },
      { value: 'regroup', label: '回防落位' },
    ],
  },
  {
    key: 'build_up_style',
    label: '推进方式',
    type: 'select',
    options: [
      { value: 'short', label: '短传推进' },
      { value: 'balanced', label: '均衡' },
      { value: 'direct', label: '直接推进' },
      { value: 'long_ball', label: '长传冲吊' },
    ],
  },
  {
    key: 'chance_creation',
    label: '创造机会',
    type: 'select',
    options: [
      { value: 'patient', label: '耐心组织' },
      { value: 'balanced', label: '均衡' },
      { value: 'early_shot', label: '尽早射门' },
      { value: 'work_into_box', label: '渗透禁区' },
    ],
  },
]

function SituationalRulesPanel({
  teamInstructions,
  onChange,
}: {
  teamInstructions: TeamInstructions
  onChange: (next: TeamInstructions) => void
}) {
  const rules = teamInstructions.situational_rules || []

  const updateRules = (next: SituationalRule[]) => {
    onChange({ ...teamInstructions, situational_rules: next.slice(0, 10) })
  }

  const updateRule = (index: number, patch: Partial<SituationalRule>) => {
    updateRules(rules.map((rule, i) => (i === index ? { ...rule, ...patch } : rule)))
  }

  const updateCondition = (index: number, patch: Partial<SituationalRuleCondition>) => {
    updateRule(index, { condition: { ...rules[index].condition, ...patch } })
  }

  const removeConditionField = (index: number, key: keyof SituationalRuleCondition) => {
    const next = { ...rules[index].condition }
    delete next[key]
    updateRule(index, { condition: next })
  }

  const updateOverride = (index: number, patch: SituationalRuleOverride) => {
    updateRule(index, { override: { ...rules[index].override, ...patch } })
  }

  const removeOverride = (index: number, key: keyof SituationalRuleOverride) => {
    const next = { ...rules[index].override }
    delete next[key]
    updateRule(index, { override: next })
  }

  const addRule = () => {
    updateRules([
      ...rules,
      {
        id: newRuleId(),
        name: '新规则',
        enabled: true,
        condition: {},
        override: {},
      },
    ])
  }

  const conditionDefaults: Record<keyof SituationalRuleCondition, number> = {
    minute_gte: 40,
    minute_lt: 90,
    goal_diff_lte: -1,
    goal_diff_gte: 1,
    team_stamina_avg_lte: 50,
  }

  const addCondition = (index: number, key: keyof SituationalRuleCondition) => {
    updateCondition(index, { [key]: conditionDefaults[key] } as Partial<SituationalRuleCondition>)
  }

  const addOverride = (index: number, key: keyof SituationalRuleOverride) => {
    const field = situationalOverrideFields.find((f) => f.key === key)
    if (!field) return
    const value = field.type === 'slider' ? 2 : field.options![0].value
    updateOverride(index, { [key]: value } as SituationalRuleOverride)
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Flag className="h-4 w-4 text-[#D5B15E]" />
          <h2 className="font-black text-[#FFF8DE]">情境规则</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-[#786F5A]">{rules.length}/10</span>
          <button
            type="button"
            onClick={addRule}
            disabled={rules.length >= 10}
            className="border-2 border-[#3B3425] bg-[#0D0B07] px-2 py-1 text-[10px] font-black text-[#D5B15E] hover:border-[#D5B15E] disabled:opacity-40"
          >
            + 新增规则
          </button>
        </div>
      </div>

      {rules.length === 0 && (
        <div className="border-2 border-dashed border-[#3B3425] p-4 text-center text-xs font-bold text-[#786F5A]">
          暂无情境规则。点击右上角添加，或在预设中恢复默认规则。
        </div>
      )}

      <div className="space-y-3">
        {rules.map((rule, index) => {
          const conditionKeys = Object.keys(rule.condition) as Array<keyof SituationalRuleCondition>
          const overrideKeys = Object.keys(rule.override) as Array<keyof SituationalRuleOverride>

          return (
            <div
              key={rule.id}
              className="border-2 border-[#3B3425] bg-[#0D0B07] p-3 shadow-pixel"
            >
              <div className="mb-3 flex items-center gap-2">
                <input
                  type="text"
                  value={rule.name}
                  onChange={(event) => updateRule(index, { name: event.target.value })}
                  className="min-w-0 flex-1 border-2 border-[#3B3425] bg-[#15110A] px-2 py-1 text-xs font-black text-[#FFF8DE] focus:border-[#D5B15E] focus:outline-none"
                />
                <label className="flex items-center gap-1.5 text-[10px] font-black text-[#EFE8CE]">
                  <input
                    type="checkbox"
                    checked={rule.enabled}
                    onChange={(event) => updateRule(index, { enabled: event.target.checked })}
                    className="accent-[#D5B15E]"
                  />
                  启用
                </label>
                <button
                  type="button"
                  title="删除规则"
                  onClick={() => updateRules(rules.filter((_, i) => i !== index))}
                  className="grid h-6 w-6 place-items-center border-2 border-[#3B3425] bg-[#15110A] text-[#786F5A] hover:text-[#E97762]"
                >
                  <Delete className="h-3.5 w-3.5" />
                </button>
              </div>

              {/* Sentence editor: conditions */}
              <div className="mb-3 flex flex-wrap items-center gap-2 text-xs leading-7">
                <span className="font-black text-[#786F5A]">当</span>
                {conditionKeys.length === 0 && (
                  <span className="font-bold text-[#786F5A]">（无条件，始终触发）</span>
                )}
                {conditionKeys.map((key, ci) => {
                  const field = situationalConditionFields.find((f) => f.key === key)!
                  return (
                    <div key={key} className="inline-flex items-center gap-1">
                      {ci > 0 && <span className="font-black text-[#D5B15E]">并且</span>}
                      <span className="font-black text-[#EFE8CE]">{field.label}</span>
                      <input
                        type="number"
                        min={field.min}
                        max={field.max}
                        value={rule.condition[key]}
                        onChange={(event) => {
                          const num = Math.min(field.max, Math.max(field.min, Number(event.target.value)))
                          updateCondition(index, { [key]: num } as Partial<SituationalRuleCondition>)
                        }}
                        className="w-14 border-2 border-[#3B3425] bg-[#15110A] px-1 py-0.5 text-center font-['Press_Start_2P'] text-[10px] font-black text-[#D5B15E] focus:border-[#D5B15E] focus:outline-none"
                      />
                      <button
                        type="button"
                        title="移除条件"
                        onClick={() => removeConditionField(index, key)}
                        className="grid h-5 w-5 place-items-center text-[#786F5A] hover:text-[#E97762]"
                      >
                        <Delete className="h-3 w-3" />
                      </button>
                    </div>
                  )
                })}
                <select
                  value=""
                  onChange={(event) => {
                    if (event.target.value) {
                      addCondition(index, event.target.value as keyof SituationalRuleCondition)
                      event.target.value = ''
                    }
                  }}
                  className="border-2 border-[#3B3425] bg-[#15110A] px-2 py-0.5 text-[10px] font-black text-[#D5B15E]"
                >
                  <option value="">+ 并且…</option>
                  {situationalConditionFields
                    .filter((field) => rule.condition[field.key] === undefined)
                    .map((field) => (
                      <option key={field.key} value={field.key}>
                        {field.label}
                      </option>
                    ))}
                </select>
              </div>

              {/* Sentence editor: overrides */}
              <div className="flex flex-wrap items-center gap-2 text-xs leading-7">
                <span className="font-black text-[#786F5A]">时，将</span>
                {overrideKeys.length === 0 && (
                  <span className="font-bold text-[#786F5A]">（无覆盖）</span>
                )}
                {overrideKeys.map((key) => {
                  const field = situationalOverrideFields.find((f) => f.key === key)!
                  const value = rule.override[key] as number | string
                  return (
                    <div key={key} className="inline-flex items-center gap-1.5">
                      <span className="font-black text-[#EFE8CE]">{field.label}</span>
                      <span className="font-black text-[#786F5A]">调整为</span>
                      {field.type === 'slider' ? (
                        <>
                          <input
                            type="range"
                            min={0}
                            max={field.max}
                            step={1}
                            value={value as number}
                            onChange={(event) =>
                              updateOverride(index, { [key]: Number(event.target.value) } as SituationalRuleOverride)
                            }
                            className="w-20 accent-[#D5B15E]"
                          />
                          <span className='font-["Press_Start_2P"] w-3 text-center text-[10px] font-black text-[#D5B15E]'>
                            {value}
                          </span>
                        </>
                      ) : (
                        <select
                          value={value as string}
                          onChange={(event) =>
                            updateOverride(index, { [key]: event.target.value } as SituationalRuleOverride)
                          }
                          className="border-2 border-[#3B3425] bg-[#15110A] px-1 py-0.5 text-[10px] font-black text-[#FFF8DE]"
                        >
                          {field.options!.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                      )}
                      <button
                        type="button"
                        title="移除覆盖"
                        onClick={() => removeOverride(index, key)}
                        className="grid h-5 w-5 place-items-center text-[#786F5A] hover:text-[#E97762]"
                      >
                        <Delete className="h-3 w-3" />
                      </button>
                    </div>
                  )
                })}
                <select
                  value=""
                  onChange={(event) => {
                    if (event.target.value) {
                      addOverride(index, event.target.value as keyof SituationalRuleOverride)
                      event.target.value = ''
                    }
                  }}
                  className="border-2 border-[#3B3425] bg-[#15110A] px-2 py-0.5 text-[10px] font-black text-[#D5B15E]"
                >
                  <option value="">+ 将…调整为…</option>
                  {situationalOverrideFields
                    .filter((field) => rule.override[field.key] === undefined)
                    .map((field) => (
                      <option key={field.key} value={field.key}>
                        {field.label}
                      </option>
                    ))}
                </select>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function BenchPanel({
  bench,
  selectedPlayerId,
  onPlayerClick,
  onDragStart,
}: {
  bench: TacticalPlayer[]
  selectedPlayerId: string | null
  onPlayerClick: (player: TacticalPlayer, index: number) => void
  onDragStart: (event: React.DragEvent<HTMLButtonElement>, player: TacticalPlayer, index: number) => void
}) {
  return (
    <div className="flex h-full min-h-0 flex-col border-2 border-[#3B3425] bg-[#15110A] p-3 shadow-pixel">
      <div className="mb-3 flex items-center gap-2">
        <Users className="h-4 w-4 text-[#D5B15E]" />
        <h2 className="font-black text-[#FFF8DE]">替补席</h2>
        <span className="ml-auto text-[10px] font-bold text-[#786F5A]">{bench.length}人</span>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto pr-1">
        {bench.length ? bench.map((player, index) => (
          <BenchPlayerRow
            key={player.id}
            player={player}
            selected={selectedPlayerId === player.id}
            onClick={() => onPlayerClick(player, index)}
            onDragStart={(event) => onDragStart(event, player, index)}
          />
        )) : (
          <div className="flex h-24 items-center justify-center border-2 border-dashed border-[#3B3425] text-xs font-bold text-[#786F5A]">
            暂无可用替补
          </div>
        )}
      </div>
    </div>
  )
}

function PlayerDetailPanel({
  player,
  slot,
  onClear,
  teamInstructions,
  onInstructionChange,
}: {
  player?: TacticalPlayer
  slot?: StarterSlot
  onClear: () => void
  teamInstructions: TeamInstructions
  onInstructionChange: (next: TeamInstructions) => void
}) {
  return (
    <div className="flex h-full min-h-0 flex-col border-2 border-[#3B3425] bg-[#15110A] p-3 shadow-pixel">
      <div className="mb-3 flex items-center gap-2">
        <Target className="h-4 w-4 text-[#D5B15E]" />
        <h2 className="font-black text-[#FFF8DE]">球员详情</h2>
      </div>
      <div className="flex-1 overflow-y-auto pr-1">
        {player ? (
          <PlayerPanel
            player={player}
            slot={slot}
            onClear={onClear}
            teamInstructions={teamInstructions}
            onInstructionChange={onInstructionChange}
          />
        ) : (
          <div className="flex h-48 flex-col items-center justify-center gap-3 border-2 border-dashed border-[#3B3425] p-4 text-center">
            <Target className="h-8 w-8 text-[#3B3425]" />
            <p className="text-sm font-bold text-[#786F5A]">点击球场或替补球员查看详情</p>
          </div>
        )}
      </div>
    </div>
  )
}

function SaveButton({ saved, onSave }: { saved: boolean; onSave: () => void | Promise<void> }) {
  return (
    <button
      onClick={onSave}
      className={clsx(
        'inline-flex items-center gap-1.5 border-2 px-3 py-2 text-xs font-black shadow-pixel-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:brightness-110',
        saved
          ? 'border-[#4A7C23] bg-[#7CB342] text-[#0D1A05]'
          : 'border-[#6F521B] bg-[#D5B15E] text-[#191007]',
      )}
    >
      {saved ? <Check className="h-3 w-3" /> : <Download className="h-3 w-3" />}
      {saved ? '已保存' : '保存方案'}
    </button>
  )
}

export default function Tactics() {
  const [players, setPlayers] = useState<TacticalPlayer[]>([])
  const [loading, setLoading] = useState(true)
  const [teamId, setTeamId] = useState<string | null>(null)
  const [formationId, setFormationId] = useState<FormationId>('F01')
  const [teamInstructions, setTeamInstructions] = useState<TeamInstructions>(presets[0].teamInstructions)
  const [activePreset, setActivePreset] = useState('balanced')
  const [starterIds, setStarterIds] = useState<Array<string | null>>([])
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null)
  const [panelPlayerId, setPanelPlayerId] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [hasLoadedStorage, setHasLoadedStorage] = useState(false)
  const [dragOverSlot, setDragOverSlot] = useState<number | null>(null)
  const [activeTab, setActiveTab] = useState<TabId>('personnel')
  const [saveError, setSaveError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    async function fetchPlayers() {
      try {
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) {
          // No team context: fallback to localStorage defaults
          setHasLoadedStorage(true)
          return
        }
        setTeamId(teamRes.data.id)
        const playersRes = await api.get<{ items: PlayerListItem[] }>(`/teams/${teamRes.data.id}/players?page_size=100`)
        if (!cancelled && playersRes.success) {
          setPlayers((playersRes.data?.items || []).filter((player) => player.status === 'ACTIVE'))
        }
      } catch {
        // Keep the tactics editor usable when the local API is unavailable.
        setHasLoadedStorage(true)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPlayers()
    return () => { cancelled = true }
  }, [])

  // Load saved tactics from API, fallback to localStorage
  useEffect(() => {
    if (!teamId || !players.length) return
    const currentTeamId = teamId
    let cancelled = false

    async function fetchTactics() {
      try {
        const res = await api.getTeamTactics(currentTeamId)
        if (cancelled) return
        if (res.success && res.data) {
          const data = res.data
          if (formations.some((formation) => formation.id === data.formation_id)) {
            setFormationId(data.formation_id as FormationId)
          }
          if (data.team_instructions) {
            const loaded: TeamInstructions = {
              ...data.team_instructions,
              player_instructions: data.team_instructions.player_instructions || [],
              situational_rules: data.team_instructions.situational_rules || defaultSituationalRules(),
            }
            setTeamInstructions(loaded)
            const loadedLegacy = loaded.legacy_team_sliders
            const matchedPreset = presets.find((preset) =>
              tacticFields.every((field) => preset.teamInstructions.legacy_team_sliders[field.key] === loadedLegacy[field.key])
            )
            setActivePreset(matchedPreset ? matchedPreset.id : 'custom')
          }
          if (data.lineup_player_ids && data.lineup_player_ids.length > 0) {
            const validIds = data.lineup_player_ids
              .filter((id): id is string => Boolean(id) && players.some((player) => player.id === id))
              .slice(0, 8)
            setStarterIds([...validIds, ...Array(Math.max(0, 8 - validIds.length)).fill(null)])
          }
          return
        }
      } catch {
        // Fallback to localStorage on API error
      }

      // Fallback: localStorage
      const parsed = readStoredSetup()
      if (!parsed) return
      if (parsed.formationId && formations.some((formation) => formation.id === parsed.formationId)) {
        setFormationId(parsed.formationId)
      }
      if (parsed.teamInstructions) {
        const loaded = parsed.teamInstructions
        setTeamInstructions(loaded)
        const loadedLegacy = loaded.legacy_team_sliders
        const matchedPreset = presets.find((preset) =>
          tacticFields.every((field) => preset.teamInstructions.legacy_team_sliders[field.key] === loadedLegacy[field.key])
        )
        setActivePreset(matchedPreset ? matchedPreset.id : 'custom')
      } else if (parsed.preset) {
        setActivePreset(parsed.preset)
      }
      if (parsed.starterIds) setStarterIds(parsed.starterIds.slice(0, 8))
    }

    fetchTactics()
    setHasLoadedStorage(true)
    return () => { cancelled = true }
  }, [teamId, players])

  useEffect(() => {
    if (!hasLoadedStorage || !players.length) return
    setStarterIds((current) => {
      const slots = getSlots(formationId)
      const valid = current.filter((id): id is string => Boolean(id) && players.some((player) => player.id === id))
      if (valid.length) {
        const unique = Array.from(new Set(valid)).slice(0, slots.length)
        return [...unique, ...Array(Math.max(0, slots.length - unique.length)).fill(null)]
      }
      return pickInitialLineup(players, formationId)
    })
  }, [formationId, hasLoadedStorage, players])

  const playerById = useMemo(() => new Map(players.map((player) => [player.id, player])), [players])
  const slots = useMemo(() => getSlots(formationId), [formationId])
  const lineup: StarterSlot[] = useMemo(() => slots.map((slot, index) => ({
    ...slot,
    player: starterIds[index] ? playerById.get(starterIds[index] || '') : undefined,
  })), [playerById, slots, starterIds])
  const starterIdSet = useMemo(() => new Set(starterIds.filter(Boolean)), [starterIds])
  const bench = useMemo(() => players.filter((player) => !starterIdSet.has(player.id)).sort(sortPlayersForLineup), [players, starterIdSet])
  const selectedPlayer = useMemo(() => players.find((player) => player.id === panelPlayerId), [players, panelPlayerId])
  const selectedSlot = useMemo(() => lineup.find((slot) => slot.player?.id === panelPlayerId), [lineup, panelPlayerId])

  const movePlayer = (from: { source: SelectionSource; index: number }, to: { source: SelectionSource; index: number }) => {
    if (from.source === to.source && from.index === to.index) {
      setSelectedPlayerId(null)
      return
    }
    setStarterIds((current) => {
      const next = [...current]
      if (from.source === 'starter' && to.source === 'starter') {
        const temp = next[from.index] || null
        next[from.index] = next[to.index] || null
        next[to.index] = temp
        return next
      }
      if (from.source === 'bench' && to.source === 'starter') {
        const benchPlayer = bench[from.index]
        if (!benchPlayer) return current
        next[to.index] = benchPlayer.id
        return next
      }
      if (from.source === 'starter' && to.source === 'bench') {
        next[from.index] = null
        return next
      }
      return current
    })
    setSelectedPlayerId(null)
    setSaved(false)
  }

  const handleTargetClick = (source: SelectionSource, index: number) => {
    const targetPlayer = source === 'starter' ? lineup[index]?.player : bench[index]
    if (!selectedPlayerId) {
      if (targetPlayer) {
        setSelectedPlayerId(targetPlayer.id)
        setPanelPlayerId(targetPlayer.id)
      }
      return
    }
    const fromSlotIndex = lineup.findIndex((slot) => slot.player?.id === selectedPlayerId)
    const from: { source: SelectionSource; index: number } = fromSlotIndex !== -1
      ? { source: 'starter', index: fromSlotIndex }
      : { source: 'bench', index: bench.findIndex((player) => player.id === selectedPlayerId) }
    if (from.index === -1) {
      setSelectedPlayerId(null)
      return
    }
    movePlayer(from, { source, index })
  }

  const onBenchPlayerClick = (player: TacticalPlayer, _index: number) => {
    setSelectedPlayerId(player.id)
    setPanelPlayerId(player.id)
  }

  const onBenchDragStart = (event: React.DragEvent<HTMLButtonElement>, player: TacticalPlayer, index: number) => {
    event.dataTransfer.setData('application/json', JSON.stringify({ source: 'bench', index }))
    setSelectedPlayerId(player.id)
    setPanelPlayerId(player.id)
  }

  const onPreset = (presetId: string) => {
    const preset = presets.find((item) => item.id === presetId)
    if (!preset) return
    setActivePreset(preset.id)
    setTeamInstructions(preset.teamInstructions)
    setSaved(false)
  }

  const onFormation = (nextFormationId: FormationId) => {
    setFormationId(nextFormationId)
    setSelectedPlayerId(null)
    if (!panelPlayerId || !players.some((p) => p.id === panelPlayerId)) {
      setPanelPlayerId(null)
    }
    setSaved(false)
  }

  const onTacticChange = (key: TacticKey, value: number) => {
    const field = tacticFields.find((item) => item.key === key)
    setActivePreset('custom')
    setTeamInstructions((current) => ({
      ...current,
      legacy_team_sliders: { ...current.legacy_team_sliders, [key]: clamp(value, field?.max ?? 4) },
    }))
    setSaved(false)
  }

  const handleSave = async () => {
    setSaveError(null)

    // Always keep a local draft backup
    localStorage.setItem(storageKey, JSON.stringify({ formationId, teamInstructions, preset: activePreset, starterIds }))

    if (!teamId) {
      // Offline / not logged in: only localStorage
      setSaved(true)
      window.setTimeout(() => setSaved(false), 1800)
      return
    }

    const validStarterIds = starterIds
      .filter((id): id is string => Boolean(id))
      .slice(0, 8)
    const validBenchIds = bench
      .map((player) => player.id)
      .filter((id) => !validStarterIds.includes(id))
      .slice(0, 5)

    const payload: import('../../types/tactics').TeamTacticsUpdate = {
      formation_id: formationId,
      lineup_player_ids: validStarterIds,
      bench_player_ids: validBenchIds,
      team_instructions: teamInstructions,
      set_piece_instructions: {},
      substitution_rules: {},
    }

    try {
      const res = await api.saveTeamTactics(teamId, payload)
      if (res.success) {
        setSaved(true)
        window.setTimeout(() => setSaved(false), 1800)
      } else {
        setSaveError(res.message || '保存失败')
      }
    } catch (error) {
      setSaveError(error instanceof Error ? error.message : '保存失败')
    }
  }

  const autoPick = () => {
    setStarterIds(pickInitialLineup(players, formationId))
    setSelectedPlayerId(null)
    setPanelPlayerId(null)
    setSaved(false)
  }

  const clearPanelPlayer = () => {
    setPanelPlayerId(null)
    setSelectedPlayerId(null)
  }

  if (loading) {
    return <div className="max-w-[1440px] p-8 text-center text-[#8B8BA7]">加载战术室...</div>
  }

  return (
    <div className="mx-auto max-w-[1600px] space-y-4 text-[#EFE8CE]">
      {/* Tab bar */}
      <div className="flex gap-1 border-b-2 border-[#3B3425]">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={clsx(
              'px-4 py-2.5 text-sm font-medium border-b-2 -mb-0.5 transition-all',
              activeTab === tab.id
                ? 'border-[#D5B15E] text-[#D5B15E]'
                : 'border-transparent text-[#786F5A] hover:text-[#FFF8DE]',
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 1: Personnel */}
      {activeTab === 'personnel' && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-36">
                <FormationSelect value={formationId} onChange={onFormation} />
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={autoPick}
                className="border border-[#6F521B] px-3 py-2 text-[11px] font-black text-[#D5B15E] hover:bg-[#2A1E0E]"
              >
                自动排阵
              </button>
              <SaveButton saved={saved} onSave={handleSave} />
            </div>
          </div>

          {saveError && (
            <div className="border-2 border-[#8E2E20] bg-[#2B0905] px-3 py-2 text-xs font-black text-[#E97762]">
              保存失败：{saveError}
            </div>
          )}

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-[260px_1fr_340px]">
            <BenchPanel
              bench={bench}
              selectedPlayerId={selectedPlayerId}
              onPlayerClick={onBenchPlayerClick}
              onDragStart={onBenchDragStart}
            />

            <div className="flex flex-col items-center">
              <div className="relative aspect-[1037/1517] h-[min(78vh,740px)] w-full max-w-[560px] overflow-hidden border-4 border-[#33291A] bg-[#D6C08E] shadow-pixel-lg">
                <img
                  src="/tactics/hand-drawn-board-portrait-pixel-v2.png"
                  alt=""
                  className="absolute inset-0 h-full w-full object-cover opacity-95"
                />
                <div className="absolute inset-0 bg-[#F2DFA6]/10 mix-blend-multiply" />

                {lineup.map((slot, index) => {
                  const player = slot.player
                  const markerPosition = player?.position || slot.position
                  const tone = positionTone[markerPosition]
                  const isSelected = selectedPlayerId === player?.id
                  const isDragTarget = dragOverSlot === index
                  const isEmpty = !player
                  return (
                    <button
                      key={`${slot.id}-${index}`}
                      draggable={Boolean(player)}
                      onClick={() => handleTargetClick('starter', index)}
                      onDragStart={(event) => {
                        event.dataTransfer.setData('application/json', JSON.stringify({ source: 'starter', index }))
                        if (player) {
                          setSelectedPlayerId(player.id)
                          setPanelPlayerId(player.id)
                        }
                      }}
                      onDragOver={(event) => {
                        event.preventDefault()
                        setDragOverSlot(index)
                      }}
                      onDragLeave={() => setDragOverSlot((current) => (current === index ? null : current))}
                      onDrop={(event) => {
                        event.preventDefault()
                        setDragOverSlot(null)
                        const payload = JSON.parse(event.dataTransfer.getData('application/json')) as { source: SelectionSource; index: number }
                        movePlayer(payload, { source: 'starter', index })
                      }}
                      className="group absolute -translate-x-1/2 -translate-y-1/2 text-left"
                      style={{ left: `${slot.x}%`, top: `${slot.y}%` }}
                    >
                      <div
                        className={clsx(
                          'relative h-[74px] w-[74px] transition-transform',
                          isSelected && 'drop-shadow-[0_0_8px_rgba(255,244,184,0.9)]',
                          isDragTarget && !isEmpty && 'scale-110',
                          isEmpty && 'opacity-55 grayscale',
                          !isEmpty && 'group-hover:-translate-y-0.5',
                        )}
                      >
                        <img
                          src={tone.marker}
                          alt=""
                          className="pointer-events-none absolute inset-0 h-full w-full object-contain [image-rendering:pixelated]"
                        />
                        <div
                          className="absolute left-1/2 top-1/2 h-[48px] w-[48px] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full"
                          style={{ backgroundColor: tone.fill }}
                        >
                          {player?.avatar_url ? (
                            <img
                              src={`/${player.avatar_url}`}
                              alt={player?.name || ''}
                              className="h-full w-full object-cover object-top [image-rendering:pixelated]"
                            />
                          ) : (
                            <img
                              src={tone.token}
                              alt=""
                              className="absolute inset-0 h-full w-full object-contain [image-rendering:pixelated]"
                            />
                          )}
                        </div>
                        <span className="absolute -right-1 -top-2 rounded-full border-2 border-[#60471F] bg-[#F8E8B6] px-1.5 text-[10px] font-black text-[#2B1B08] font-['Press_Start_2P']">
                          {index + 1}
                        </span>
                      </div>
                      <div className="absolute left-1/2 top-[74px] w-24 -translate-x-1/2 text-center">
                        <p className={clsx(
                          'truncate rounded-sm border border-[#5A4420] px-1 text-[10px] font-black shadow-[2px_2px_0_rgba(31,21,9,0.34)]',
                          isSelected ? 'bg-[#FFF4B8] text-[#2B1B08]' : 'bg-[#F7E5B5] text-[#241808]',
                        )}>
                          {player?.name || '空位'}
                        </p>
                      </div>
                      {isDragTarget && isEmpty && (
                        <div className="absolute left-1/2 top-1/2 h-[74px] w-[74px] -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-dashed border-[#D5B15E] bg-[#D5B15E]/10" />
                      )}
                    </button>
                  )
                })}
              </div>
            </div>

            <PlayerDetailPanel
              player={selectedPlayer}
              slot={selectedSlot}
              onClear={clearPanelPlayer}
              teamInstructions={teamInstructions}
              onInstructionChange={(next) => {
                setTeamInstructions(next)
                setActivePreset('custom')
                setSaved(false)
              }}
            />
          </div>
        </>
      )}

      {/* Tab 2: Tactics */}
      {activeTab === 'tactics' && (
        <>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <div className="w-36">
                <FormationSelect value={formationId} onChange={onFormation} />
              </div>
              <div className="w-44">
                <PresetSelect value={activePreset} onChange={onPreset} />
              </div>
            </div>
            <SaveButton saved={saved} onSave={handleSave} />
          </div>

          {saveError && (
            <div className="border-2 border-[#8E2E20] bg-[#2B0905] px-3 py-2 text-xs font-black text-[#E97762]">
              保存失败：{saveError}
            </div>
          )}

          <TacticsDesignPanel
            tactics={teamInstructions.legacy_team_sliders}
            activePreset={activePreset}
            onTacticChange={onTacticChange}
            onPreset={onPreset}
          />

          <PhaseTacticsPanel
            teamInstructions={teamInstructions}
            onChange={(next) => {
              setTeamInstructions(next)
              setActivePreset('custom')
              setSaved(false)
            }}
          />

          <SituationalRulesPanel
            teamInstructions={teamInstructions}
            onChange={(next) => {
              setTeamInstructions(next)
              setActivePreset('custom')
              setSaved(false)
            }}
          />
        </>
      )}

      {/* Tab 3: Set piece */}
      {activeTab === 'setpiece' && (
        <div className="flex min-h-[50vh] items-center justify-center">
          <div className="flex flex-col items-center gap-4 border-2 border-[#3B3425] bg-[#15110A] p-8 text-center shadow-pixel">
            <Target className="h-12 w-12 text-[#3B3425]" />
            <h2 className="text-lg font-black text-[#FFF8DE]">定位球</h2>
            <p className="text-sm font-bold text-[#786F5A]">角球 / 任意球 / 点球主罚人<br />暂未开发，敬请期待</p>
          </div>
        </div>
      )}

      {/* Tab 4: Substitution */}
      {activeTab === 'substitution' && (
        <div className="flex min-h-[50vh] items-center justify-center">
          <div className="flex flex-col items-center gap-4 border-2 border-[#3B3425] bg-[#15110A] p-8 text-center shadow-pixel">
            <Users className="h-12 w-12 text-[#3B3425]" />
            <h2 className="text-lg font-black text-[#FFF8DE]">换人策略</h2>
            <p className="text-sm font-bold text-[#786F5A]">暂未开发，敬请期待</p>
          </div>
        </div>
      )}
    </div>
  )
}
