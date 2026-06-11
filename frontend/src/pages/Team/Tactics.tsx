import { useEffect, useMemo, useState } from 'react'
import { api } from '../../api/client'
import type { PlayerListItem } from '../../types/player'
import {
  Chart,
  Check,
  Download,
  Fire,
  Flag,
  Grid3x3,
  Shield,
  Sword,
  Target,
  Users,
  Zap,
} from '../../components/ui/pixel-icons'

type FormationId = 'F01' | 'F02' | 'F03' | 'F04' | 'F05' | 'F06' | 'F07' | 'F08'

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
    desc: '没有明显短板，适合观察对手。',
    icon: Target,
    tactics: { passing_style: 2, attack_width: 2, attack_tempo: 2, defensive_line_height: 2, crossing_strategy: 2, shooting_mentality: 2, playmaker_focus: 0, pressing_intensity: 2, defensive_compactness: 1, marking_strategy: 0, offside_trap: 0, tackling_aggression: 1 },
  },
  {
    id: 'high_press',
    name: '高位逼抢',
    desc: '压上防线和逼抢，换取前场夺回球权。',
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

const storageKey = 'lsl:tactics:v1'

const clamp = (value: number, max: number) => Math.min(max, Math.max(0, value))

const positionColor: Record<string, string> = {
  GK: 'bg-[#D7A94A]',
  DF: 'bg-[#3D8FE6]',
  MF: 'bg-[#50D1C8]',
  FW: 'bg-[#D75A4A]',
}

const formationRows: Record<FormationId, Array<{ position: 'GK' | 'DF' | 'MF' | 'FW'; count: number; y: number }>> = {
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
      position: row.position,
      x: start + spacing * index,
      y: row.y + (row.position === 'MF' && row.count === 4 && index % 2 === 0 ? 3 : 0),
    }))
  })
}

function pickLineup(players: TacticalPlayer[], formationId: FormationId) {
  const used = new Set<string>()
  return getSlots(formationId).map((slot) => {
    const candidates = players
      .filter((player) => player.position === slot.position && !used.has(player.id))
      .sort((a, b) => b.ovr - a.ovr)
    const fallback = players
      .filter((player) => !used.has(player.id))
      .sort((a, b) => b.ovr - a.ovr)
    const player = candidates[0] || fallback[0]
    if (player) used.add(player.id)
    return { ...slot, player }
  })
}

function getMatchFormScore(form?: string) {
  if (form === 'HOT') return 8
  if (form === 'GOOD') return 4
  if (form === 'LOW') return -6
  return 0
}

function scoreFormation(players: TacticalPlayer[], formationId: FormationId) {
  const lineup = pickLineup(players, formationId)
  if (!lineup.length) return 0
  const fit = lineup.reduce((sum, slot) => {
    if (!slot.player) return sum - 10
    const positionBonus = slot.player.position === slot.position ? 8 : -8
    return sum + slot.player.ovr + (slot.player.fitness || 75) * 0.18 + getMatchFormScore(slot.player.match_form) + positionBonus
  }, 0)
  return Math.round(fit / lineup.length)
}

function riskScore(tactics: TacticsSetup) {
  const raw = (4 - tactics.passing_style) * 0.2 +
    tactics.attack_tempo * 0.2 +
    tactics.shooting_mentality * 0.2 +
    tactics.tackling_aggression * 0.15 +
    (2 - tactics.marking_strategy) * 0.1 +
    (4 - tactics.defensive_line_height) * 0.15
  return Math.round(Math.min(1, Math.max(0, raw / 4)) * 100)
}

