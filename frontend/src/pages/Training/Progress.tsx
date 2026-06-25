import { useEffect, useMemo, useState } from 'react'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  Scatter,
} from 'recharts'
import { clsx } from 'clsx'
import { api } from '../../api/client'
import { useSeasons } from '../../hooks/useSeasons'
import { TrainingPageShell } from './components/TrainingPageShell'
import Avatar from '../../components/ui/Avatar'
import { User } from '../../components/ui/pixel-icons'
import type { PlayerListItem } from '../../types/player'
import type { TrainingProgressResponse } from '../../types/training'

const METRIC_GROUPS: { label: string; options: { key: string; label: string }[] }[] = [
  { label: '综合', options: [{ key: 'ovr', label: 'OVR' }] },
  {
    label: '进攻',
    options: [
      { key: 'sho', label: '射门' },
      { key: 'pas', label: '传球' },
      { key: 'dri', label: '盘带' },
      { key: 'fin', label: '远射' },
      { key: 'cro', label: '传中' },
      { key: 'hea', label: '头球' },
    ],
  },
  {
    label: '身体',
    options: [
      { key: 'spd', label: '速度' },
      { key: 'acc', label: '爆发力' },
      { key: 'str_', label: '力量' },
      { key: 'sta', label: '体能' },
      { key: 'bal', label: '平衡' },
    ],
  },
  {
    label: '防守/技术',
    options: [
      { key: 'defe', label: '防守意识' },
      { key: 'tkl', label: '抢断' },
      { key: 'vis', label: '视野' },
      { key: 'con', label: '控球' },
      { key: 'com', label: '镇定' },
      { key: 'dec', label: '球商' },
    ],
  },
  {
    label: '门将',
    options: [
      { key: 'sav', label: '扑救' },
      { key: 'ref', label: '反应' },
      { key: 'pos', label: '站位' },
      { key: 'rus', label: '出击' },
    ],
  },
  {
    label: '定位球',
    options: [
      { key: 'fk', label: '任意球' },
      { key: 'pk', label: '点球' },
    ],
  },
]

const PALETTE = [
  '#B9EF3F',
  '#1F5F43',
  '#FFC247',
  '#59C7EE',
  '#FF6F59',
]

