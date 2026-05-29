import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, X } from 'lucide-react'
import {
  Check,
  Clock,
  WarningDiamond,
  Loader,
} from '../../components/ui/pixel-icons'
import api from '../../api/client'

interface DraftPlayer {
  pool_player_id: string
  player_id: string
  name: string
  race: string
  avatar_url?: string
  position: string
  age: number
  ovr: number
  potential_letter: string
  source_team_name: string | null
  status: string
  rank_snapshot: number
}

interface DraftResult {
  selection_id: string
  selection_order: number
  team_id: string
  team_name: string
  player_id: string
  player_name: string
  position: string
  ovr: number
  potential_letter: string
  status: string
  expires_at: string | null
}

interface TeamSelection {
  selection_id: string
  player_id: string
  name: string
  race: string
  avatar_url?: string
  position: string
  age: number
  ovr: number
  potential_letter: string
  expires_at: string | null
}

const positionColors: Record<string, string> = {
  FW: 'bg-red-500 text-white',
  MF: 'bg-emerald-500 text-white',
  DF: 'bg-blue-500 text-white',
  GK: 'bg-amber-500 text-black',
}

export default function Draft() {
  const [phase, setPhase] = useState<'loading' | 'voting' | 'result' | 'signing' | 'error'>('loading')
  const [poolId, setPoolId] = useState<string | null>(null)
  const [players, setPlayers] = useState<DraftPlayer[]>([])
  const [results, setResults] = useState<DraftResult[]>([])
  const [selections, setSelections] = useState<TeamSelection[]>([])
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [signingId, setSigningId] = useState<string | null>(null)
  const [signLoading, setSignLoading] = useState(false)

  const fetchData = useCallback(async () => {
    setPhase('loading')
    setError(null)
    try {
      // 获取球队信息
      const teamRes = await api.get<{ id: string; current_league_id?: string; name: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setError('无法获取球队信息')
        setPhase('error')
        return
      }
      const team = teamRes.data

      // 获取当前赛季
      const seasonRes = await api.getCurrentSeason()
      if (!seasonRes.success || !seasonRes.data) {
        setError('无法获取赛季信息')
        setPhase('error')
        return
      }
      const season = seasonRes.data

      if (!team.current_league_id) {
        setError('球队尚未加入联赛')
        setPhase('error')
        return
      }

      // 获取选秀池
      const poolRes = await api.getDraftPool(team.current_league_id, season.id)
      if (poolRes.success && poolRes.data && poolRes.data.pool_id) {
        setPoolId(poolRes.data.pool_id)
        setPlayers(poolRes.data.players)

        if (poolRes.data.status === 'preferences_open') {
          setPhase('voting')
        } else if (poolRes.data.status === 'completed') {
          // 获取选秀结果
          const resultsRes = await api.getDraftResults(team.current_league_id, season.id)
          if (resultsRes.success && resultsRes.data) {
            setResults(resultsRes.data.selections)
          }
          // 获取本队待签约
          const selRes = await api.getTeamDraftSelections(team.id, season.id)
          if (selRes.success && selRes.data) {
            setSelections(selRes.data)
          }
          setPhase(selections.length > 0 ? 'signing' : 'result')
        } else {
          setPhase('result')
        }
      } else {
        // 无选秀池
        setPhase('result')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败')
      setPhase('error')
    }
  }, [selections.length])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const handleSavePreferences = async () => {
    if (!poolId) return
    setSaving(true)
    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        alert('无法获取球队信息')
        return
      }
      const prefs = players.map((p, idx) => ({
        player_id: p.player_id,
        priority: idx + 1,
        excluded: false,
      }))
      const res = await api.saveDraftPreferences(poolId, teamRes.data.id, prefs)
      if (res.success) {
        alert('志愿已保存')
      } else {
        alert(res.message || '保存失败')
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSign = async (selection: TeamSelection) => {
    setSigningId(selection.selection_id)
    setSignLoading(true)
    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        alert('无法获取球队信息')
        return
      }
      const res = await api.signDraftPlayer(selection.selection_id, {
        team_id: teamRes.data.id,
        years: 2,
        wage: 1000, // 简化，实际应获取建议工资
        squad_role: 'youngster',
      })
      if (res.success) {
        alert(`成功签约 ${selection.name}！`)
        fetchData()
      } else {
        alert(res.message || '签约失败')
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : '签约失败')
    } finally {
      setSignLoading(false)
      setSigningId(null)
    }
  }

  const handleDecline = async (selectionId: string) => {
    if (!confirm('确定要放弃这名选秀球员吗？他将进入自由市场。')) return
    try {
      const res = await api.declineDraftPlayer(selectionId)
      if (res.success) {
        fetchData()
      } else {
        alert(res.message || '放弃失败')
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : '放弃失败')
    }
  }

  if (phase === 'loading') {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
        <span className="ml-2 text-sm text-[#8B8BA7]">加载中...</span>
      </div>
    )
  }

  if (phase === 'error') {
    return (
      <div className="flex items-center gap-2 p-4 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
        <AlertTriangle className="w-4 h-4" />
        {error || '加载失败'}
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">选秀大会</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">志愿优先级排序，系统自动分配</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/youth/academy" className="btn-secondary text-sm">青训营</Link>
        </div>
      </div>

      {/* 阶段提示 */}
      {phase === 'voting' && (
        <div className="bg-[#0D4A4D]/20 border-2 border-[#0D7377]/30 p-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#E2E2F0]">
              志愿排序开放中！系统默认按 OVR 降序排序，点击提交即可保存。
            </span>
          </div>
        </div>
      )}

      {phase === 'voting' && (
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">选秀池</h3>
            <span className="text-xs text-[#4B4B6A]">共 {players.length} 名球员</span>
          </div>
          <div className="space-y-2 max-h-[500px] overflow-y-auto">
            {players.map((p, idx) => (
              <div key={p.pool_player_id} className="flex items-center gap-3 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                <span className="w-6 h-6 bg-[#0D7377] flex items-center justify-center text-xs font-bold text-white">
                  {idx + 1}
                </span>
                <span className={clsx('text-xs px-2 py-0.5 font-bold', positionColors[p.position] || 'bg-[#2D2D44] text-white')}>
                  {p.position}
                </span>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{p.name}</p>
                  <p className="text-xs text-[#4B4B6A]">{p.age}岁 · OVR {p.ovr} · 潜力 {p.potential_letter} · {p.source_team_name || '未知来源'}</p>
                </div>
              </div>
            ))}
          </div>
          <button
            onClick={handleSavePreferences}
            disabled={saving || players.length === 0}
            className="btn-primary w-full mt-4 flex items-center justify-center gap-2 disabled:opacity-40"
          >
            <Check className="w-4 h-4" />
            {saving ? '保存中...' : '提交志愿排序'}
          </button>
        </div>
      )}

      {phase === 'result' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">选秀结果</h3>
          {results.length === 0 ? (
            <div className="text-center py-12 text-[#4B4B6A]">
              <WarningDiamond className="w-8 h-8 mx-auto mb-3" />
              <p>暂无选秀结果</p>
              <p className="text-xs mt-1">选秀结束后可查看分配结果</p>
            </div>
          ) : (
            <div className="space-y-2">
              {results.map((r) => (
                <div key={r.selection_id} className="flex items-center gap-3 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                  <span className="w-6 h-6 bg-[#0D7377] flex items-center justify-center text-xs font-bold text-white">
                    {r.selection_order}
                  </span>
                  <span className={clsx('text-xs px-2 py-0.5 font-bold', positionColors[r.position] || 'bg-[#2D2D44] text-white')}>
                    {r.position}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{r.player_name}</p>
                    <p className="text-xs text-[#4B4B6A]">OVR {r.ovr} · {r.team_name}</p>
                  </div>
                  <span className={clsx('text-xs px-2 py-0.5 border', r.status === 'pending' ? 'text-yellow-400 border-yellow-400/30' : r.status === 'signed' ? 'text-emerald-400 border-emerald-400/30' : 'text-[#4B4B6A] border-[#2D2D44]')}>
                    {r.status === 'pending' ? '待签约' : r.status === 'signed' ? '已签约' : r.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {phase === 'signing' && (
        <>
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">待签约选秀球员</h3>
            <div className="space-y-2">
              {selections.map((s) => (
                <div key={s.selection_id} className="flex items-center gap-3 p-3 bg-[#0A0A0F] border-2 border-[#0D7377]/30">
                  <span className={clsx('text-xs px-2 py-0.5 font-bold', positionColors[s.position] || 'bg-[#2D2D44] text-white')}>
                    {s.position}
                  </span>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{s.name}</p>
                    <p className="text-xs text-[#4B4B6A]">{s.age}岁 · OVR {s.ovr} · 潜力 {s.potential_letter}</p>
                  </div>
                  {s.expires_at && (
                    <span className="text-xs text-[#4B4B6A]">
                      截止: {new Date(s.expires_at).toLocaleDateString()}
                    </span>
                  )}
                  <button
                    onClick={() => handleSign(s)}
                    disabled={signLoading && signingId === s.selection_id}
                    className="px-3 py-1.5 bg-emerald-500/20 text-emerald-400 text-xs font-bold border-2 border-emerald-500/30 hover:bg-emerald-500/30 transition-colors disabled:opacity-40"
                  >
                    {signLoading && signingId === s.selection_id ? '签约中...' : '签约'}
                  </button>
                  <button
                    onClick={() => handleDecline(s.selection_id)}
                    className="px-3 py-1.5 bg-red-500/20 text-red-400 text-xs font-bold border-2 border-red-500/30 hover:bg-red-500/30 transition-colors"
                  >
                    <X className="w-3 h-3" />
                  </button>
                </div>
              ))}
            </div>
          </div>

          {results.length > 0 && (
            <div className="card">
              <h3 className="text-lg font-semibold mb-4">全部选秀结果</h3>
              <div className="space-y-2">
                {results.map((r) => (
                  <div key={r.selection_id} className="flex items-center gap-3 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                    <span className="w-6 h-6 bg-[#0D7377] flex items-center justify-center text-xs font-bold text-white">
                      {r.selection_order}
                    </span>
                    <span className={clsx('text-xs px-2 py-0.5 font-bold', positionColors[r.position] || 'bg-[#2D2D44] text-white')}>
                      {r.position}
                    </span>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">{r.player_name}</p>
                      <p className="text-xs text-[#4B4B6A]">OVR {r.ovr} · {r.team_name}</p>
                    </div>
                    <span className={clsx('text-xs px-2 py-0.5 border', r.status === 'pending' ? 'text-yellow-400 border-yellow-400/30' : r.status === 'signed' ? 'text-emerald-400 border-emerald-400/30' : 'text-[#4B4B6A] border-[#2D2D44]')}>
                      {r.status === 'pending' ? '待签约' : r.status === 'signed' ? '已签约' : r.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
