import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, X } from 'lucide-react'
import {
  Tree,
  TrendingUp,
  Sparkles,
  Check,
  Cancel,
  Loader,
} from '../../components/ui/pixel-icons'
import api from '../../api/client'
import type { ContractPreview } from '../../types/player'

interface AcademyPlayer {
  academy_player_id: string
  player_id: string
  name: string
  race: string
  avatar_url?: string
  position: string
  age: number
  ovr: number
  potential_letter: string
  growth_speed: string
  joined_day: number
  last_trained_day: number | null
}

const growthSpeedLabels: Record<string, string> = {
  fast: '快',
  normal: '中',
  slow: '慢',
}

const growthSpeedClasses: Record<string, string> = {
  fast: 'text-emerald-400 border-emerald-400/30 bg-emerald-500/10',
  normal: 'text-yellow-400 border-yellow-400/30 bg-yellow-500/10',
  slow: 'text-[#4B4B6A] border-[#2D2D44]',
}

const positionColors: Record<string, string> = {
  FW: 'bg-red-500 text-white',
  MF: 'bg-emerald-500 text-white',
  DF: 'bg-blue-500 text-white',
  GK: 'bg-amber-500 text-black',
}

export default function YouthAcademy() {
  const [players, setPlayers] = useState<AcademyPlayer[]>([])
  const [capacity, setCapacity] = useState(8)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null)
  const [signingId, setSigningId] = useState<string | null>(null)
  const [preview, setPreview] = useState<ContractPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [signSuccess, setSignSuccess] = useState<string | null>(null)

  const fetchAcademy = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setError('无法获取球队信息')
        return
      }
      const res = await api.getYouthAcademy(teamRes.data.id)
      if (res.success && res.data) {
        setPlayers(res.data.players)
        setCapacity(res.data.capacity)
      } else {
        setPlayers([])
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchAcademy()
  }, [fetchAcademy])

  const openSignModal = async (player: AcademyPlayer) => {
    setSigningId(player.academy_player_id)
    setPreview(null)
    setPreviewError(null)
    setSignSuccess(null)
    setPreviewLoading(true)

    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setPreviewError('无法获取球队信息')
        setPreviewLoading(false)
        return
      }
      const teamId = teamRes.data.id

      // 计算建议工资（ROOKIE = 0.70 折扣）
      // 先获取球员详情来计算建议工资
      const playerRes = await api.get<{ wage: number }>(`/players/${player.player_id}`)
      const recommendedWage = playerRes.success && playerRes.data ? Math.round(playerRes.data.wage * 0.70) : 1000

      const res = await api.previewYouthSigning(player.academy_player_id, {
        team_id: teamId,
        years: 2,
        wage: recommendedWage,
        squad_role: 'youngster',
      })
      if (res.success && res.data) {
        setPreview(res.data)
      } else {
        setPreviewError(res.message || '预览失败')
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : '预览请求失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleSign = async () => {
    if (!signingId || !preview) return
    const player = players.find(p => p.academy_player_id === signingId)
    if (!player) return

    setPreviewLoading(true)
    setPreviewError(null)
    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setPreviewError('无法获取球队信息')
        setPreviewLoading(false)
        return
      }
      const teamId = teamRes.data.id

      const res = await api.signYouthPlayer(signingId, {
        team_id: teamId,
        years: 2,
        wage: preview.offered_wage,
        squad_role: 'youngster',
      })
      if (res.success && res.data) {
        setSignSuccess(`成功签约 ${player.name}！`)
        fetchAcademy()
      } else {
        setPreviewError(res.message || '签约失败')
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : '签约请求失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleRelease = async (academyPlayerId: string) => {
    if (!confirm('确定要放弃这名青训球员吗？他将进入自由市场。')) return
    try {
      const res = await api.releaseYouthPlayer(academyPlayerId)
      if (res.success) {
        fetchAcademy()
      } else {
        alert(res.message || '放弃失败')
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : '放弃请求失败')
    }
  }

  const closeModal = () => {
    setSigningId(null)
    setPreview(null)
    setPreviewError(null)
    setSignSuccess(null)
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">青训营</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">观察年轻球员成长，赛季末未签约会进入自由市场</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/youth/young-players" className="btn-secondary text-sm">年轻球员</Link>
        </div>
      </div>

      {/* 青训概况 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Tree className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">在营人数</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">{players.length}/{capacity}</p>
          <p className="text-xs text-[#4B4B6A] mt-1">每赛季刷新 2 次</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">平均 OVR</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">
            {players.length > 0 ? Math.round(players.reduce((s, p) => s + p.ovr, 0) / players.length) : 0}
          </p>
          <p className="text-xs text-[#4B4B6A] mt-1">在营球员平均值</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">高潜球员</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">
            {players.filter(p => ['S', 'A', 'B'].includes(p.potential_letter)).length}
          </p>
          <p className="text-xs text-[#4B4B6A] mt-1">潜力 S/A/B 档</p>
        </div>
      </div>

      {/* 加载 & 错误 */}
      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
          <span className="ml-2 text-sm text-[#8B8BA7]">加载中...</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* 球员列表 */}
      {!loading && !error && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">在营球员</h3>
            <span className="text-xs text-[#4B4B6A]">点击卡片查看成长曲线</span>
          </div>

          {players.length === 0 ? (
            <div className="text-center py-8 text-[#8B8BA7]">
              <p className="text-sm">暂无在营球员，等待下次刷新</p>
            </div>
          ) : (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {players.map((p) => (
                <div
                  key={p.academy_player_id}
                  className={clsx(
                    'bg-[#0A0A0F] border-2 p-4 transition-all cursor-pointer',
                    selectedPlayer === p.academy_player_id ? 'border-[#0D7377] shadow-pixel-green' : 'border-[#2D2D44] hover:border-[#0D7377]/50'
                  )}
                  onClick={() => setSelectedPlayer(selectedPlayer === p.academy_player_id ? null : p.academy_player_id)}
                >
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <h4 className="font-bold text-white">{p.name}</h4>
                      <p className="text-xs text-[#8B8BA7]">{p.age}岁 · 入营第{p.joined_day}天</p>
                    </div>
                    <div className="flex flex-col items-end gap-1">
                      <span className={clsx('text-xs px-2 py-0.5 font-bold', positionColors[p.position] || 'bg-[#2D2D44] text-white')}>
                        {p.position}
                      </span>
                      <span className={clsx('text-xs px-2 py-0.5 font-bold border', growthSpeedClasses[p.growth_speed] || growthSpeedClasses.normal)}>
                        {growthSpeedLabels[p.growth_speed] || p.growth_speed}速成长
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center justify-between mb-3">
                    <span className="text-xs text-[#8B8BA7]">OVR {p.ovr} · 潜力 {p.potential_letter}</span>
                    <span className="text-xs text-[#4B4B6A]">
                      {p.last_trained_day ? `最近训练: 第${p.last_trained_day}天` : '尚未训练'}
                    </span>
                  </div>

                  {/* 操作按钮 */}
                  <div className="flex gap-2 pt-3 border-t-2 border-[#2D2D44]">
                    <button
                      onClick={(e) => { e.stopPropagation(); openSignModal(p) }}
                      className="flex-1 px-3 py-2 bg-emerald-500/20 text-emerald-400 text-xs font-bold border-2 border-emerald-500/30 hover:bg-emerald-500/30 transition-colors"
                    >
                      <Check className="w-3 h-3 inline mr-1" />
                      签约
                    </button>
                    <button
                      onClick={(e) => { e.stopPropagation(); handleRelease(p.academy_player_id) }}
                      className="flex-1 px-3 py-2 bg-red-500/20 text-red-400 text-xs font-bold border-2 border-red-500/30 hover:bg-red-500/30 transition-colors"
                    >
                      <Cancel className="w-3 h-3 inline mr-1" />
                      放弃
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 签约弹窗 */}
      {signingId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-lg">
            <div className="flex items-center justify-between p-4 border-b-2 border-[#2D2D44]">
              <h3 className="text-lg font-bold text-white">
                {signSuccess ? '签约成功' : '签约青训球员'}
              </h3>
              <button onClick={closeModal} className="text-[#8B8BA7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {previewLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
                </div>
              )}

              {previewError && (
                <div className="flex items-center gap-2 p-3 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
                  <AlertTriangle className="w-4 h-4" />
                  {previewError}
                </div>
              )}

              {signSuccess && (
                <div className="space-y-3">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <Check className="w-5 h-5" />
                    <span className="font-bold">{signSuccess}</span>
                  </div>
                  <button
                    onClick={closeModal}
                    className="w-full py-2 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                  >
                    确定
                  </button>
                </div>
              )}

              {preview && !signSuccess && (
                <div className="space-y-3">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">合同类型</span>
                      <span className="text-emerald-400 font-bold">新人合同 (ROOKIE)</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">周薪</span>
                      <span className="text-white">{preview.offered_wage}万</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">建议周薪</span>
                      <span className="text-white">{preview.recommended_wage}万</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">薪资满意度</span>
                      <span className={preview.wage_ratio >= 1 ? 'text-emerald-400' : preview.wage_ratio >= 0.8 ? 'text-yellow-400' : 'text-red-400'}>
                        {Math.round(preview.wage_ratio * 100)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">球员反应</span>
                      <span className="text-white">{preview.visible_reaction}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">签约后薪资帽占比</span>
                      <span className="text-white">{Math.round(preview.wage_cap_after_pct * 100)}%</span>
                    </div>
                  </div>

                  {preview.warnings.length > 0 && (
                    <div className="space-y-1">
                      {preview.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-yellow-400 flex items-start gap-1">
                          <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5" />
                          {w}
                        </p>
                      ))}
                    </div>
                  )}

                  {!preview.can_submit && (
                    <div className="p-2 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-xs">
                      当前条件不满足签约要求
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeModal}
                      className="flex-1 py-2 bg-[#2D2D44] hover:bg-[#3D3D5C] text-white text-sm font-bold border-2 border-[#2D2D44] transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSign}
                      disabled={previewLoading || !preview.can_submit}
                      className="flex-1 py-2 bg-[#0D7377] hover:bg-[#0A5A5D] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                    >
                      {previewLoading ? '签约中...' : '确认签约'}
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
