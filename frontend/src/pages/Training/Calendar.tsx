import { useEffect, useState, useMemo } from 'react'
import { api } from '../../api/client'
import type { TrainingPlanSlot, TrainingResultItem } from '../../types/training'
import { TRAINING_CATEGORY_BG } from '../../types/training'
import { TrainingPageShell } from './components/TrainingPageShell'

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
  const [season, setSeason] = useState<{ current_day: number; total_days: number } | null>(null)

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
        const totalDays = seasonRes.data.total_days || currentDay

        const [planRes, resultRes] = await Promise.all([
          api.getTeamTrainingPlan(teamRes.data.id, seasonRes.data.id, 1, totalDays),
          api.getTrainingResults(teamRes.data.id, seasonRes.data.id, { start_day: 1, days: totalDays, limit: 2000 }),
        ])
        if (!cancelled) {
          setSeason({ current_day: currentDay, total_days: totalDays })
          setSelectedWeek(Math.max(0, Math.floor((currentDay - 1) / 7)))
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
    const totalDays = season?.total_days
    if (!totalDays) {
      return [{ label: '本周', startDay: 1 }]
    }
    const list: Array<{ label: string; startDay: number }> = []
    for (let s = 1; s <= totalDays; s += 7) {
      const e = Math.min(s + 6, totalDays)
      list.push({ label: `第 ${s}~${e} 天`, startDay: s })
    }
    return list
  }, [season])

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
    const totalFatigue = weekResults.reduce((s, r) => s + Math.max(0, r.fatigue_after - r.fatigue_before), 0)
    return Math.min(100, Math.round(totalFatigue / completed * 3))
  }, [weekResults])

  if (loading) {
    return (
      <TrainingPageShell title="训练日历" subtitle="查看训练计划与执行记录">
        <div className="training-panel" style={{ padding: 36, textAlign: 'center', color: 'var(--tr-muted)', fontWeight: 900 }}>
          加载中…
        </div>
      </TrainingPageShell>
    )
  }

  return (
    <TrainingPageShell title="训练日历" subtitle="查看训练计划与执行记录">
      <div className="training-category-tabs" style={{ marginBottom: 14 }}>
        {weeks.map((w, idx) => (
          <button
            key={w.startDay}
            onClick={() => setSelectedWeek(idx)}
            className={selectedWeek === idx ? 'is-active' : ''}
          >
            {w.label}
          </button>
        ))}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, minmax(0, 1fr))', gap: 10, marginBottom: 16 }}>
        <div className="training-stat-tile is-amber">
          <span>该周训练人次</span>
          <strong>{weekResults.length} 次</strong>
        </div>
        <div className="training-stat-tile is-blue">
          <span>计划项</span>
          <strong>
            {Object.values(weekPlans).reduce((s, d) => s + (d.am ? 1 : 0) + (d.pm ? 1 : 0) + (d.eve ? 1 : 0), 0)} 项
          </strong>
        </div>
        <div className="training-stat-tile is-green">
          <span>平均强度</span>
          <strong>{avgIntensity}%</strong>
        </div>
        <div className="training-stat-tile is-red">
          <span>属性突破</span>
          <strong>{weekResults.reduce((s, r) => s + (r.breakthroughs?.length ?? 0), 0)} 次</strong>
        </div>
      </div>

      <div className="training-panel" style={{ padding: 16, marginBottom: 16 }}>
        <h3 style={{ color: 'var(--tr-text)', fontSize: 18, fontWeight: 1000, marginBottom: 14 }}>
          训练明细
        </h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid var(--tr-border)' }}>
                <th style={{ textAlign: 'left', color: 'var(--tr-muted)', fontSize: 12, fontWeight: 900, padding: '8px 12px 8px 0' }}>日期</th>
                <th style={{ textAlign: 'left', color: 'var(--tr-muted)', fontSize: 12, fontWeight: 900, padding: '8px 12px' }}>上午</th>
                <th style={{ textAlign: 'left', color: 'var(--tr-muted)', fontSize: 12, fontWeight: 900, padding: '8px 12px' }}>下午</th>
                <th style={{ textAlign: 'left', color: 'var(--tr-muted)', fontSize: 12, fontWeight: 900, padding: '8px 12px' }}>晚上</th>
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: 7 }).map((_, i) => {
                const dayNum = currentWeekStart + i
                const dayData = weekPlans[String(dayNum)] || {}
                const dayResults = results.filter(r => r.season_day === dayNum)
                return (
                  <tr key={dayNum} style={{ borderBottom: '1px solid var(--tr-border)' }}>
                    <td style={{ padding: '10px 12px 10px 0', color: 'var(--tr-text)', fontSize: 13, fontWeight: 800 }}>
                      第 {dayNum} 天
                      <span style={{ color: 'var(--tr-muted)', marginLeft: 6 }}>({DAYS[i]})</span>
                      {dayResults.length > 0 && (
                        <span style={{ marginLeft: 8, color: '#B9EF3F', fontSize: 11, fontWeight: 1000 }}>✓ 已执行</span>
                      )}
                    </td>
                    <td style={{ padding: '10px 12px' }}><SlotCell slot={dayData.am} /></td>
                    <td style={{ padding: '10px 12px' }}><SlotCell slot={dayData.pm} /></td>
                    <td style={{ padding: '10px 12px' }}><SlotCell slot={dayData.eve} /></td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </div>

      {weekResults.length > 0 && (
        <div className="training-panel" style={{ padding: 16 }}>
          <h3 style={{ color: 'var(--tr-text)', fontSize: 18, fontWeight: 1000, marginBottom: 14 }}>
            该周训练成果
          </h3>
          <div style={{ display: 'grid', gap: 8 }}>
            {weekResults.slice(0, 20).map(r => (
              <div
                key={r.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12,
                  padding: 10,
                  background: 'rgba(255,255,255,0.86)',
                  border: '2px solid var(--tr-border)',
                  fontSize: 13,
                }}
              >
                <span style={{ color: 'var(--tr-text)', width: 80, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontWeight: 800 }}>
                  {r.player_name || r.player_id}
                </span>
                <span style={{ color: 'var(--tr-muted)', width: 120, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.training_item_name || r.training_item_id}
                </span>
                <span style={{ color: 'var(--tr-muted)', fontSize: 12 }}>
                  第{r.season_day}天 · {SLOT_LABELS[r.slot] || r.slot}
                </span>
                <span style={{ color: '#FFC247', marginLeft: 'auto', fontWeight: 1000 }}>效率 {r.efficiency}%</span>
                {r.breakthroughs && r.breakthroughs.length > 0 && (
                  <span style={{ color: '#B9EF3F', fontSize: 11, fontWeight: 1000 }}>突破 {r.breakthroughs.length} 项</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </TrainingPageShell>
  )
}

function SlotCell({ slot }: { slot?: TrainingPlanSlot }) {
  if (!slot?.training_item) return <span style={{ color: 'var(--tr-muted)', fontSize: 13 }}>-</span>
  const style = TRAINING_CATEGORY_BG[slot.training_item.category]
  return (
    <span
      style={{
        display: 'inline-block',
        fontSize: 12,
        padding: '4px 8px',
        border: `2px solid ${style?.border || 'var(--tr-border)'}`,
        background: style?.bg || 'rgba(255,255,255,0.86)',
        color: style?.text ? undefined : 'var(--tr-text)',
        fontWeight: 900,
      }}
      className={style?.text || ''}
    >
      {slot.training_item.name}
    </span>
  )
}
