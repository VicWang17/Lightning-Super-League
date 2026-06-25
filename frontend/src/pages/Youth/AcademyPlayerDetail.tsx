import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams, Link } from 'react-router-dom'
import { ChevronLeft, Loader, TrendingUp } from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import { PageHeader } from '../../components/ui/PageHeader'
import { YouthTabs } from '../../components/youth/YouthTabs'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'
import Avatar from '../../components/ui/Avatar'
import Badge from '../../components/ui/Badge'
import { ContractModal } from '../../components/players/ContractModal'
import { useYouthAcademy } from '../../hooks/useYouthAcademy'
import { useAcademyGrowth } from '../../hooks/useAcademyGrowth'
import type { Player, PlayerAbility } from '../../types/player'

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
  FW: 'bg-[#FF6F59] text-[#F8FFD2]',
  MF: 'bg-[#1F5F43] text-[#173126]',
  DF: 'bg-[#59C7EE] text-[#173126]',
  GK: 'bg-[#FFC247] text-[#173126]',
}

const ABILITY_GROUPS: { label: string; keys: { key: keyof PlayerAbility; label: string }[] }[] = [
  {
    label: '进攻',
    keys: [
      { key: 'sho', label: '射门' },
      { key: 'pas', label: '传球' },
      { key: 'dri', label: '盘带' },
      { key: 'fin', label: '终结' },
      { key: 'cro', label: '传中' },
      { key: 'hea', label: '头球' },
    ],
  },
  {
    label: '身体',
    keys: [
      { key: 'spd', label: '速度' },
      { key: 'acc', label: '爆发力' },
      { key: 'str', label: '力量' },
      { key: 'sta', label: '体能' },
      { key: 'bal', label: '平衡' },
    ],
  },
  {
    label: '防守 / 技术',
    keys: [
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
    keys: [
      { key: 'sav', label: '扑救' },
      { key: 'ref', label: '反应' },
      { key: 'pos', label: '站位' },
      { key: 'rus', label: '出击' },
    ],
  },
  {
    label: '定位球',
    keys: [
      { key: 'fk', label: '任意球' },
      { key: 'pk', label: '点球' },
    ],
  },
]

function GrowthChart({ data }: { data: { season_day: number; ovr: number }[] }) {
  const values = data.map((d) => d.ovr)
  const maxOvr = Math.max(...values)
  const minOvr = Math.min(...values)
  const range = Math.max(maxOvr - minOvr, 1)

  return (
    <div className="flex items-end gap-1 h-32 px-1">
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
                isLast ? 'bg-[#B9EF3F]' : 'bg-[#1F5F43]'
              }`}
              style={{ height: `${heightPct}%` }}
            />
            <span className="text-[9px] text-[#466353]">{point.season_day}</span>
            <div className="absolute -top-7 left-1/2 -translate-x-1/2 opacity-0 group-hover:opacity-100 transition-opacity bg-[#FFF8DC]/90 border border-[#1F5F43]/20 px-2 py-1 text-xs whitespace-nowrap z-10">
              第{point.season_day}天: OVR {point.ovr}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default function AcademyPlayerDetail() {
  const { academyPlayerId } = useParams<{ academyPlayerId: string }>()
  const navigate = useNavigate()
  const { data: academyData, rosterFull, loading: academyLoading, error: academyError, refetch } = useYouthAcademy()
  const { data: growthData, loading: growthLoading } = useAcademyGrowth(academyPlayerId ?? null)

  const [player, setPlayer] = useState<Player | null>(null)
  const [playerLoading, setPlayerLoading] = useState(false)
  const [contractOpen, setContractOpen] = useState(false)
  const [releasing, setReleasing] = useState(false)

  const academyPlayer = useMemo(() => {
    if (!academyData || !academyPlayerId) return null
    return academyData.players.find((p) => p.academy_player_id === academyPlayerId) ?? null
  }, [academyData, academyPlayerId])

  useEffect(() => {
    if (!academyPlayer?.player_id) return
    let cancelled = false
    setPlayerLoading(true)
    api.get<Player>(`/players/${academyPlayer.player_id}`)
      .then((res) => {
        if (!cancelled && res.success && res.data) {
          setPlayer(res.data)
        }
      })
      .catch(() => {})
      .finally(() => {
        if (!cancelled) setPlayerLoading(false)
      })
    return () => { cancelled = true }
  }, [academyPlayer?.player_id])

  const handleRelease = async () => {
    if (!academyPlayerId || !confirm('确定要放弃这名青训球员吗？他将进入新人市场。')) return
    setReleasing(true)
    try {
      const res = await api.releaseYouthPlayer(academyPlayerId)
      if (res.success) {
        refetch()
        navigate('/youth/academy')
      } else {
        alert(res.message || '放弃失败')
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : '放弃请求失败')
    } finally {
      setReleasing(false)
    }
  }

  const handleContractSuccess = () => {
    setContractOpen(false)
    refetch()
    navigate('/youth/academy')
  }

  if (academyLoading) {
    return (
      <div className="max-w-[1400px] p-8 text-center text-[#466353]">
        <Loader className="w-6 h-6 animate-spin mx-auto mb-2" />
        加载青训数据中...
      </div>
    )
  }

  if (academyError || !academyPlayer) {
    return (
      <div className="max-w-[1400px] p-8">
        <div className="p-4 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">
          {academyError || '未找到该青训球员'}
        </div>
      </div>
    )
  }

  const abilities = player?.abilities

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center gap-3">
        <Link
          to="/youth/academy"
          className="inline-flex items-center gap-1 text-sm text-[#466353] hover:text-[#173126] transition-colors"
        >
          <ChevronLeft className="w-4 h-4" />
          返回青训营
        </Link>
      </div>

      <PageHeader
        title={academyPlayer.name}
        subtitle={`${academyPlayer.age} 岁 · 入营第 ${academyPlayer.joined_day} 天 · 潜力 ${academyPlayer.potential_letter}`}
      />

      <YouthTabs />

      {rosterFull && (
        <div className="p-3 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30">
          <p className="text-sm text-[#FF6F59]">
            一线队已满 18 人，无法签约新球员。
          </p>
        </div>
      )}

      {/* 头部信息卡 */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row sm:items-center gap-4">
            <Avatar
              src={academyPlayer.avatar_url ? `/${academyPlayer.avatar_url}` : undefined}
              name={academyPlayer.name}
              size="lg"
            />
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className={`text-xs px-2 py-0.5 font-bold ${positionColors[academyPlayer.position] || 'bg-[#F8FFD2] text-[#173126]'}`}>
                  {academyPlayer.position}
                </span>
                <Badge variant={growthSpeedVariants[academyPlayer.growth_speed] || 'default'} size="sm">
                  {growthSpeedLabels[academyPlayer.growth_speed] || academyPlayer.growth_speed}速成长
                </Badge>
              </div>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-3">
                <div className="p-2 bg-[#FFF8DC]/80 text-center">
                  <p className="text-xs text-[#466353]">OVR</p>
                  <p className="text-xl font-bold text-[#173126] stat-number">{academyPlayer.ovr}</p>
                </div>
                <div className="p-2 bg-[#FFF8DC]/80 text-center">
                  <p className="text-xs text-[#466353]">潜力</p>
                  <p className={`text-xl font-bold ${
                    academyPlayer.potential_letter === 'S' ? 'text-[#C77A00]' :
                    academyPlayer.potential_letter === 'A' ? 'text-[#1F5F43]' :
                    'text-[#173126]'
                  } stat-number`}>
                    {academyPlayer.potential_letter}
                  </p>
                </div>
                <div className="p-2 bg-[#FFF8DC]/80 text-center">
                  <p className="text-xs text-[#466353]">年龄</p>
                  <p className="text-xl font-bold text-[#173126] stat-number">{academyPlayer.age}</p>
                </div>
                <div className="p-2 bg-[#FFF8DC]/80 text-center">
                  <p className="text-xs text-[#466353]">入营天数</p>
                  <p className="text-xl font-bold text-[#173126] stat-number">{academyPlayer.joined_day}</p>
                </div>
                <div className="p-2 bg-[#FFF8DC]/80 text-center">
                  <p className="text-xs text-[#466353]">最近训练</p>
                  <p className="text-sm font-bold text-[#173126]">
                    {academyPlayer.last_trained_day ? `第${academyPlayer.last_trained_day}天` : '未训练'}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex flex-col gap-2 sm:w-32">
              <button
                onClick={() => setContractOpen(true)}
                disabled={rosterFull || playerLoading || !player}
                className="px-4 py-2 bg-[#B9EF3F] text-[#173126] text-xs font-black border-2 border-[#1F5F43] hover:bg-[#FFC247] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                {playerLoading ? '加载中...' : rosterFull ? '阵容已满' : '签约'}
              </button>
              <button
                onClick={handleRelease}
                disabled={releasing}
                className="px-4 py-2 bg-[#FF6F59]/15 text-[#FF6F59] text-xs font-black border-2 border-[#FF6F59]/30 hover:bg-[#FF6F59]/30 disabled:opacity-40 transition-colors"
              >
                {releasing ? '处理中...' : '放弃'}
              </button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 能力值 */}
      <Card>
        <CardHeader title="能力值" />
        <CardContent className="p-4 space-y-5">
          {playerLoading ? (
            <div className="text-center py-8 text-[#466353]">
              <Loader className="w-5 h-5 animate-spin mx-auto mb-2" />
              加载能力值...
            </div>
          ) : !abilities ? (
            <p className="text-center text-sm text-[#466353] py-8">暂无能力值数据</p>
          ) : (
            ABILITY_GROUPS.map((group) => (
              <div key={group.label}>
                <h4 className="text-sm font-black text-[#1F5F43] mb-2">{group.label}</h4>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2">
                  {group.keys.map(({ key, label }) => {
                    const value = abilities[key]
                    if (value === undefined || value === null) return null
                    return (
                      <div
                        key={key}
                        className="p-2 bg-[#FFF8DC]/80 text-center border border-[#1F5F43]/10"
                      >
                        <p className="text-[10px] text-[#466353]">{label}</p>
                        <p className="text-sm font-bold text-[#173126] pixel-number">{value}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>

      {/* 成长情况 */}
      <Card>
        <CardHeader title="成长情况" />
        <CardContent className="p-4">
          {growthLoading ? (
            <div className="text-center py-8 text-[#466353]">
              <Loader className="w-5 h-5 animate-spin mx-auto mb-2" />
              加载成长曲线...
            </div>
          ) : growthData.length === 0 ? (
            <p className="text-center text-sm text-[#466353] py-8">暂无成长记录</p>
          ) : (
            <>
              <div className="flex items-center gap-2 mb-4">
                <TrendingUp className="w-4 h-4 text-[#1F5F43]" />
                <span className="text-sm font-bold text-[#173126]">OVR 成长曲线</span>
                <span className="text-xs text-[#466353]">
                  OVR {Math.min(...growthData.map((d) => d.ovr))} → {Math.max(...growthData.map((d) => d.ovr))}
                </span>
              </div>
              <GrowthChart data={growthData} />
            </>
          )}
        </CardContent>
      </Card>

      {contractOpen && player && (
        <ContractModal
          player={player}
          teamId={academyData?.team_id ?? ''}
          contractType="ROOKIE"
          onClose={() => setContractOpen(false)}
          onSuccess={handleContractSuccess}
        />
      )}
    </div>
  )
}
