import { useState } from 'react'
import { 
  Zap, 
  Shield, 
  Target,
  Clock,
  WarningDiamond
} from '../../components/ui/pixel-icons'

// 训练内容类型
const trainingTypes = [
  { id: 'attack-tactic', name: '进攻战术演练', category: '战术', effect: '全队进攻+1%', fatigue: 12, icon: Target },
  { id: 'defense-tactic', name: '防守站位训练', category: '战术', effect: '全队防守+1%', fatigue: 12, icon: Shield },
  { id: 'set-piece', name: '定位球专项', category: '战术', effect: '定位球+2%', fatigue: 12, icon: Target },
  { id: 'shooting', name: '射门特训', category: '技术', effect: '前锋射术+0.3', fatigue: 20, icon: Target },
  { id: 'passing', name: '传球特训', category: '技术', effect: '中场传球+0.3', fatigue: 12, icon: Zap },
  { id: 'dribbling', name: '盘带特训', category: '技术', effect: '边锋盘带+0.3', fatigue: 20, icon: Zap },
  { id: 'fitness', name: '体能特训', category: '技术', effect: '全身体能+0.2', fatigue: 25, icon: Zap },
  { id: 'defense-tech', name: '防守特训', category: '技术', effect: '后卫防守+0.3', fatigue: 20, icon: Shield },
  { id: 'rest', name: '全队休息', category: '恢复', effect: '疲劳-25%', fatigue: -25, icon: Clock },
  { id: 'stretch', name: '轻度拉伸', category: '恢复', effect: '疲劳-10%', fatigue: -10, icon: Clock },
  { id: 'massage', name: '按摩恢复', category: '恢复', effect: '指定3人-30%', fatigue: -30, icon: Clock },
  { id: 'video', name: '录像分析', category: '恢复', effect: '克制对方+5%', fatigue: 5, icon: Target },
]

// 快速方案
const quickPlans = [
  { id: 'attack', name: '🔥 强调进攻', desc: '进攻为主，防守为辅' },
  { id: 'defense', name: '🛡️ 强调防守', desc: '防守为主，反击为辅' },
  { id: 'balanced', name: '⚖️ 均衡发展', desc: '攻防均衡' },
  { id: 'recovery', name: '💤 全力恢复', desc: '全周以恢复为主' },
  { id: 'prepare', name: '📹 深度备战', desc: '针对下一场对手' },
  { id: 'fitness', name: '🏃 体能储备', desc: '高强度体能周' },
  { id: 'penalty', name: '🎯 点球备战', desc: '预感要踢点球' },
]

// Mock 球员疲劳
const mockPlayerFatigue = [
  { name: '王强', position: 'GK', fatigue: 15, risk: 'low' },
  { name: '李明', position: 'CB', fatigue: 35, risk: 'low' },
  { name: '张伟', position: 'CB', fatigue: 62, risk: 'medium' },
  { name: '刘洋', position: 'CMF', fatigue: 78, risk: 'high' },
  { name: '陈浩', position: 'WF', fatigue: 45, risk: 'low' },
  { name: '赵雷', position: 'ST', fatigue: 55, risk: 'medium' },
  { name: '孙凯', position: 'WF', fatigue: 30, risk: 'low' },
]

const days = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const periods = ['上午', '下午', '晚上']

const categoryColors: Record<string, string> = {
  '战术': 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  '技术': 'bg-red-500/20 text-red-400 border-red-500/30',
  '恢复': 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
}

