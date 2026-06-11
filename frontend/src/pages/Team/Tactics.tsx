import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import clsx from 'clsx'
import { api } from '../../api/client'
import type { PlayerAbility, PlayerListItem, PlayerPosition } from '../../types/player'
import {
  Chart,
  Check,
  Download,
  Fire,
  Flag,
  Shield,
  Sword,
  Target,
  UserPlus,
  Users,
  Zap,
} from '../../components/ui/pixel-icons'

type FormationId = 'F01' | 'F02' | 'F03' | 'F04' | 'F05' | 'F06' | 'F07' | 'F08'
type SelectionSource = 'starter' | 'bench'

type TacticsSetup = {
  passing_style: number
  attack_width: number
  attack_tempo: number
  defensive_line_height: number
  crossing_strategy: number
  shooting_mentality: number
  playmaker_focus: number
  pressing_intensity: number
  defensive_compactness: number
  marking_strategy: number
  offside_trap: number
  tackling_aggression: number
}

type TacticKey = keyof TacticsSetup
type TacticalPlayer = PlayerListItem & { fitness?: number; match_form?: string }
type StarterSlot = ReturnType<typeof getSlots>[number] & { player?: TacticalPlayer }

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

const presets: Array<{ id: string; name: string; desc: string; icon: typeof Target; tactics: TacticsSetup }> = [
  {
    id: 'balanced',
    name: '均衡默认',
    desc: '观察对手，线间距离保持稳定。',
    icon: Target,
    tactics: { passing_style: 2, attack_width: 2, attack_tempo: 2, defensive_line_height: 2, crossing_strategy: 2, shooting_mentality: 2, playmaker_focus: 0, pressing_intensity: 2, defensive_compactness: 1, marking_strategy: 0, offside_trap: 0, tackling_aggression: 1 },
  },
  {
    id: 'high_press',
    name: '高位逼抢',
    desc: '压上防线，前场夺回球权。',
    icon: Zap,
    tactics: { passing_style: 2, attack_width: 2, attack_tempo: 3, defensive_line_height: 4, crossing_strategy: 2, shooting_mentality: 3, playmaker_focus: 0, pressing_intensity: 4, defensive_compactness: 1, marking_strategy: 2, offside_trap: 2, tackling_aggression: 3 },
  },
  {
    id: 'possession',
    name: '控球推进',
    desc: '短传和组织核心，降低草率射门。',
    icon: Chart,
    tactics: { passing_style: 4, attack_width: 2, attack_tempo: 1, defensive_line_height: 3, crossing_strategy: 1, shooting_mentality: 1, playmaker_focus: 2, pressing_intensity: 2, defensive_compactness: 2, marking_strategy: 1, offside_trap: 1, tackling_aggression: 1 },
  },
  {
    id: 'counter',
    name: '极速反击',
    desc: '回收阵型后快速纵向推进。',
    icon: Fire,
    tactics: { passing_style: 1, attack_width: 2, attack_tempo: 4, defensive_line_height: 1, crossing_strategy: 2, shooting_mentality: 2, playmaker_focus: 0, pressing_intensity: 1, defensive_compactness: 2, marking_strategy: 0, offside_trap: 0, tackling_aggression: 1 },
  },
  {
    id: 'deep_defense',
    name: '深度防反',
    desc: '低位压缩空间，优先降低失球风险。',
    icon: Shield,
    tactics: { passing_style: 1, attack_width: 1, attack_tempo: 2, defensive_line_height: 0, crossing_strategy: 2, shooting_mentality: 2, playmaker_focus: 0, pressing_intensity: 0, defensive_compactness: 2, marking_strategy: 0, offside_trap: 0, tackling_aggression: 0 },
  },
  {
    id: 'wide_attack',
    name: '边路冲击',
    desc: '宽度和传中拉满，适合高点前锋。',
    icon: Flag,
    tactics: { passing_style: 2, attack_width: 4, attack_tempo: 3, defensive_line_height: 2, crossing_strategy: 4, shooting_mentality: 3, playmaker_focus: 0, pressing_intensity: 2, defensive_compactness: 1, marking_strategy: 0, offside_trap: 0, tackling_aggression: 2 },
  },
  {
    id: 'all_out',
    name: '全力进攻',
    desc: '高节奏高射门，适合必须进球的阶段。',
    icon: Sword,
    tactics: { passing_style: 1, attack_width: 3, attack_tempo: 4, defensive_line_height: 3, crossing_strategy: 3, shooting_mentality: 4, playmaker_focus: 0, pressing_intensity: 3, defensive_compactness: 0, marking_strategy: 1, offside_trap: 1, tackling_aggression: 3 },
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
    return JSON.parse(raw) as {
      formationId?: FormationId
      tactics?: TacticsSetup
      preset?: string
      starterIds?: Array<string | null>
    }
  } catch {
    localStorage.removeItem(storageKey)
    return null
  }
}