function tacticalFlags(tactics: TacticsSetup) {
  return [
    { label: '高位逼抢', active: tactics.defensive_line_height >= 3 && tactics.pressing_intensity >= 3 },
    { label: '深度防守', active: tactics.defensive_line_height <= 1 && tactics.defensive_compactness >= 2 },
    { label: '越位陷阱', active: tactics.offside_trap >= 1 && tactics.defensive_line_height >= 2 },
    { label: '盯人元素', active: tactics.marking_strategy >= 1 },
    { label: '后场组织', active: tactics.passing_style <= 1 && tactics.defensive_line_height >= 2 },
    { label: '反击焦点', active: tactics.attack_tempo >= 4 },
  ]
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
    <div className="border-2 border-[#242832] bg-[#07080A]/82 p-3 shadow-pixel-sm">
      <div className="mb-2 flex items-center justify-between gap-3">
        <span className="text-sm font-black text-[#E8EAD8]">{field.label}</span>
        <span className="stat-number text-sm text-[#B8E532]">{value}/{field.max}</span>
      </div>
      <input
        type="range"
        min={0}
        max={field.max}
        step={1}
        value={value}
        onChange={(event) => onChange(field.key, Number(event.target.value))}
        className="w-full accent-[#B8E532]"
      />
      <div className="mt-1 flex items-center justify-between text-[11px] font-bold text-[#697157]">
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
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const raw = localStorage.getItem(storageKey)
    if (!raw) return
    try {
      const parsed = JSON.parse(raw) as { formationId?: FormationId; tactics?: TacticsSetup; preset?: string }
      if (parsed.formationId && formations.some((formation) => formation.id === parsed.formationId)) {
        setFormationId(parsed.formationId)
      }
      if (parsed.tactics) setTactics(parsed.tactics)
      if (parsed.preset) setActivePreset(parsed.preset)
    } catch {
      localStorage.removeItem(storageKey)
    }
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

  const selectedFormation = formations.find((formation) => formation.id === formationId) || formations[0]
  const lineup = useMemo(() => pickLineup(players, formationId), [players, formationId])
  const fitScore = useMemo(() => scoreFormation(players, formationId), [players, formationId])
  const risk = useMemo(() => riskScore(tactics), [tactics])
  const flags = useMemo(() => tacticalFlags(tactics), [tactics])
  const activeFlags = flags.filter((flag) => flag.active)

  const onPreset = (presetId: string) => {
    const preset = presets.find((item) => item.id === presetId)
    if (!preset) return
    setActivePreset(preset.id)
    setTactics(preset.tactics)
  }

  const onTacticChange = (key: TacticKey, value: number) => {
    const field = tacticFields.find((item) => item.key === key)
    setActivePreset('custom')
    setTactics((current) => ({ ...current, [key]: clamp(value, field?.max ?? 4) }))
  }

  const handleSave = () => {
    localStorage.setItem(storageKey, JSON.stringify({ formationId, tactics, preset: activePreset }))
    setSaved(true)
    window.setTimeout(() => setSaved(false), 1800)
  }

  if (loading) {
    return <div className="max-w-[1440px] p-8 text-center text-[#8B8BA7]">加载战术室...</div>
  }

  return (
    <div className="max-w-[1440px] space-y-5">
      <section className="relative overflow-hidden border-2 border-[#2F3740] bg-[#07080A] shadow-pixel-lg">
        <img
          src="/tactics/hand-drawn-board-v1.png"
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-38"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#050609] via-[#050609]/82 to-[#050609]/42" />
        <div className="relative grid gap-5 p-5 lg:grid-cols-[1fr_360px] lg:p-6">
          <div className="flex min-h-[180px] flex-col justify-between">
            <div>
              <div className="mb-3 inline-flex items-center gap-2 border-2 border-[#B8E532]/45 bg-[#0C1A0D]/80 px-3 py-1 text-xs font-black text-[#B8E532]">
                <Grid3x3 className="h-3.5 w-3.5" />
                MATCH ENGINE TACTICS
              </div>
              <h1 className="text-3xl font-black text-[#F2F4E8]">战术室</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-[#9AA58E]">
                设置 8 人制阵型、比赛预设和 12 项引擎战术参数。当前版本先保存到本机配置，字段已对齐后端比赛请求。
              </p>
            </div>
            <div className="mt-5 grid max-w-3xl grid-cols-3 gap-3">
              {[
                { label: '阵型适配', value: fitScore, color: 'text-[#B8E532]' },
                { label: '风险指数', value: risk, color: risk > 68 ? 'text-[#D75A4A]' : 'text-[#D7A94A]' },
                { label: '生效机制', value: activeFlags.length, color: 'text-[#50D1C8]' },
              ].map((item) => (
                <div key={item.label} className="border-2 border-[#242832] bg-[#07080A]/82 p-3">
                  <p className="text-[11px] font-black text-[#697157]">{item.label}</p>
                  <strong className={`stat-number text-2xl ${item.color}`}>{item.value}</strong>
                </div>
              ))}
            </div>
          </div>
          <div className="border-2 border-[#B8E532]/35 bg-[#050609]/76 p-4 shadow-pixel">
            <div className="mb-3 flex items-center justify-between">
              <span className="text-sm font-black text-[#E8EAD8]">当前方案</span>
              <span className={`text-sm font-black ${selectedFormation.tone}`}>{selectedFormation.shape}</span>
            </div>
            <p className="text-xl font-black text-white">{selectedFormation.name}</p>
            <p className="mt-2 text-sm leading-6 text-[#8B8BA7]">{selectedFormation.desc}</p>
            <button
              onClick={handleSave}
              className="mt-5 flex w-full items-center justify-center gap-2 border-2 border-[#0A5A5D] bg-[#0D7377] px-4 py-3 text-sm font-black text-white shadow-pixel-sm transition-all hover:-translate-x-0.5 hover:-translate-y-0.5 hover:bg-[#0A5A5D]"
            >
              {saved ? <Check className="h-4 w-4" /> : <Download className="h-4 w-4" />}
              {saved ? '已保存到本机' : '保存战术方案'}
            </button>
          </div>
        </div>
      </section>

      <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)_360px]">
        <aside className="space-y-5">
          <section className="border-2 border-[#242832] bg-[#07080A] p-4 shadow-pixel">
            <div className="mb-4 flex items-center gap-2">
              <Target className="h-4 w-4 text-[#B8E532]" />
              <h2 className="font-black text-[#F2F4E8]">阵型选择</h2>
            </div>
            <div className="space-y-2">
              {formations.map((formation) => (
                <button
                  key={formation.id}
                  onClick={() => setFormationId(formation.id)}
                  className={`w-full border-2 p-3 text-left transition-all ${
                    formationId === formation.id
                      ? 'border-[#B8E532] bg-[#0C1A0D] shadow-pixel-green'
                      : 'border-[#242832] bg-[#050609] hover:border-[#B8E532]/45'
                  }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <div>
                      <p className="font-black text-white">{formation.name}</p>
                      <p className="text-xs font-bold text-[#697157]">{formation.id} · {formation.shape}</p>
                    </div>
                    <span className={`border border-current px-2 py-0.5 text-xs font-black ${formation.tone}`}>{formation.tag}</span>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section className="border-2 border-[#242832] bg-[#07080A] p-4 shadow-pixel">
            <div className="mb-4 flex items-center gap-2">
              <Sword className="h-4 w-4 text-[#B8E532]" />
              <h2 className="font-black text-[#F2F4E8]">比赛预设</h2>
            </div>
            <div className="grid gap-2">
              {presets.map((preset) => (
                <button
                  key={preset.id}
                  onClick={() => onPreset(preset.id)}
                  className={`border-2 p-3 text-left transition-all ${
                    activePreset === preset.id
                      ? 'border-[#50D1C8] bg-[#071719]'
                      : 'border-[#242832] bg-[#050609] hover:border-[#50D1C8]/50'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <preset.icon className="mt-0.5 h-4 w-4 text-[#50D1C8]" />
                    <div>
                      <p className="font-black text-white">{preset.name}</p>
                      <p className="mt-1 text-xs leading-5 text-[#8B8BA7]">{preset.desc}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </section>
        </aside>

        <main className="space-y-5">
          <section className="border-2 border-[#242832] bg-[#07080A] p-4 shadow-pixel">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <Users className="h-4 w-4 text-[#B8E532]" />
                <h2 className="font-black text-[#F2F4E8]">战术板首发</h2>
              </div>
              <div className="flex flex-wrap items-center gap-2 text-[11px] font-black text-[#8B8BA7]">
                {['GK', 'DF', 'MF', 'FW'].map((position) => (
                  <span key={position} className="inline-flex items-center gap-1">
                    <span className={`h-2.5 w-2.5 ${positionColor[position]}`} />
                    {position}
                  </span>
                ))}
              </div>
            </div>

            <div className="relative mx-auto aspect-[3/4] max-h-[720px] w-full max-w-[560px] overflow-hidden border-4 border-[#2F3740] bg-[#143F2C] shadow-pixel-lg">
              <div
                className="absolute inset-0 opacity-35"
                style={{
                  backgroundImage: 'linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)',
                  backgroundSize: '18px 18px',
                }}
              />
              <div className="absolute inset-5 border-2 border-white/30" />
              <div className="absolute left-5 right-5 top-1/2 h-0.5 bg-white/25" />
              <div className="absolute left-1/2 top-1/2 h-24 w-24 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white/25" />
              <div className="absolute left-1/2 top-5 h-16 w-28 -translate-x-1/2 border-x-2 border-b-2 border-white/25" />
              <div className="absolute bottom-5 left-1/2 h-16 w-28 -translate-x-1/2 border-x-2 border-t-2 border-white/25" />

              {lineup.map((slot, index) => (
                <div
                  key={`${slot.position}-${index}`}
                  className="absolute -translate-x-1/2 -translate-y-1/2"
                  style={{ left: `${slot.x}%`, top: `${slot.y}%` }}
                >
                  <div className={`grid h-11 w-11 place-items-center border-2 border-white/80 shadow-pixel ${positionColor[slot.position]}`}>
                    <span className="text-xs font-black text-white">{slot.position}</span>
                  </div>
                  <div className="absolute left-1/2 top-12 w-24 -translate-x-1/2 text-center">
                    <p className="truncate bg-black/68 px-1 text-[10px] font-black text-white">
                      {slot.player?.name || '空位'}
                    </p>
                    <p className="mt-0.5 text-[10px] font-black text-[#B8E532]">
                      {slot.player ? `OVR ${slot.player.ovr}` : 'NEED'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </section>

          <section className="grid gap-4 lg:grid-cols-2">
            {(['进攻组织', '防守结构'] as const).map((group) => (
              <div key={group} className="border-2 border-[#242832] bg-[#07080A] p-4 shadow-pixel">
                <div className="mb-4 flex items-center gap-2">
                  {group === '进攻组织' ? <Sword className="h-4 w-4 text-[#D75A4A]" /> : <Shield className="h-4 w-4 text-[#63B3FF]" />}
                  <h2 className="font-black text-[#F2F4E8]">{group}</h2>
                </div>
                <div className="space-y-3">
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

        <aside className="space-y-5">
          <section className="border-2 border-[#242832] bg-[#07080A] p-4 shadow-pixel">
            <div className="mb-4 flex items-center gap-2">
              <Chart className="h-4 w-4 text-[#B8E532]" />
              <h2 className="font-black text-[#F2F4E8]">阵型通道</h2>
            </div>
            {['前场控制', '中场控制', '后场控制'].map((label, index) => (
              <div key={label} className="mb-4 last:mb-0">
                <div className="mb-2 flex items-center justify-between text-sm">
                  <span className="font-bold text-[#8B8BA7]">{label}</span>
                  <span className="stat-number font-black text-[#B8E532]">{selectedFormation.lanes[index]}</span>
                </div>
                <div className="pixel-progress-track">
                  <div className="pixel-progress-fill" style={{ width: `${selectedFormation.lanes[index]}%` }} />
                </div>
              </div>
            ))}
          </section>

          <section className="border-2 border-[#242832] bg-[#07080A] p-4 shadow-pixel">
            <div className="mb-4 flex items-center gap-2">
              <Zap className="h-4 w-4 text-[#50D1C8]" />
              <h2 className="font-black text-[#F2F4E8]">引擎触发</h2>
            </div>
            <div className="grid gap-2">
              {flags.map((flag) => (
                <div
                  key={flag.label}
                  className={`flex items-center justify-between border-2 px-3 py-2 text-sm font-black ${
                    flag.active
                      ? 'border-[#50D1C8]/70 bg-[#071719] text-[#E8EAD8]'
                      : 'border-[#242832] bg-[#050609] text-[#4F5A49]'
                  }`}
                >
                  <span>{flag.label}</span>
                  <span>{flag.active ? 'ON' : 'OFF'}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="border-2 border-[#242832] bg-[#07080A] p-4 shadow-pixel">
            <div className="mb-4 flex items-center gap-2">
              <Shield className="h-4 w-4 text-[#D7A94A]" />
              <h2 className="font-black text-[#F2F4E8]">阵容需求</h2>
            </div>
            <div className="grid grid-cols-3 gap-2">
              {(['DF', 'MF', 'FW'] as const).map((position) => (
                <div key={position} className="border-2 border-[#242832] bg-[#050609] p-3 text-center">
                  <p className="text-xs font-black text-[#697157]">{position}</p>
                  <p className="stat-number text-xl font-black text-white">{selectedFormation.requirements[position]}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 border-2 border-[#2F3740] bg-[#050609] p-3 text-xs leading-5 text-[#8B8BA7]">
              比赛引擎会按阵型挑选 1 名 GK 加 7 名外场首发。当前适配分综合 OVR、体能、状态和位置匹配。
            </div>
          </section>
        </aside>
      </div>
    </div>
  )
}
