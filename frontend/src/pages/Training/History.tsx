import { useState } from 'react'
import { ClipboardNote, Zap, Target, Shield, Clock, TrendingUp } from '../../components/ui/pixel-icons'

interface TrainingRecord {
  id: string
  name: string
  category: string
  count: number
  totalEffect: string
  avgFatigue: number
  trend: 'up' | 'down' | 'stable'
}

const records: TrainingRecord[] = [
  { id: '1', name: '射门特训', category: '技术', count: 12, totalEffect: '前锋射术 +3.6', avgFatigue: 20, trend: 'up' },
  { id: '2', name: '传球特训', category: '技术', count: 10, totalEffect: '中场传球 +3.0', avgFatigue: 12, trend: 'stable' },
  { id: '3', name: '体能特训', category: '技术', count: 8, totalEffect: '全身体能 +1.6', avgFatigue: 25, trend: 'down' },
  { id: '4', name: '进攻战术演练', category: '战术', count: 9, totalEffect: '进攻加成 +9%', avgFatigue: 12, trend: 'up' },
  { id: '5', name: '防守站位训练', category: '战术', count: 7, totalEffect: '防守加成 +7%', avgFatigue: 12, trend: 'stable' },
  { id: '6', name: '定位球专项', category: '战术', count: 5, totalEffect: '定位球 +10%', avgFatigue: 12, trend: 'up' },
  { id: '7', name: '全队休息', category: '恢复', count: 14, totalEffect: '疲劳恢复 -350', avgFatigue: -25, trend: 'stable' },
  { id: '8', name: '轻度拉伸', category: '恢复', count: 10, totalEffect: '疲劳恢复 -100', avgFatigue: -10, trend: 'stable' },
  { id: '9', name: '按摩恢复', category: '恢复', count: 6, totalEffect: '疲劳恢复 -180', avgFatigue: -30, trend: 'up' },
  { id: '10', name: '录像分析', category: '恢复', count: 4, totalEffect: '克制加成 +20%', avgFatigue: 5, trend: 'up' },
  { id: '11', name: '防守特训', category: '技术', count: 6, totalEffect: '后卫防守 +1.8', avgFatigue: 20, trend: 'down' },
  { id: '12', name: '盘带特训', category: '技术', count: 5, totalEffect: '边锋盘带 +1.5', avgFatigue: 20, trend: 'stable' },
]

const categoryIcons: Record<string, React.ElementType> = {
  '战术': Target,
  '技术': Zap,
  '恢复': Clock,
}

const categoryColors: Record<string, string> = {
  '战术': 'text-blue-400 bg-blue-500/10 border-blue-500/30',
  '技术': 'text-red-400 bg-red-500/10 border-red-500/30',
  '恢复': 'text-emerald-400 bg-emerald-500/10 border-emerald-500/30',
}

export default function TrainingHistory() {
  const [filter, setFilter] = useState<string>('全部')
  const categories = ['全部', '战术', '技术', '恢复']

  const filtered = filter === '全部' ? records : records.filter((r) => r.category === filter)

  const totalSessions = records.reduce((s, r) => s + r.count, 0)
  const totalFatigue = Math.round(records.reduce((s, r) => s + r.avgFatigue * r.count, 0) / totalSessions)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-2xl font-bold text-white">训练历史</h1>
        <p className="text-sm text-[#8B8BA7] mt-1">过去4周训练执行统计与效果分析</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <ClipboardNote className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">总训练次数</span>
          </div>
          <p className="text-2xl font-bold text-white">{totalSessions} 次</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-sm text-[#8B8BA7]">技术训练占比</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {Math.round(records.filter((r) => r.category === '技术').reduce((s, r) => s + r.count, 0) / totalSessions * 100)}%
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-[#8B8BA7]">战术训练占比</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {Math.round(records.filter((r) => r.category === '战术').reduce((s, r) => s + r.count, 0) / totalSessions * 100)}%
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">平均疲劳/次</span>
          </div>
          <p className={clsx('text-2xl font-bold', totalFatigue > 15 ? 'text-yellow-400' : 'text-white')}>
            {totalFatigue > 0 ? `+${totalFatigue}` : totalFatigue}
          </p>
        </div>
      </div>

      <div className="flex gap-2">
        {categories.map((c) => (
          <button
            key={c}
            onClick={() => setFilter(c)}
            className={clsx(
              'px-4 py-2 border-2 text-sm font-medium transition-all duration-200',
              filter === c
                ? 'bg-[#0D7377] border-[#0A5A5D] text-white shadow-pixel-green'
                : 'bg-[#0A0A0F] border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50 hover:text-white'
            )}
          >
            {c}
          </button>
        ))}
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4">训练执行统计</h3>
        <div className="space-y-3">
          {filtered.map((r) => {
            const Icon = categoryIcons[r.category] || Shield
            return (
              <div key={r.id} className="flex items-center gap-4 bg-[#0A0A0F] border border-[#2D2D44] p-4">
                <div className={clsx('w-10 h-10 flex items-center justify-center border', categoryColors[r.category])}>
                  <Icon className="w-4 h-4" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <p className="text-sm text-white font-medium">{r.name}</p>
                    <span className={clsx('text-[10px] px-1.5 py-0.5 border', categoryColors[r.category])}>
                      {r.category}
                    </span>
                  </div>
                  <p className="text-xs text-[#6B6B8A] mt-1">{r.totalEffect}</p>
                </div>
                <div className="text-right shrink-0">
                  <p className="text-lg font-bold text-white">{r.count} 次</p>
                  <p className={clsx('text-xs', r.avgFatigue > 0 ? 'text-red-400' : 'text-emerald-400')}>
                    平均{r.avgFatigue > 0 ? '+' : ''}{r.avgFatigue}疲劳
                  </p>
                </div>
                <div className="w-24 shrink-0">
                  <div className="pixel-progress-track h-2">
                    <div
                      className={clsx(
                        'pixel-progress-fill h-full',
                        r.trend === 'up' ? 'bg-emerald-500' : r.trend === 'down' ? 'bg-red-500' : 'bg-yellow-500'
                      )}
                      style={{ width: `${Math.min(r.count * 5, 100)}%` }}
                    />
                  </div>
                  <p className={clsx(
                    'text-[10px] text-right mt-1',
                    r.trend === 'up' ? 'text-emerald-400' : r.trend === 'down' ? 'text-red-400' : 'text-yellow-400'
                  )}>
                    {r.trend === 'up' ? '↑ 增加' : r.trend === 'down' ? '↓ 减少' : '→ 稳定'}
                  </p>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
