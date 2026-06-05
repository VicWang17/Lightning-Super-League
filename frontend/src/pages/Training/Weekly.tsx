import { useEffect, useState, useCallback } from 'react'
import {
  Clock,
  WarningDiamond,
  Archive,
  Check
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import type { TrainingItem, PlayerFatigueItem } from '../../types/training'
import { TRAINING_CATEGORY_BG } from '../../types/training'
import { Card } from '../../components/ui/Card'

const DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const PERIODS = [
  { key: 'morning', label: '上午' },
  { key: 'afternoon', label: '下午' },
  { key: 'evening', label: '晚上' },
] as const

export default function WeeklyTraining() {
  const [items, setItems] = useState<TrainingItem[]>([])
  const [fatigue, setFatigue] = useState<PlayerFatigueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [selectedCell, setSelectedCell] = useState<{ dayIndex: number; periodIndex: number } | null>(null)
  const [localPlan, setLocalPlan] = useState<Map<string, string | null>>(new Map())
  const [weekStart, setWeekStart] = useState(1)
  const [teamId, setTeamId] = useState('')
  const [seasonId, setSeasonId] = useState('')

  // 加载数据
  useEffect(() => {
    let cancelled = false
    async function fetch() {
      try {
        const [teamRes, seasonRes, itemsRes] = await Promise.all([
          api.get<{ id: string }>('/teams/my-team'),
          api.getCurrentSeason(),
          api.getTrainingItems(),
        ])
        if (!teamRes.success || !teamRes.data?.id) return
        if (!seasonRes.success || !seasonRes.data?.id) return

        const tid = teamRes.data.id
        const sid = seasonRes.data.id
        const currentDay = seasonRes.data.current_day || 1
        const start = Math.max(1, currentDay - ((currentDay - 1) % 7))

        setTeamId(tid)
        setSeasonId(sid)
        setWeekStart(start)

        if (itemsRes.success) {
          setItems(itemsRes.data?.items || [])
        }

        const [planRes, fatigueRes] = await Promise.all([
          api.getTeamTrainingPlan(tid, sid, start, 7),
          api.getTeamFatigue(tid),
        ])

        if (!cancelled) {
          if (planRes.success) {
            const fetched = planRes.data?.items || []
            const map = new Map<string, string | null>()
            for (const p of fetched) {
              const key = `${p.season_day}-${p.slot}`
              map.set(key, p.training_item_id)
            }
            setLocalPlan(map)
          }
          if (fatigueRes.success) {
            setFatigue(fatigueRes.data?.players || [])
          }
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

  const getCellKey = useCallback((dayIndex: number, slot: string) => {
    return `${weekStart + dayIndex}-${slot}`
  }, [weekStart])

  const getCellItem = useCallback((dayIndex: number, slot: string) => {
    const itemId = localPlan.get(getCellKey(dayIndex, slot))
    if (!itemId) return null
    return items.find(i => i.id === itemId) || null
  }, [localPlan, items, getCellKey])

  const setTraining = useCallback((trainingId: string) => {
    if (!selectedCell) return
    const slotKey = PERIODS[selectedCell.periodIndex].key
    const key = getCellKey(selectedCell.dayIndex, slotKey)
    const next = new Map(localPlan)
    next.set(key, trainingId)
    setLocalPlan(next)
  }, [selectedCell, localPlan, getCellKey])

  const savePlan = async () => {
    if (!teamId || !seasonId) return
    setSaving(true)
    setSaveMsg('')
    try {
      const saveItems: Array<{
        season_day: number
        slot: string
        mode: string
        training_item_id?: string
      }> = []
      for (let d = 0; d < 7; d++) {
        for (const p of PERIODS) {
          const key = getCellKey(d, p.key)
          const itemId = localPlan.get(key)
          saveItems.push({
            season_day: weekStart + d,
            slot: p.key,
            mode: 'team',
            ...(itemId ? { training_item_id: itemId } : {}),
          })
        }
      }
      const res = await api.saveTeamTrainingPlan(teamId, seasonId, saveItems)
      if (res.success) {
        setSaveMsg('保存成功')
        setTimeout(() => setSaveMsg(''), 2000)
      } else {
        setSaveMsg(res.message || '保存失败')
      }
    } catch {
      setSaveMsg('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const clearAll = () => {
    setLocalPlan(new Map())
  }

  if (loading) {
    return <div className="max-w-[1400px] p-8 text-center text-[#8B8BA7]">加载中...</div>
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
          <button
            onClick={savePlan}
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-[#0D7377] border-2 border-[#0A5A5D] text-white text-sm font-medium hover:bg-[#0A5A5D] transition-all disabled:opacity-50"
          >
            {saving ? <Clock className="w-4 h-4 animate-spin" /> : <Archive className="w-4 h-4" />}
            保存计划
          </button>
          {saveMsg && (
            <span className={`text-sm flex items-center gap-1 ${saveMsg.includes('成功') ? 'text-emerald-400' : 'text-red-400'}`}>
              {saveMsg.includes('成功') && <Check className="w-4 h-4" />}
              {saveMsg}
            </span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 训练矩阵 */}
        <div className="lg:col-span-2">
          <Card>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">本周训练计划（第 {weekStart}~{weekStart + 6} 天）</h3>
              <button
                onClick={clearAll}
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
                    {DAYS.map((d, i) => (
                      <th key={d} className="text-center text-xs text-[#4B4B6A] pb-2 px-1">
                        {d}
                        <span className="block text-[10px] text-[#2D2D44]">第{weekStart + i}天</span>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {PERIODS.map((period, pi) => (
                    <tr key={period.key}>
                      <td className="text-xs text-[#8B8BA7] pr-2 py-1">{period.label}</td>
                      {DAYS.map((_, di) => {
                        const item = getCellItem(di, period.key)
                        const isSelected = selectedCell?.dayIndex === di && selectedCell?.periodIndex === pi
                        const style = item ? TRAINING_CATEGORY_BG[item.category] : null
                        return (
                          <td key={di} className="px-1 py-1">
                            <button
                              onClick={() => setSelectedCell({ dayIndex: di, periodIndex: pi })}
                              className={`w-full h-14 border-2 text-[10px] leading-tight p-1 transition-all duration-200 ${
                                isSelected
                                  ? 'border-[#C6F135] shadow-pixel-green'
                                  : item
                                  ? 'border-transparent'
                                  : 'border-[#2D2D44] bg-[#0A0A0F] hover:border-[#0D7377]/50'
                              }`}
                              style={style ? {
                                backgroundColor: style.bg,
                                borderColor: isSelected ? '#C6F135' : style.border,
                              } : {}}
                            >
                              {item ? (
                                <span className={`text-[10px] ${style?.text || 'text-white'}`}>
                                  {item.name}
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
          </Card>
        </div>

        {/* 训练内容侧边栏 */}
        <div className="space-y-6">
          <Card>
            <h3 className="text-lg font-semibold mb-4">训练内容</h3>
            <p className="text-xs text-[#4B4B6A] mb-3">
              {selectedCell
                ? `选择 ${DAYS[selectedCell.dayIndex]} ${PERIODS[selectedCell.periodIndex].label} 的训练`
                : '点击左侧格子选择时段'}
            </p>
            <div className="space-y-1 max-h-[400px] overflow-y-auto">
              {items.map(t => (
                <button
                  key={t.id}
                  disabled={!selectedCell}
                  onClick={() => setTraining(t.id)}
                  className="w-full text-left p-2 border-2 transition-all duration-200 disabled:opacity-30 hover:border-[#0D7377]/50 bg-[#0A0A0F] border-[#2D2D44]"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-white">{t.name}</span>
                    <span className={`text-[10px] px-1 py-0.5 border ${TRAINING_CATEGORY_BG[t.category]?.text || 'text-[#8B8BA7]'} ${TRAINING_CATEGORY_BG[t.category]?.bg || 'bg-[#1E1E2D]'} ${TRAINING_CATEGORY_BG[t.category]?.border || 'border-[#2D2D44]'}`}>
                      {t.category}
                    </span>
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-[10px] text-[#8B8BA7]">强度 {t.intensity}</span>
                    <span className={`text-[10px] ${t.fatigue_delta > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                      {t.fatigue_delta > 0 ? `+${t.fatigue_delta}疲劳` : `${t.fatigue_delta}疲劳`}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </Card>
        </div>
      </div>

      {/* 疲劳总览 */}
      <Card>
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <WarningDiamond className="w-4 h-4 text-yellow-500" />
          全队疲劳总览
        </h3>
        {fatigue.length === 0 ? (
          <p className="text-[#8B8BA7] text-center py-8">暂无疲劳数据</p>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {fatigue.map(p => (
              <div key={p.player_id} className="bg-[#0A0A0F] border-2 border-[#2D2D44] p-3">
                <p className="text-xs text-white font-medium">{p.player_name}</p>
                <div className="mt-2">
                  <div className="pixel-progress-track h-2">
                    <div
                      className={`pixel-progress-fill h-full ${
                        p.fatigue > 80 ? 'bg-red-500' : p.fatigue > 60 ? 'bg-yellow-500' : 'bg-emerald-500'
                      }`}
                      style={{ width: `${Math.min(100, p.fatigue)}%` }}
                    />
                  </div>
                  <p className={`text-[10px] mt-1 text-right ${p.fatigue > 80 ? 'text-red-400' : p.fatigue > 60 ? 'text-yellow-400' : 'text-emerald-400'}`}>
                    {p.fatigue}%
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
