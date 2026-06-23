import { useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader, TrendingUp, Users, Zap, Wallet } from 'lucide-react'
import { api } from '../../api/client'
import type { Player } from '../../types/player'
import { PageHeader } from '../../components/ui/PageHeader'
import { YouthTabs } from '../../components/youth/YouthTabs'
import { Card, CardHeader, CardContent } from '../../components/ui/Card'
import Badge from '../../components/ui/Badge'
import Avatar from '../../components/ui/Avatar'
import { ContractModal } from '../../components/players/ContractModal'
import { useYouthAcademy } from '../../hooks/useYouthAcademy'
import { useAcademyGrowth } from '../../hooks/useAcademyGrowth'

const growthSpeedLabels: Record<string, string> = {
  fast: '快',
  normal: '中',
  slow: '慢',
}

const growthSpeedVariants: Record<string, 'success' | 'warning' | 'default'> = {
  fast: 'success',
  normal: 'warning',
  slow: 'default',
}

const positionColors: Record<string, string> = {
  FW: 'bg-red-500 text-white',
  MF: 'bg-emerald-500 text-white',
  DF: 'bg-blue-500 text-white',
  GK: 'bg-amber-500 text-black',
}

const potentialOrder: Record<string, number> = {
  S: 5, A: 4, B: 3, C: 2, D: 1,
}

const speedOrder: Record<string, number> = {
  fast: 3, normal: 2, slow: 1,
}

type SortKey = 'ovr' | 'potential' | 'age' | 'growth' | 'joined'

interface ContractModalState {
  open: boolean
  player: Player | null
}

function formatPct(value?: number) {
  if (value === undefined || value === null) return '-'
  return `${(value * 100).toFixed(1)}%`
}

function getInvestmentLevel(pct?: number) {
  if (pct === undefined || pct === null) return { label: '未知', variant: 'default' as const }
  if (pct <= 0.1) return { label: '低投入', variant: 'default' as const }
  if (pct <= 0.17) return { label: '中投入', variant: 'warning' as const }
  return { label: '高投入', variant: 'success' as const }
}