function MetricSelect({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-[#466353] whitespace-nowrap">指标</label>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#173126] text-sm px-3 py-2 focus:outline-none focus:border-[#1F5F43]"
      >
        {METRIC_GROUPS.map((group) => (
          <optgroup key={group.label} label={group.label} className="text-[#466353]">
            {group.options.map((opt) => (
              <option key={opt.key} value={opt.key}>
                {opt.label}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  )
}

function PlayerSelect({
  players,
  selected,
  onChange,
}: {
  players: PlayerListItem[]
  selected: string[]
  onChange: (ids: string[]) => void
}) {
  const toggle = (id: string) => {
    if (selected.includes(id)) {
      onChange(selected.filter((x) => x !== id))
    } else if (selected.length < 5) {
      onChange([...selected, id])
    }
  }

  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-[#466353]">球员</span>
        <span className={clsx('text-xs', selected.length >= 5 ? 'text-[#FF6F59]' : 'text-[#8B5A2B]/40')}>
          {selected.length}/5
        </span>
      </div>
      <div className="max-h-60 overflow-y-auto border-2 border-[#1F5F43]/20 bg-[#FFF8DC]/80 p-2 space-y-1">
        {players.map((p) => {
          const isSelected = selected.includes(p.id)
          return (
            <button
              key={p.id}
              onClick={() => toggle(p.id)}
              disabled={!isSelected && selected.length >= 5}
              className={clsx(
                'w-full flex items-center gap-3 px-2 py-1.5 text-left transition-colors',
                isSelected
                  ? 'bg-[#B9EF3F]/30 border border-[#1F5F43]/50'
                  : 'hover:bg-[#FFF8DC]/60 border border-transparent',
                !isSelected && selected.length >= 5 && 'opacity-40 cursor-not-allowed'
              )}
            >
              <div className="relative">
                <Avatar
                  src={p.avatar_url ? `/${p.avatar_url}` : undefined}
                  name={p.name}
                  size="xs"
                  fallback={<User className="w-3 h-3 text-[#466353]" />}
                />
                {isSelected && (
                  <span className="absolute -top-1 -right-1 w-3 h-3 bg-[#B9EF3F] text-[#173126] text-[8px] flex items-center justify-center font-bold">
                    ✓
                  </span>
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium text-[#173126] truncate">{p.name}</div>
                <div className="text-xs text-[#466353]">
                  {p.position} · OVR {p.ovr}
                </div>
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function RangeInput({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  onChange: (v: number) => void
}) {
  return (
    <div className="flex items-center gap-2">
      <label className="text-sm text-[#466353] whitespace-nowrap">{label}</label>
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        onChange={(e) => {
          const v = parseInt(e.target.value, 10)
          if (!isNaN(v)) onChange(Math.max(min, Math.min(max, v)))
        }}
        className="w-20 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#173126] text-sm px-2 py-2 focus:outline-none focus:border-[#1F5F43]"
      />
    </div>
  )
}

function ProgressChart({ data }: { data: TrainingProgressResponse }) {
  const allValues = useMemo(
    () => data.series.flatMap((s) => s.values.map((v) => v.value)),
    [data]
  )
  const minValue = useMemo(() => (allValues.length ? Math.min(...allValues) : 0), [allValues])
  const maxValue = useMemo(() => (allValues.length ? Math.max(...allValues) : 0), [allValues])

  const padding = useMemo(() => {
    const range = maxValue - minValue || 1
    return range * 0.1
  }, [minValue, maxValue])

  const scatterData = useMemo(() => {
    return data.series.map((s) => {
      const valueMap = new Map(s.values.map((v) => [v.season_day, v.value]))
      return s.breakthroughs
        .map((bt) => ({
          season_day: bt.season_day,
          value: valueMap.get(bt.season_day) ?? 0,
        }))
        .filter((p) => p.value !== undefined)
    })
  }, [data])

  return (
    <div className="h-80 sm:h-96 border-2 border-[#1F5F43]/20 bg-[#FFF8DC]/80 p-4">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
          <CartesianGrid stroke="#B9D3A8" strokeDasharray="4 4" />
          <XAxis
            dataKey="season_day"
            type="number"
            domain={[data.start_day, data.end_day]}
            tick={{ fill: '#466353', fontSize: 12 }}
            stroke="#B9D3A8"
            label={{ value: '赛季天数', position: 'insideBottom', offset: -2, fill: '#466353', fontSize: 12 }}
          />
          <YAxis
            domain={[Math.max(0, Math.floor(minValue - padding)), Math.ceil(maxValue + padding)]}
            tick={{ fill: '#466353', fontSize: 12 }}
            stroke="#B9D3A8"
          />
          <Tooltip
            contentStyle={{
              backgroundColor: '#FFFFFF',
              border: '2px solid #1F5F43',
              borderRadius: 0,
            }}
            labelStyle={{ color: '#466353' }}
            itemStyle={{ color: '#173126' }}
            formatter={(value: number) => [value.toFixed(2), data.metric_label]}
            labelFormatter={(day: number) => `第 ${day} 天`}
          />
          <Legend wrapperStyle={{ color: '#466353' }} />
          {data.series.map((s, idx) => (
            <Line
              key={s.player_id}
              data={s.values}
              type="monotone"
              dataKey="value"
              name={s.player_name}
              stroke={PALETTE[idx % PALETTE.length]}
              strokeWidth={2}
              dot={false}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
          ))}
          {data.series.map((s, idx) => (
            <Scatter
              key={`bt-${s.player_id}`}
              data={scatterData[idx]}
              fill={PALETTE[idx % PALETTE.length]}
              stroke={PALETTE[idx % PALETTE.length]}
              strokeWidth={2}
              shape="star"
              legendType="none"
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function TrainingProgress() {
  const { seasons } = useSeasons()
  const currentSeason = useMemo(
    () => seasons.find((s) => s.status === 'ongoing') || seasons[0],
    [seasons]
  )

  const [teamId, setTeamId] = useState<string | null>(null)
  const [players, setPlayers] = useState<PlayerListItem[]>([])
  const [playersLoading, setPlayersLoading] = useState(true)

  const [seasonId, setSeasonId] = useState<string | undefined>(currentSeason?.id)
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [metric, setMetric] = useState('ovr')
  const [startDay, setStartDay] = useState(1)
  const [endDay, setEndDay] = useState(30)

  const [data, setData] = useState<TrainingProgressResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // 初始化赛季
  useEffect(() => {
    if (currentSeason?.id && !seasonId) {
      setSeasonId(currentSeason.id)
      const currentDay = currentSeason.current_day || 30
      setEndDay(currentDay)
      setStartDay(Math.max(1, currentDay - 30))
    }
  }, [currentSeason, seasonId])

  // 获取我的球队和球员列表
  useEffect(() => {
    const init = async () => {
      try {
        setPlayersLoading(true)
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data) return
        const tid = teamRes.data.id
        setTeamId(tid)

        const playersRes = await api.get<{ items: PlayerListItem[]; total: number }>(
          `/teams/${tid}/players?page=1&page_size=100`
        )
        if (playersRes.success && playersRes.data) {
          const list = playersRes.data.items
            .filter((p) => p.team_id === tid)
            .sort((a, b) => b.ovr - a.ovr)
          setPlayers(list)
          setSelectedIds(list.slice(0, 3).map((p) => p.id))
        }
      } catch (err) {
        console.error(err)
      } finally {
        setPlayersLoading(false)
      }
    }
    init()
  }, [])

  // 获取成长曲线
  useEffect(() => {
    if (!teamId || !seasonId || selectedIds.length === 0) return

    const fetch = async () => {
      try {
        setLoading(true)
        setError(null)
        const params = new URLSearchParams()
        params.append('season_id', seasonId)
        selectedIds.forEach((id) => params.append('player_ids', id))
        params.append('metric', metric)
        params.append('start_day', String(startDay))
        params.append('end_day', String(endDay))

        const res = await api.get<TrainingProgressResponse>(
          `/training/teams/${teamId}/progress?${params.toString()}`
        )
        if (res.success) {
          setData(res.data)
        } else {
          setError(res.message || '获取数据失败')
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '请求失败')
      } finally {
        setLoading(false)
      }
    }

    fetch()
  }, [teamId, seasonId, selectedIds, metric, startDay, endDay])

  const selectedSeason = seasons.find((s) => s.id === seasonId)
  const maxDay = selectedSeason?.current_day || 100

  return (
    <TrainingPageShell title="球员成长曲线对比" subtitle="对比球员能力或 OVR 的训练变化趋势">
      <div className="space-y-4">
        {/* 控制栏 */}
        <div className="flex flex-col xl:flex-row gap-4 p-4 border-2 border-[#1F5F43]/20 bg-[#FFF8DC]/80">
          <PlayerSelect players={players} selected={selectedIds} onChange={setSelectedIds} />

          <div className="flex flex-col sm:flex-row gap-4 shrink-0">
            <div className="flex flex-col gap-3">
              <MetricSelect value={metric} onChange={setMetric} />
              <div className="flex items-center gap-2">
                <label className="text-sm text-[#466353] whitespace-nowrap">赛季</label>
                <select
                  value={seasonId || ''}
                  onChange={(e) => setSeasonId(e.target.value)}
                  className="bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#173126] text-sm px-3 py-2 focus:outline-none focus:border-[#1F5F43]"
                >
                  {seasons.map((s) => (
                    <option key={s.id} value={s.id}>
                      第 {s.season_number} 赛季
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex flex-col gap-3">
              <RangeInput label="起始天" value={startDay} min={1} max={endDay} onChange={setStartDay} />
              <RangeInput label="结束天" value={endDay} min={startDay} max={maxDay} onChange={setEndDay} />
            </div>
          </div>
        </div>

        {/* 提示 */}
        {selectedIds.length === 0 && !playersLoading && (
          <div className="flex items-center gap-2 text-sm text-[#466353]">
            请至少选择一名球员
          </div>
        )}

        {/* 加载与错误 */}
        {loading && (
          <div className="space-y-2 animate-pulse">
            <div className="h-8 bg-[#FFF8DC]/80 w-1/3" />
            <div className="h-80 bg-[#FFF8DC]/80" />
          </div>
        )}
        {error && (
          <div className="p-4 border border-[#FF6F59]/40 bg-[#FF6F59]/10 text-[#FF6F59] text-sm">
            {error}
          </div>
        )}

        {/* 图表 */}
        {!loading && data && data.series.length > 0 && (
          <ProgressChart data={data} />
        )}

        {!loading && data && data.series.length === 0 && (
          <div className="text-center py-16 border-2 border-dashed border-[#1F5F43]/20 bg-[#FFF8DC]/50">
            <p className="text-[#466353]">所选球员在该时间段内暂无训练数据</p>
          </div>
        )}
      </div>
    </TrainingPageShell>
  )
}
