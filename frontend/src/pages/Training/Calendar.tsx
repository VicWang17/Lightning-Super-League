import { useEffect, useState, useMemo } from 'react'
import { Calendar, Clock, Zap, Shield, Target } from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import type { TrainingPlanSlot, TrainingResultItem } from '../../types/training'
import { Card } from '../../components/ui/Card'
import { TRAINING_CATEGORY_BG } from '../../types/training'

const SLOT_LABELS: Record<string, string> = {
  morning: '上午',
  afternoon: '下午',
  evening: '晚上',
}

const DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

export default function TrainingCalendar() {
  const [plans, setPlans] = useState<TrainingPlanSlot[]>([])
  const [results, setResults] = useState<TrainingResultItem[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedWeek, setSelectedWeek] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function fetch() {
      try {
        const [teamRes, seasonRes] = await Promise.all([
          api.get<{ id: string }>('/teams/my-team'),
          api.getCurrentSeason(),
        ])
        if (!teamRes.success || !teamRes.data?.id) return
        if (!seasonRes.success || !seasonRes.data?.id) return
        const currentDay = seasonRes.data.current_day || 1
        const weekStart = Math.max(1, currentDay - ((currentDay - 1) % 7))

        const [planRes, resultRes] = await Promise.all([
          api.getTeamTrainingPlan(teamRes.data.id, seasonRes.data.id, weekStart, 14),
          api.getTrainingResults(teamRes.data.id, seasonRes.data.id, { start_day: Math.max(1, currentDay - 14), days: 21, limit: 500 }),
        ])
        if (!cancelled) {
          if (planRes.success && Array.isArray(planRes.data)) setPlans(planRes.data)
          if (resultRes.success && Array.isArray(resultRes.data)) setResults(resultRes.data)
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

  const weeks = useMemo(() => {
    if (plans.length === 0) return [] as Array<{ label: string; startDay: number }>
    const minDay = Math.min(...plans.map(p => p.season_day))
    const start = Math.floor((minDay - 1) / 7) * 7 + 1
    const list: Array<{ label: string; startDay: number }> = []
    for (let i = 0; i < 4; i++) {
      const s = start + i * 7
      list.push({ label: `第 ${s}~${s + 6} 天`, startDay: s })
    }
    return list
  }, [plans])

  const currentWeekStart = weeks[selectedWeek]?.startDay ?? 1

  const weekPlans = useMemo(() => {
    const map: Record<string, { am?: TrainingPlanSlot; pm?: TrainingPlanSlot; eve?: TrainingPlanSlot }> = {}
    for (let i = 0; i < 7; i++) {
      const day = currentWeekStart + i
      map[String(day)] = { am: undefined, pm: undefined, eve: undefined }
    }
    for (const p of plans) {
      if (p.season_day >= currentWeekStart && p.season_day < currentWeekStart + 7) {
        const dayKey = String(p.season_day)
        if (!map[dayKey]) map[dayKey] = {}
        if (p.slot === 'morning') map[dayKey].am = p
        else if (p.slot === 'afternoon') map[dayKey].pm = p
        else if (p.slot === 'evening') map[dayKey].eve = p
      }
    }
    return map
  }, [plans, currentWeekStart])

  const weekResults = useMemo(() => {
    return results.filter(r => r.season_day >= currentWeekStart && r.season_day < currentWeekStart + 7)
  }, [results, currentWeekStart])

  const avgIntensity = useMemo(() => {
    const completed = weekResults.length
    if (completed === 0) return 0
    // 用疲劳变化作为强度指标
    const totalFatigue = weekResults.reduce((s, r) => s + Math.max(0, r.fatigue_after - r.fatigue_before), 0)
    return Math.min(100, Math.round(totalFatigue / completed * 3))
  }, [weekResults])

  if (loading) {
    return <div className="max-w-[1400px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-2xl font-bold text-white">训练日历</h1>
        <p className="text-sm text-[#8B8BA7] mt-1">查看训练计划与执行记录</p>
      </div>

      <div className="flex gap-2 flex-wrap">
        {weeks.map((w, idx) => (
          <button
            key={w.startDay}
            onClick={() => setSelectedWeek(idx)}
            className={`px-4 py-2 border-2 text-sm font-medium transition-all duration-200 ${
              selectedWeek === idx
                ? 'bg-[#0D7377] border-[#0A5A5D] text-white shadow-pixel-green'
                : 'bg-[#0A0A0F] border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50 hover:text-white'
            }`}
          >
            {w.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-sm text-[#8B8BA7]">该周训练人次</span>
          </div>
          <p className="text-2xl font-bold text-white">{weekResults.length} 次</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-[#8B8BA7]">计划项</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {Object.values(weekPlans).reduce((s, d) => s + (d.am ? 1 : 0) + (d.pm ? 1 : 0) + (d.eve ? 1 : 0), 0)} 项
          </p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">平均强度</span>
          </div>
          <p className="text-2xl font-bold text-white">{avgIntensity}%</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-red-400" />
            <span className="text-sm text-[#8B8BA7]">属性突破</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {weekResults.reduce((s, r) => s + (r.breakthroughs?.length ?? 0), 0)} 次
          </p>
        </Card>
      </div>

      <Card>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-[#0D7377]" />
          训练明细
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-[#2D2D44]">
                <th className="text-left text-xs text-[#4B4B6A] py-2 pr-4">日期</th>
                <th className="text-left text-xs text-[#4B4B6A] py-2 px-3">上午</th>
                <th className="text-left text-xs text-[#4B4B6A] py-2 px-3">下午</th>
                <th className="text-left text-xs text-[#4B4B6A] py-2 px-3">晚上</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 7 }).map((_, i) => {
                const dayNum = currentWeekStart + i
                const dayData = weekPlans[String(dayNum)] || {}
                const dayResults = results.filter(r => r.season_day === dayNum)
                return (
                  <tr key={dayNum} className="border-b border-[#2D2D44]/50">
                    <td className="py-3 pr-4 text-sm text-white font-medium">
                      第 {dayNum} 天
                      <span className="text-[#4B4B6A] ml-1">({DAYS[i]})</span>
                      {dayResults.length > 0 && (
                        <span className="ml-2 text-[10px] text-emerald-400">✓ 已执行</span>
                      )}
                    </td>
                    <td className="py-3 px-3">
                      <SlotCell slot={dayData.am} />
                    </td>
                    <td className="py-3 px-3">
                      <SlotCell slot={dayData.pm} />
                    </td>
                    <td className="py-3 px-3">
                      <SlotCell slot={dayData.eve} />
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {weekResults.length > 0 && (
        <Card>
          <h3 className="text-lg font-semibold mb-4">该周训练成果</h3>
          <div className="space-y-2">
            {weekResults.slice(0, 20).map(r => (
              <div key={r.id} className="flex items-center gap-3 text-sm bg-[#0A0A0F] p-2 border border-[#2D2D44]">
                <span className="text-white w-20 truncate">{r.player_name || r.player_id}</span>
                <span className="text-[#8B8BA7] w-24 truncate">{r.training_item_name || r.training_item_id}</span>
                <span className="text-[#4B4B6A]">第{r.season_day}天 · {SLOT_LABELS[r.slot] || r.slot}</span>
                <span className="text-amber-400 ml-auto">效率 {r.efficiency}%</span>
                {r.breakthroughs && r.breakthroughs.length > 0 && (
                  <span className="text-emerald-400 text-xs">突破 {r.breakthroughs.length} 项</span>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  )
}

function SlotCell({ slot }: { slot?: TrainingPlanSlot }) {
  if (!slot?.training_item) return <span className="text-[#4B4B6A] text-sm">-</span>
  const style = TRAINING_CATEGORY_BG[slot.training_item.category]
  return (
    <span
      className="text-xs px-2 py-1 border inline-block"
      style={style ? {
        backgroundColor: style.bg,
        borderColor: style.border,
        color: style.text.replace('text-', ''),
      } : {}}
    >
      {slot.training_item.name}
    </span>
  )
}