function GrowthPanel({ academyPlayerId }: { academyPlayerId: string }) {
  const { data, loading } = useAcademyGrowth(academyPlayerId)

  if (loading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader className="w-5 h-5 text-[#0D7377] animate-spin" />
      </div>
    )
  }

  if (data.length === 0) {
    return (
      <div className="py-4 text-center text-xs text-[#8B8BA7]">
        暂无成长记录
      </div>
    )
  }

  const ovrValues = data.map(d => d.ovr)
  const maxOvr = Math.max(...ovrValues)
  const minOvr = Math.min(...ovrValues)
  const range = Math.max(maxOvr - minOvr, 1)

  return (
    <div className="mt-4 pt-4 border-t-2 border-[#2D2D44]">
      <div className="flex items-center gap-2 mb-3">
        <TrendingUp className="w-4 h-4 text-[#0D7377]" />
        <span className="text-sm font-medium text-white">成长曲线</span>
        <span className="text-xs text-[#8B8BA7]">
          OVR {minOvr} → {maxOvr}
        </span>
      </div>
      <div className="flex items-end gap-1 h-24 px-1">
        {data.map((point, idx) => {
          const isLast = idx === data.length - 1
          const heightPct = ((point.ovr - minOvr) / range) * 70 + 30
          return (
            <div
              key={`${point.season_day}-${idx}`}
              className="flex-1 flex flex-col items-center gap-1 group relative"
            >
              <div
                className={`w-full max-w-[18px] transition-all ${
                  isLast ? 'bg-[#C6F135]' : 'bg-[#0D7377]'
                }`}
                style={{ height: `${heightPct}%` }}
              />
              <span className="text-[9px] text-[#8B8BA7]">{point.season_day}</span>
              <div className="absolute -top-7 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-[#1E1E2D] border border-[#2D2D44] px-2 py-1 text-xs whitespace-nowrap z-10">
                第{point.season_day}天: OVR {point.ovr}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function YouthAcademy() {
  const navigate = useNavigate()
  const { data, budget, rosterFull, loading, error, refetch } = useYouthAcademy()
  const [sortKey, setSortKey] = useState<SortKey>('ovr')
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [contractModal, setContractModal] = useState<ContractModalState>({ open: false, player: null })
  const [signingId, setSigningId] = useState<string | null>(null)

  const players = useMemo(() => {
    if (!data) return []
    const list = [...data.players]
    list.sort((a, b) => {
      switch (sortKey) {
        case 'ovr':
          return b.ovr - a.ovr
        case 'potential':
          return potentialOrder[b.potential_letter] - potentialOrder[a.potential_letter]
        case 'age':
          return a.age - b.age
        case 'growth':
          return speedOrder[b.growth_speed] - speedOrder[a.growth_speed]
        case 'joined':
          return a.joined_day - b.joined_day
        default:
          return 0
      }
    })
    return list
  }, [data, sortKey])

  const avgOvr = useMemo(() => {
    if (!data || data.players.length === 0) return 0
    return Math.round(data.players.reduce((s, p) => s + p.ovr, 0) / data.players.length)
  }, [data])

  const highPotentialCount = useMemo(() => {
    if (!data) return 0
    return data.players.filter(p => ['S', 'A', 'B'].includes(p.potential_letter)).length
  }, [data])

  const investment = useMemo(() => getInvestmentLevel(budget?.youth_pct), [budget])

  const handleOpenSign = useCallback(async (academyPlayer: typeof players[number]) => {
    setSigningId(academyPlayer.academy_player_id)
    try {
      const res = await api.get<Player>(`/players/${academyPlayer.player_id}`)
      if (res.success && res.data) {
        setContractModal({ open: true, player: res.data })
      }
    } catch (err) {
      // 失败时静默处理，ContractModal 不会打开
    } finally {
      setSigningId(null)
    }
  }, [])

  const handleRelease = useCallback(async (academyPlayerId: string) => {
    if (!confirm('确定要放弃这名青训球员吗？他将进入新人市场。')) return
    try {
      const res = await api.releaseYouthPlayer(academyPlayerId)
      if (res.success) {
        refetch()
      } else {
        alert(res.message || '放弃失败')
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : '放弃请求失败')
    }
  }, [refetch])

  const handleContractSuccess = useCallback(() => {
    setContractModal({ open: false, player: null })
    refetch()
  }, [refetch])

  const toggleSelected = useCallback((id: string) => {
    setSelectedId(prev => (prev === id ? null : id))
  }, [])

  if (loading) {
    return (
      <div className="max-w-[1400px] p-8 text-center text-[#8B8BA7]">
        <Loader className="w-6 h-6 animate-spin mx-auto mb-2" />
        加载青训数据中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-[1400px] p-8">
        <div className="p-4 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-[#8B8BA7] hover:text-white transition-colors"
      >
        返回上一页
      </button>

      <PageHeader
        title="青训营"
        subtitle="17-18 岁 Rookie · 赛季末未签约将流入新人市场"
      />

      <YouthTabs />

      {/* 青训概况 */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[#8B8BA7] flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" />
                在营人数
              </span>
            </div>
            <p className="text-2xl font-bold text-white stat-number">
              {data?.count ?? 0}/{data?.capacity ?? 8}
            </p>
            <p className="text-xs text-[#4B4B6A] mt-1">每赛季第 4 / 8 天刷新</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[#8B8BA7] flex items-center gap-1.5">
                <Zap className="w-3.5 h-3.5" />
                平均 OVR
              </span>
            </div>
            <p className="text-2xl font-bold text-white stat-number">{avgOvr}</p>
            <p className="text-xs text-[#4B4B6A] mt-1">在营球员平均值</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[#8B8BA7] flex items-center gap-1.5">
                <TrendingUp className="w-3.5 h-3.5" />
                高潜球员
              </span>
            </div>
            <p className="text-2xl font-bold text-white stat-number">{highPotentialCount}</p>
            <p className="text-xs text-[#4B4B6A] mt-1">潜力 S/A/B 档</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs text-[#8B8BA7] flex items-center gap-1.5">
                <Wallet className="w-3.5 h-3.5" />
                青训投入
              </span>
              <Badge variant={investment.variant} size="sm">{investment.label}</Badge>
            </div>
            <p className="text-2xl font-bold text-white stat-number">{formatPct(budget?.youth_pct)}</p>
            <p className="text-xs text-[#4B4B6A] mt-1">本赛季预算分配</p>
          </CardContent>
        </Card>
      </div>

      {/* roster 满提示 */}
      {rosterFull && (
        <div className="p-3 bg-red-500/10 border-2 border-red-500/30">
          <p className="text-sm text-red-400">
            一线队已满 18 人，无法签约新球员。请先清理阵容或等待球员离队。
          </p>
        </div>
      )}

      {/* 工具栏 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-wrap items-center gap-3">
            <span className="text-sm text-[#8B8BA7]">排序：</span>
            {([
              { key: 'ovr', label: 'OVR' },
              { key: 'potential', label: '潜力' },
              { key: 'age', label: '年龄' },
              { key: 'growth', label: '成长速度' },
              { key: 'joined', label: '入营时间' },
            ] as { key: SortKey; label: string }[]).map((opt) => (
              <button
                key={opt.key}
                onClick={() => setSortKey(opt.key)}
                className={`px-3 py-1.5 text-xs border-2 transition-colors ${
                  sortKey === opt.key
                    ? 'border-[#0D7377] text-[#0D7377] bg-[#0D7377]/10'
                    : 'border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* 球员列表 */}
      <Card>
        <CardHeader
          title="在营球员"
          subtitle="点击卡片查看成长曲线"
          action={<span className="text-xs text-[#4B4B6A]">共 {players.length} 人</span>}
        />
        <CardContent>
          {players.length === 0 ? (
            <div className="text-center py-12 text-[#8B8BA7]">
              <p className="text-sm mb-2">暂无在营球员</p>
              <p className="text-xs text-[#4B4B6A]">
                青训营将在赛季第 4 天和第 8 天自动刷新，最多补满 8 人
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {players.map((p) => {
                const isSelected = selectedId === p.academy_player_id
                const isSigning = signingId === p.academy_player_id
                return (
                  <div
                    key={p.academy_player_id}
                    className={`bg-[#0A0A0F] border-2 p-4 transition-all cursor-pointer ${
                      isSelected ? 'border-[#0D7377] shadow-pixel-green' : 'border-[#2D2D44] hover:border-[#0D7377]/50'
                    }`}
                    onClick={() => toggleSelected(p.academy_player_id)}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <Avatar
                          src={p.avatar_url ? `/${p.avatar_url}` : undefined}
                          name={p.name}
                          size="md"
                        />
                        <div>
                          <h4 className="font-bold text-white">{p.name}</h4>
                          <p className="text-xs text-[#8B8BA7]">{p.age}岁 · 入营第{p.joined_day}天</p>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1.5">
                        <span className={`text-xs px-2 py-0.5 font-bold ${positionColors[p.position] || 'bg-[#2D2D44] text-white'}`}>
                          {p.position}
                        </span>
                        <Badge variant={growthSpeedVariants[p.growth_speed] || 'default'} size="sm">
                          {growthSpeedLabels[p.growth_speed] || p.growth_speed}速成长
                        </Badge>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-2 mb-4">
                      <div className="p-2 bg-[#1E1E2D] text-center">
                        <p className="text-xs text-[#8B8BA7]">OVR</p>
                        <p className="text-lg font-bold text-white stat-number">{p.ovr}</p>
                      </div>
                      <div className="p-2 bg-[#1E1E2D] text-center">
                        <p className="text-xs text-[#8B8BA7]">潜力</p>
                        <p className={`text-lg font-bold ${
                          p.potential_letter === 'S' ? 'text-yellow-400' :
                          p.potential_letter === 'A' ? 'text-[#0D7377]' :
                          'text-white'
                        } stat-number`}>
                          {p.potential_letter}
                        </p>
                      </div>
                      <div className="p-2 bg-[#1E1E2D] text-center">
                        <p className="text-xs text-[#8B8BA7]">最近训练</p>
                        <p className="text-sm font-medium text-white">
                          {p.last_trained_day ? `第${p.last_trained_day}天` : '未训练'}
                        </p>
                      </div>
                    </div>

                    {/* 操作按钮 */}
                    <div className="flex gap-2">
                      <button
                        onClick={(e) => { e.stopPropagation(); handleOpenSign(p) }}
                        disabled={isSigning || rosterFull}
                        className="flex-1 px-3 py-2 bg-emerald-500/20 text-emerald-400 text-xs font-bold border-2 border-emerald-500/30 hover:bg-emerald-500/30 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                      >
                        {isSigning ? '加载中...' : rosterFull ? '阵容已满' : '签约'}
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleRelease(p.academy_player_id) }}
                        className="flex-1 px-3 py-2 bg-red-500/20 text-red-400 text-xs font-bold border-2 border-red-500/30 hover:bg-red-500/30 transition-colors"
                      >
                        放弃
                      </button>
                    </div>

                    {isSelected && <GrowthPanel academyPlayerId={p.academy_player_id} />}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* 复用全局 ContractModal */}
      {contractModal.open && contractModal.player && (
        <ContractModal
          player={contractModal.player}
          teamId={data?.team_id ?? ''}
          contractType="ROOKIE"
          onClose={() => setContractModal({ open: false, player: null })}
          onSuccess={handleContractSuccess}
        />
      )}
    </div>
  )
}