export default function WeeklyTraining() {
  const [selectedCell, setSelectedCell] = useState<{day: number, period: number} | null>(null)
  const [plan, setPlan] = useState<(string | null)[][]>(Array(7).fill(null).map(() => Array(3).fill(null)))
  const [selectedPlan, setSelectedPlan] = useState('balanced')

  const applyPlan = (planId: string) => {
    setSelectedPlan(planId)
    // Mock: fill with balanced plan
    const newPlan = Array(7).fill(null).map(() => Array(3).fill(null))
    for (let d = 0; d < 7; d++) {
      if (planId === 'balanced') {
        newPlan[d][0] = 'shooting'
        newPlan[d][1] = 'attack-tactic'
        newPlan[d][2] = 'stretch'
      } else if (planId === 'attack') {
        newPlan[d][0] = 'shooting'
        newPlan[d][1] = 'attack-tactic'
        newPlan[d][2] = 'rest'
      } else if (planId === 'defense') {
        newPlan[d][0] = 'defense-tech'
        newPlan[d][1] = 'defense-tactic'
        newPlan[d][2] = 'rest'
      } else if (planId === 'recovery') {
        newPlan[d][0] = 'rest'
        newPlan[d][1] = 'stretch'
        newPlan[d][2] = 'massage'
      }
    }
    setPlan(newPlan)
  }

  const setTraining = (trainingId: string) => {
    if (!selectedCell) return
    const newPlan = plan.map(row => [...row])
    newPlan[selectedCell.day][selectedCell.period] = trainingId
    setPlan(newPlan)
  }

  const getTrainingName = (id: string | null) => {
    if (!id) return null
    return trainingTypes.find(t => t.id === id)?.name
  }

  const getTrainingCategory = (id: string | null) => {
    if (!id) return null
    return trainingTypes.find(t => t.id === id)?.category
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">训练中心</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">规划本周训练，提升球队实力</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-2 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30 text-sm">
            <Clock className="w-4 h-4 text-[#0D7377]" />
            <span className="text-[#0D7377] font-medium">☀️ 上午训练中</span>
          </div>
        </div>
      </div>

      {/* 实时横幅 */}
      <div className="bg-[#0D4A4D]/20 border-2 border-[#0D7377]/30 p-4">
        <p className="text-sm text-[#E2E2F0]">
          ☀️ 球员们正在进行上午训练：<span className="text-[#0D7377] font-bold">体能特训</span>（还剩1.5小时）
        </p>
      </div>

      {/* 快速方案 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">快速方案</h3>
        <div className="flex flex-wrap gap-2">
          {quickPlans.map((p) => (
            <button
              key={p.id}
              onClick={() => applyPlan(p.id)}
              className={clsx(
                'px-4 py-2 border-2 text-sm font-medium transition-all duration-200',
                selectedPlan === p.id
                  ? 'bg-[#0D7377] border-[#0A5A5D] text-white shadow-pixel-green'
                  : 'bg-[#0A0A0F] border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50 hover:text-white'
              )}
            >
              {p.name}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 训练矩阵 */}
        <div className="lg:col-span-2 card">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold">本周训练计划</h3>
            <button 
              onClick={() => setPlan(Array(7).fill(null).map(() => Array(3).fill(null)))}
              className="text-xs text-[#8B8BA7] hover:text-white transition-colors"
            >
              清空全部
            </button>
          </div>
          
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  <th className="text-left text-xs text-[#4B4B6A] pb-2 pr-2">时段</th>
                  {days.map(d => (
                    <th key={d} className="text-center text-xs text-[#4B4B6A] pb-2 px-1">{d}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {periods.map((period, pi) => (
                  <tr key={period}>
                    <td className="text-xs text-[#8B8BA7] pr-2 py-1">{period}</td>
                    {days.map((_, di) => {
                      const trainingId = plan[di][pi]
                      const isSelected = selectedCell?.day === di && selectedCell?.period === pi
                      const category = getTrainingCategory(trainingId)
                      return (
                        <td key={di} className="px-1 py-1">
                          <button
                            onClick={() => setSelectedCell({ day: di, period: pi })}
                            className={clsx(
                              'w-full h-14 border-2 text-[10px] leading-tight p-1 transition-all duration-200',
                              isSelected
                                ? 'border-[#0D7377] bg-[#0D7377]/20 shadow-pixel-green'
                                : trainingId
                                  ? 'border-transparent'
                                  : 'border-[#2D2D44] bg-[#0A0A0F] hover:border-[#0D7377]/50'
                            )}
                            style={category ? {
                              backgroundColor: category === '战术' ? 'rgba(59,130,246,0.1)' :
                                category === '技术' ? 'rgba(239,68,68,0.1)' :
                                'rgba(16,185,129,0.1)',
                              borderColor: category === '战术' ? 'rgba(59,130,246,0.3)' :
                                category === '技术' ? 'rgba(239,68,68,0.3)' :
                                'rgba(16,185,129,0.3)'
                            } : {}}
                          >
                            {trainingId ? (
                              <span className={clsx(
                                'text-[10px]',
                                category === '战术' ? 'text-blue-400' :
                                category === '技术' ? 'text-red-400' :
                                'text-emerald-400'
                              )}>
                                {getTrainingName(trainingId)}
                              </span>
                            ) : (
                              <span className="text-[#4B4B6A]">+</span>
                            )}
                          </button>
                        </td>
                      )
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 训练内容侧边栏 */}
        <div className="space-y-6">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">训练内容</h3>
            <p className="text-xs text-[#4B4B6A] mb-3">
              {selectedCell ? `选择 ${days[selectedCell.day]} ${periods[selectedCell.period]} 的训练` : '点击左侧格子选择时段'}
            </p>
            <div className="space-y-1 max-h-[400px] overflow-y-auto">
              {trainingTypes.map((t) => (
                <button
                  key={t.id}
                  disabled={!selectedCell}
                  onClick={() => setTraining(t.id)}
                  className={clsx(
                    'w-full text-left p-2 border-2 transition-all duration-200 disabled:opacity-30',
                    'hover:border-[#0D7377]/50 bg-[#0A0A0F] border-[#2D2D44]'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-white">{t.name}</span>
                    <span className={clsx('text-[10px] px-1 py-0.5 border', categoryColors[t.category])}>
                      {t.category}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-[10px] text-[#8B8BA7]">{t.effect}</span>
                    <span className={clsx('text-[10px]', t.fatigue > 0 ? 'text-red-400' : 'text-emerald-400')}>
                      {t.fatigue > 0 ? `+${t.fatigue}疲劳` : `${t.fatigue}疲劳`}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* 疲劳总览 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <WarningDiamond className="w-4 h-4 text-yellow-500" />
          全队疲劳总览
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {mockPlayerFatigue.map((p) => (
            <div key={p.name} className="bg-[#0A0A0F] border-2 border-[#2D2D44] p-3">
              <p className="text-xs text-white font-medium">{p.name}</p>
              <p className="text-[10px] text-[#4B4B6A]">{p.position}</p>
              <div className="mt-2">
                <div className="pixel-progress-track h-2">
                  <div 
                    className={clsx(
                      'pixel-progress-fill h-full',
                      p.fatigue > 80 ? 'bg-red-500' : p.fatigue > 60 ? 'bg-yellow-500' : 'bg-emerald-500'
                    )}
                    style={{ width: `${p.fatigue}%` }}
                  />
                </div>
                <p className={clsx(
                  'text-[10px] mt-1 text-right',
                  p.fatigue > 80 ? 'text-red-400' : p.fatigue > 60 ? 'text-yellow-400' : 'text-emerald-400'
                )}>
                  {p.fatigue}%
                </p>
              </div>
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
