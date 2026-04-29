import { useState } from 'react'
import { WarningDiamond, Heart, TrendingUp, User } from '../../components/ui/pixel-icons'

interface PlayerFatigue {
  id: string
  name: string
  position: string
  fatigue: number
  trend: number[]
  risk: 'low' | 'medium' | 'high'
  recommendation: string
}

const players: PlayerFatigue[] = [
  { id: '1', name: '王强', position: 'GK', fatigue: 15, trend: [20, 18, 15, 12, 15, 18, 15], risk: 'low', recommendation: '状态良好，可正常安排训练' },
  { id: '2', name: '李明', position: 'CB', fatigue: 35, trend: [30, 32, 35, 38, 40, 38, 35], risk: 'low', recommendation: '状态良好，可正常安排训练' },
  { id: '3', name: '张伟', position: 'CB', fatigue: 62, trend: [45, 50, 55, 60, 58, 60, 62], risk: 'medium', recommendation: '建议安排轻度恢复训练' },
  { id: '4', name: '刘洋', position: 'CMF', fatigue: 78, trend: [55, 60, 65, 70, 75, 76, 78], risk: 'high', recommendation: '疲劳较高，建议休息或按摩恢复' },
  { id: '5', name: '陈浩', position: 'WF', fatigue: 45, trend: [40, 42, 45, 48, 50, 48, 45], risk: 'low', recommendation: '状态良好，可正常安排训练' },
  { id: '6', name: '赵雷', position: 'ST', fatigue: 55, trend: [50, 52, 55, 58, 55, 53, 55], risk: 'medium', recommendation: '建议控制训练强度' },
  { id: '7', name: '孙凯', position: 'WF', fatigue: 30, trend: [35, 33, 30, 28, 30, 32, 30], risk: 'low', recommendation: '状态良好，可正常安排训练' },
  { id: '8', name: '周鹏', position: 'DMF', fatigue: 82, trend: [60, 65, 70, 75, 80, 82, 82], risk: 'high', recommendation: '极度疲劳，强制休息！' },
  { id: '9', name: '吴迪', position: 'CB', fatigue: 48, trend: [40, 43, 46, 48, 50, 49, 48], risk: 'low', recommendation: '状态良好，可正常安排训练' },
  { id: '10', name: '郑华', position: 'AMF', fatigue: 70, trend: [55, 60, 62, 65, 68, 70, 70], risk: 'high', recommendation: '疲劳较高，建议减少高强度训练' },
]

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

export default function PlayerFatigue() {
  const [sortBy, setSortBy] = useState<'fatigue' | 'risk'>('fatigue')

  const sorted = [...players].sort((a, b) => {
    if (sortBy === 'fatigue') return b.fatigue - a.fatigue
    const riskOrder = { high: 0, medium: 1, low: 2 }
    return riskOrder[a.risk] - riskOrder[b.risk]
  })

  const highRiskCount = players.filter((p) => p.risk === 'high').length
  const avgFatigue = Math.round(players.reduce((s, p) => s + p.fatigue, 0) / players.length)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-2xl font-bold text-white">球员疲劳</h1>
        <p className="text-sm text-[#8B8BA7] mt-1">监控全队疲劳状态，预防伤病</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Heart className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">平均疲劳</span>
          </div>
          <p className={clsx('text-2xl font-bold', avgFatigue > 60 ? 'text-yellow-400' : 'text-white')}>
            {avgFatigue}%
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <WarningDiamond className="w-4 h-4 text-red-400" />
            <span className="text-sm text-[#8B8BA7]">高风险球员</span>
          </div>
          <p className={clsx('text-2xl font-bold', highRiskCount > 0 ? 'text-red-400' : 'text-white')}>
            {highRiskCount} 人
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <User className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-[#8B8BA7]">总球员数</span>
          </div>
          <p className="text-2xl font-bold text-white">{players.length} 人</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">状态良好</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {players.filter((p) => p.fatigue <= 60).length} 人
          </p>
        </div>
      </div>

      {highRiskCount > 0 && (
        <div className="card border-red-500/30 bg-red-500/5">
          <h3 className="text-lg font-semibold mb-3 flex items-center gap-2 text-red-400">
            <WarningDiamond className="w-4 h-4" />
            需要立即休息的球员
          </h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {players
              .filter((p) => p.risk === 'high')
              .map((p) => (
                <div key={p.id} className="flex items-center gap-3 bg-[#0A0A0F] p-3 border border-red-500/20">
                  <div className="w-9 h-9 bg-red-500/10 border border-red-500/30 flex items-center justify-center">
                    <span className="text-sm font-bold text-red-400">{p.name.charAt(0)}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm text-white font-medium">{p.name}</p>
                    <p className="text-xs text-[#4B4B6A]">{p.position} · {p.recommendation}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-red-400">{p.fatigue}%</p>
                    <p className="text-[10px] text-red-400/70">疲劳值</p>
                  </div>
                </div>
              ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">全队疲劳详情</h3>
          <div className="flex gap-2">
            <button
              onClick={() => setSortBy('fatigue')}
              className={clsx(
                'px-3 py-1 text-xs border-2 transition-all',
                sortBy === 'fatigue'
                  ? 'bg-[#0D7377] border-[#0A5A5D] text-white'
                  : 'bg-[#0A0A0F] border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50'
              )}
            >
              按疲劳排序
            </button>
            <button
              onClick={() => setSortBy('risk')}
              className={clsx(
                'px-3 py-1 text-xs border-2 transition-all',
                sortBy === 'risk'
                  ? 'bg-[#0D7377] border-[#0A5A5D] text-white'
                  : 'bg-[#0A0A0F] border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50'
              )}
            >
              按风险排序
            </button>
          </div>
        </div>

        <div className="space-y-3">
          {sorted.map((p) => (
            <div key={p.id} className="bg-[#0A0A0F] border border-[#2D2D44] p-4">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center shrink-0">
                  <span className="text-sm font-bold text-white">{p.name.charAt(0)}</span>
                </div>
                <div className="w-24 shrink-0">
                  <p className="text-sm text-white font-medium">{p.name}</p>
                  <p className="text-xs text-[#4B4B6A]">{p.position}</p>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3">
                    <div className="pixel-progress-track h-3 flex-1">
                      <div
                        className={clsx('pixel-progress-fill h-full', getFatigueBarColor(p.fatigue))}
                        style={{ width: `${p.fatigue}%` }}
                      />
                    </div>
                    <span className={clsx('text-sm font-bold w-10 text-right', p.fatigue > 60 ? 'text-yellow-400' : 'text-emerald-400')}>
                      {p.fatigue}%
                    </span>
                  </div>
                  <div className="flex items-end gap-[2px] mt-2 h-6">
                    {p.trend.map((v, i) => (
                      <div
                        key={i}
                        className={clsx(
                          'flex-1',
                          v >= 80 ? 'bg-red-500/50' : v >= 60 ? 'bg-yellow-500/50' : 'bg-emerald-500/50'
                        )}
                        style={{ height: `${(v / 100) * 24}px` }}
                      />
                    ))}
                  </div>
                </div>
                <span className={clsx('text-xs px-2 py-1 border shrink-0', getRiskColor(p.risk))}>
                  {getRiskLabel(p.risk)}
                </span>
              </div>
              <p className="text-xs text-[#6B6B8A] mt-2 ml-14">{p.recommendation}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
