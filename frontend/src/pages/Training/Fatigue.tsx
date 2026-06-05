import { useEffect, useState, useMemo } from 'react'
import { WarningDiamond, Heart, TrendingUp, User } from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import type { TeamFatigueResponse } from '../../types/training'
import { Card } from '../../components/ui/Card'

function getRiskColor(risk: string) {
  switch (risk) {
    case 'high': return 'text-red-400 bg-red-500/10 border-red-500/30'
    case 'medium': return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/30'
    default: return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30'
  }
}

function getRiskLabel(risk: string) {
  switch (risk) {
    case 'high': return '高风险'
    case 'medium': return '中等'
    default: return '正常'
  }
}

function getFatigueBarColor(v: number) {
  if (v >= 80) return 'bg-red-500'
  if (v >= 60) return 'bg-yellow-500'
  return 'bg-emerald-500'
}

function getRiskFromFatigue(fatigue: number): 'high' | 'medium' | 'low' {
  if (fatigue >= 75) return 'high'
  if (fatigue >= 50) return 'medium'
  return 'low'
}

export default function PlayerFatigue() {
  const [data, setData] = useState<TeamFatigueResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [sortBy, setSortBy] = useState<'fatigue' | 'risk'>('fatigue')

  useEffect(() => {
    let cancelled = false
    async function fetch() {
      try {
        const teamRes = await api.get<{ id: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) return
        const fatigueRes = await api.getTeamFatigue(teamRes.data.id)
        if (!cancelled && fatigueRes.success) {
          setData(fatigueRes.data)
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetch()
    return () => { cancelled = true }
  }, [])

  const sorted = useMemo(() => {
    if (!data?.players) return []
    const arr = [...data.players]
    if (sortBy === 'fatigue') {
      arr.sort((a, b) => b.fatigue - a.fatigue)
    } else {
      const riskOrder = { high: 0, medium: 1, low: 2 }
      arr.sort((a, b) => riskOrder[getRiskFromFatigue(a.fatigue)] - riskOrder[getRiskFromFatigue(b.fatigue)])
    }
    return arr
  }, [data, sortBy])

  const highRiskCount = useMemo(() => data?.players?.filter(p => getRiskFromFatigue(p.fatigue) === 'high').length ?? 0, [data])
  const avgFatigue = useMemo(() => data?.avg_fatigue ?? 0, [data])
  const totalPlayers = data?.players?.length ?? 0
  const goodCount = data?.players?.filter(p => p.fatigue <= 60).length ?? 0

  if (loading) {
    return <div className="max-w-[1400px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-2xl font-bold text-white">球员疲劳</h1>
        <p className="text-sm text-[#8B8BA7] mt-1">监控全队疲劳状态，预防伤病</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <Heart className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">平均疲劳</span>
          </div>
          <p className={`text-2xl font-bold ${avgFatigue > 60 ? 'text-yellow-400' : 'text-white'}`}>
            {avgFatigue.toFixed(0)}%
          </p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <WarningDiamond className="w-4 h-4 text-red-400" />
            <span className="text-sm text-[#8B8BA7]">高风险球员</span>
          </div>
          <p className={`text-2xl font-bold ${highRiskCount > 0 ? 'text-red-400' : 'text-white'}`}>
            {highRiskCount} 人
          </p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <User className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-[#8B8BA7]">总球员数</span>
          </div>
          <p className="text-2xl font-bold text-white">{totalPlayers} 人</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">状态良好</span>
          </div>
          <p className="text-2xl font-bold text-white">{goodCount} 人</p>
        </Card>
      </div>

      {highRiskCount > 0 && (
        <Card className="border-red-500/30 bg-red-500/5">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-red-400">
            <WarningDiamond className="w-4 h-4" />
            需要立即休息的球员
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {sorted
              .filter(p => getRiskFromFatigue(p.fatigue) === 'high')
              .map(p => (
                <div key={p.player_id} className="flex items-center gap-3 bg-[#0A0A0F] p-3 border border-red-500/20">
                  <div className="w-9 h-9 bg-red-500/10 border border-red-500/30 flex items-center justify-center">
                    <span className="text-sm font-bold text-red-400">{p.player_name.charAt(0)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white font-medium">{p.player_name}</p>
                    <p className="text-xs text-[#4B4B6A]">{p.recommendation}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-red-400">{p.fatigue}%</p>
                    <p className="text-[10px] text-red-400/70">疲劳值</p>
                  </div>
                </div>
              ))}
          </div>
        </Card>
      )}

      <Card>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">全队疲劳详情</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setSortBy('fatigue')}
              className={`px-3 py-1 text-xs border-2 transition-all ${
                sortBy === 'fatigue'
                  ? 'bg-[#0D7377] border-[#0A5A5D] text-white'
                  : 'bg-[#0A0A0F] border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50'
              }`}
            >
              按疲劳排序
            </button>
            <button
              onClick={() => setSortBy('risk')}
              className={`px-3 py-1 text-xs border-2 transition-all ${
                sortBy === 'risk'
                  ? 'bg-[#0D7377] border-[#0A5A5D] text-white'
                  : 'bg-[#0A0A0F] border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50'
              }`}
            >
              按风险排序
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {sorted.map(p => (
            <div key={p.player_id} className="bg-[#0A0A0F] border border-[#2D2D44] p-4">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center shrink-0">
                  <span className="text-sm font-bold text-white">{p.player_name.charAt(0)}</span>
                </div>
                <div className="w-24 shrink-0">
                  <p className="text-sm text-white font-medium">{p.player_name}</p>
                  <p className="text-xs text-[#4B4B6A]">{p.recommendation}</p>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <div className="pixel-progress-track h-3 flex-1">
                      <div
                        className={`pixel-progress-fill h-full ${getFatigueBarColor(p.fatigue)}`}
                        style={{ width: `${Math.min(100, p.fatigue)}%` }}
                      />
                    </div>
                    <span className={`text-sm font-bold w-10 text-right ${p.fatigue > 60 ? 'text-yellow-400' : 'text-emerald-400'}`}>
                      {p.fatigue}%
                    </span>
                  </div>
                </div>
                <span className={`text-xs px-2 py-1 border shrink-0 ${getRiskColor(getRiskFromFatigue(p.fatigue))}`}>
                  {getRiskLabel(getRiskFromFatigue(p.fatigue))}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