function PlayerMini({
  player,
  active,
  compact,
}: {
  player: TacticalPlayer
  active?: boolean
  compact?: boolean
}) {
  const tone = positionTone[player.position]
  return (
    <div className={clsx('flex min-w-0 items-center gap-3', compact && 'gap-2')}>
      <div className={clsx('relative grid shrink-0 place-items-center font-black overflow-hidden rounded-full border-2', compact ? 'h-9 w-9 text-[10px]' : 'h-11 w-11 text-xs', tone.ring)}>
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
      <div className="min-w-0">
        <p className={clsx('truncate font-black', active ? 'text-[#F8F4DE]' : 'text-[#E7E0C8]', compact ? 'text-xs' : 'text-sm')}>
          {player.name}
        </p>
        <p className="text-[11px] font-bold text-[#786F5A]">
          OVR {player.ovr} · {formatForm(player.match_form)}
        </p>
      </div>
    </div>
  )
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

function PlayerPanel({ player }: { player: TacticalPlayer }) {
  const navigate = useNavigate()
  const tone = positionTone[player.position]
  const fitnessColor = player.fitness >= 80 ? 'bg-[#7CB342]' : player.fitness >= 50 ? 'bg-[#E6B800]' : 'bg-[#D75A4A]'
  const formColor = player.match_form === 'HOT' ? 'text-[#E8C84A]' : player.match_form === 'GOOD' ? 'text-[#7CB342]' : player.match_form === 'LOW' ? 'text-[#D75A4A]' : 'text-[#A99E83]'

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={() => navigate(`/players/${player.id}`)}
        className="flex w-full items-start gap-3 text-left transition-opacity hover:opacity-85"
      >
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
          <h3 className="truncate text-base font-black text-[#FFF8DE]">{player.name}</h3>
          <p className="mt-1 text-sm font-black text-[#D5B15E]">{player.age}岁</p>
        </div>
      </button>

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

export default function Tactics() {
  const [players, setPlayers] = useState<TacticalPlayer[]>([])
  const [loading, setLoading] = useState(true)
  const [formationId, setFormationId] = useState<FormationId>('F01')
  const [tactics, setTactics] = useState<TacticsSetup>(presets[0].tactics)
  const [activePreset, setActivePreset] = useState('balanced')
  const [starterIds, setStarterIds] = useState<Array<string | null>>([])
  const [selectedPlayerId, setSelectedPlayerId] = useState<string | null>(null)
  const [panelPlayerId, setPanelPlayerId] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const [hasLoadedStorage, setHasLoadedStorage] = useState(false)

  useEffect(() => {
    const parsed = readStoredSetup()
    if (!parsed) {
      setHasLoadedStorage(true)
      return
    }
    if (parsed.formationId && formations.some((formation) => formation.id === parsed.formationId)) {
      setFormationId(parsed.formationId)
    }
    if (parsed.tactics) {
      const loadedTactics = parsed.tactics
      setTactics(loadedTactics)
      const matchedPreset = presets.find((preset) =>
        tacticFields.every((field) => preset.tactics[field.key] === loadedTactics[field.key])
      )
      setActivePreset(matchedPreset ? matchedPreset.id : 'custom')
    } else if (parsed.preset) {
      setActivePreset(parsed.preset)
    }
    if (parsed.starterIds) setStarterIds(parsed.starterIds.slice(0, 8))
    setHasLoadedStorage(true)
  }, [])

  useEffect(() => {
    let cancelled = false
    async function fetchPlayers() {
      try {
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) return
        const playersRes = await api.get<{ items: PlayerListItem[] }>(`/teams/${teamRes.data.id}/players?page_size=100`)
        if (!cancelled && playersRes.success) {
          setPlayers((playersRes.data?.items || []).filter((player) => player.status === 'ACTIVE'))
        }
      } catch {
        // Keep the tactics editor usable when the local API is unavailable.
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetchPlayers()
    return () => { cancelled = true }
  }, [])

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

  const onPreset = (presetId: string) => {
    const preset = presets.find((item) => item.id === presetId)
    if (!preset) return
    setActivePreset(preset.id)
    setTactics(preset.tactics)
    setSaved(false)
  }

  const onFormation = (nextFormationId: FormationId) => {
    setFormationId(nextFormationId)
    setSelectedPlayerId(null)
    setPanelPlayerId(null)
    setSaved(false)
  }

  const onTacticChange = (key: TacticKey, value: number) => {
    const field = tacticFields.find((item) => item.key === key)
    setActivePreset('custom')
    setTactics((current) => ({ ...current, [key]: clamp(value, field?.max ?? 4) }))
    setSaved(false)
  }

  const handleSave = () => {
    localStorage.setItem(storageKey, JSON.stringify({ formationId, tactics, preset: activePreset, starterIds }))
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1800)
  }

  const autoPick = () => {
    setStarterIds(pickInitialLineup(players, formationId))
    setSelectedPlayerId(null)
    setPanelPlayerId(null)
    setSaved(false)
  }

  if (loading) {
    return <div className="max-w-[1440px] p-8 text-center text-[#8B8BA7]">加载战术室...</div>
  }

  return (
    <div className="max-w-[1600px] space-y-4 text-[#EFE8CE]">
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          className="inline-flex items-center gap-1.5 border-2 border-[#6F521B] bg-[#D5B15E] px-3 py-1.5 text-xs font-black text-[#191007] shadow-pixel-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:brightness-110"
        >
          {saved ? <Check className="h-3 w-3" /> : <Download className="h-3 w-3" />}
          {saved ? '已保存' : '保存方案'}
        </button>
      </div>

      <div className="grid gap-4 xl:grid-cols-[280px_minmax(0,1fr)_300px] 2xl:grid-cols-[330px_minmax(0,1fr)_340px]">
        <aside className="space-y-4">
          <section className="border-2 border-[#3B3425] bg-[#15110A] p-4 shadow-pixel">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-[#D5B15E]" />
                <h2 className="font-black text-[#FFF8DE]">替补席</h2>
              </div>
              <button
                onClick={autoPick}
                className="border border-[#6F521B] px-2 py-1 text-[11px] font-black text-[#D5B15E] hover:bg-[#2A1E0E]"
              >
                自动选择
              </button>
            </div>
            <div className="max-h-[520px] space-y-2 overflow-y-auto pr-1">
              {bench.length ? bench.map((player, index) => (
                <button
                  key={player.id}
                  draggable
                  onClick={() => handleTargetClick('bench', index)}
                  onDragStart={(event) => {
                    event.dataTransfer.setData('application/json', JSON.stringify({ source: 'bench', index }))
                    setSelectedPlayerId(player.id)
                    setPanelPlayerId(player.id)
                  }}
                  onDragOver={(event) => event.preventDefault()}
                  onDrop={(event) => {
                    event.preventDefault()
                    const payload = JSON.parse(event.dataTransfer.getData('application/json')) as { source: SelectionSource; index: number }
                    movePlayer(payload, { source: 'bench', index })
                  }}
                  className={clsx(
                    'w-full border-2 p-2 text-left transition-all',
                    selectedPlayerId === player.id
                      ? 'border-[#D5B15E] bg-[#2A1E0E]'
                      : 'border-[#3B3425] bg-[#0D0B07] hover:border-[#D5B15E]/55',
                  )}
                >
                  <PlayerMini player={player} compact />
                </button>
              )) : (
                <div className="border-2 border-dashed border-[#3B3425] p-4 text-center text-sm font-bold text-[#786F5A]">
                  暂无可用替补
                </div>
              )}
            </div>
          </section>
        </aside>

        <main className="space-y-4">
          <div className="relative mx-auto aspect-[3/4] h-[min(78vh,760px)] min-h-[560px] max-w-[620px] overflow-hidden border-4 border-[#33291A] bg-[#D6C08E] shadow-pixel-lg">
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
                    onDragOver={(event) => event.preventDefault()}
                    onDrop={(event) => {
                      event.preventDefault()
                      const payload = JSON.parse(event.dataTransfer.getData('application/json')) as { source: SelectionSource; index: number }
                      movePlayer(payload, { source: 'starter', index })
                    }}
                    className="group absolute -translate-x-1/2 -translate-y-1/2 text-left"
                    style={{ left: `${slot.x}%`, top: `${slot.y}%` }}
                  >
                    <div
                      className={clsx(
                        'relative h-[86px] w-[86px] transition-transform group-hover:-translate-y-0.5',
                        selectedPlayerId === player?.id && 'outline outline-4 outline-[#FFF4B8]',
                        !player && 'opacity-55 grayscale',
                      )}
                    >
                      <img
                        src={tone.marker}
                        alt=""
                        className="pointer-events-none absolute inset-0 h-full w-full object-contain [image-rendering:pixelated]"
                      />
                      <div
                        className="absolute left-1/2 top-1/2 h-[58px] w-[58px] -translate-x-1/2 -translate-y-1/2 overflow-hidden rounded-full"
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
                    <div className="absolute left-1/2 top-[86px] w-28 -translate-x-1/2 text-center">
                      <p className="truncate rounded-sm border border-[#5A4420] bg-[#F7E5B5] px-1.5 text-[11px] font-black text-[#241808] shadow-[2px_2px_0_rgba(31,21,9,0.34)]">
                        {player?.name || '空位'}
                      </p>
                    </div>
                  </button>
                )
              })}
            </div>

          <section className="grid gap-3 lg:grid-cols-2">
            {(['进攻组织', '防守结构'] as const).map((group) => (
              <div key={group} className="border-2 border-[#3B3425] bg-[#15110A] p-4 shadow-pixel">
                <div className="mb-3 flex items-center gap-2">
                  {group === '进攻组织' ? <Sword className="h-4 w-4 text-[#E97762]" /> : <Shield className="h-4 w-4 text-[#63A9E8]" />}
                  <h2 className="font-black text-[#FFF8DE]">{group}</h2>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {tacticFields.filter((field) => field.group === group).map((field) => (
                    <TacticSlider
                      key={field.key}
                      field={field}
                      value={tactics[field.key]}
                      onChange={onTacticChange}
                    />
                  ))}
                </div>
              </div>
            ))}
          </section>
        </main>

        <aside className="space-y-4">
          <section className="border-2 border-[#3B3425] bg-[#15110A] p-3 shadow-pixel">
            <div className="mb-3 flex items-center gap-2">
              <Target className="h-4 w-4 text-[#D5B15E]" />
              <h2 className="font-black text-[#FFF8DE]">比赛设置</h2>
            </div>
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-[10px] font-black text-[#786F5A]">阵型</label>
                <select
                  value={formationId}
                  onChange={(e) => onFormation(e.target.value as FormationId)}
                  className="w-full appearance-none border-2 border-[#3B3425] bg-[#0D0B07] px-3 py-2 text-sm font-bold text-[#FFF8DE] focus:border-[#D5B15E] focus:outline-none"
                >
                  {formations.map((formation) => (
                    <option key={formation.id} value={formation.id}>{formation.name} · {formation.shape}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="mb-1.5 block text-[10px] font-black text-[#786F5A]">比赛预设</label>
                <select
                  value={activePreset}
                  onChange={(e) => onPreset(e.target.value)}
                  className="w-full appearance-none border-2 border-[#3B3425] bg-[#0D0B07] px-3 py-2 text-sm font-bold text-[#FFF8DE] focus:border-[#D5B15E] focus:outline-none"
                >
                  <option value="custom" disabled>自定义</option>
                  {presets.map((preset) => (
                    <option key={preset.id} value={preset.id}>{preset.name}</option>
                  ))}
                </select>
              </div>
            </div>
          </section>

          <section className="border-2 border-[#3B3425] bg-[#15110A] p-4 shadow-pixel">
            <div className="mb-3 flex items-center gap-2">
              <UserPlus className="h-4 w-4 text-[#D5B15E]" />
              <h2 className="font-black text-[#FFF8DE]">球员面板</h2>
            </div>
            {selectedPlayer ? (
              <PlayerPanel player={selectedPlayer} />
            ) : (
              <div className="border-2 border-dashed border-[#3B3425] bg-[#0D0B07] p-4 text-sm leading-6 text-[#8F846D]">
                选择一名首发或替补后，这里会显示球员状态和数据。
              </div>
            )}
          </section>

        </aside>
      </div>
    </div>
  )
}
