import { useEffect, useState, useMemo } from 'react'
import { api } from '../../api/client'
import type { TrainingResultItem } from '../../types/training'
import { Card } from '../../components/ui/Card'
import { TrainingPageShell } from './components/TrainingPageShell'

const categoryColors: Record<string, string> = {
  '战术': 'text-[#1F5F43] bg-[#59C7EE]/15 border-[#59C7EE]/40',
  '技术': 'text-[#173126] bg-[#FF6F59]/12 border-[#FF6F59]/40',
  '恢复': 'text-[#173126] bg-[#B9EF3F]/20 border-[#B9EF3F]/60',
  'tactic': 'text-[#1F5F43] bg-[#59C7EE]/15 border-[#59C7EE]/40',
  'technical': 'text-[#173126] bg-[#FF6F59]/12 border-[#FF6F59]/40',
  'recovery': 'text-[#173126] bg-[#B9EF3F]/20 border-[#B9EF3F]/60',
}

interface AggregatedResult {
  training_item_id: string
  training_item_name: string
  category: string
  count: number
  totalFitnessDelta: number
  totalFatigueDelta: number
  totalBreakthroughs: number
}

export default function TrainingHistory() {
  const [results, setResults] = useState<TrainingResultItem[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState<string>('全部')
  const categories = ['全部', '战术', '技术', '恢复']

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
        const resultsRes = await api.getTrainingResults(teamRes.data.id, seasonRes.data.id, { limit: 200 })
        if (!cancelled && resultsRes.success && Array.isArray(resultsRes.data)) {
          setResults(resultsRes.data)
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

  const aggregated = useMemo(() => {
    const map = new Map<string, AggregatedResult>()
    for (const r of results) {
      const key = r.training_item_id
      const existing = map.get(key)
      if (existing) {
        existing.count += 1
        existing.totalFitnessDelta += r.fitness_after - r.fitness_before
        existing.totalFatigueDelta += r.fatigue_after - r.fatigue_before
        existing.totalBreakthroughs += r.breakthroughs?.length ?? 0
      } else {
        // 推断分类：有 attribute_gains 的是技术，有 fitness_delta 正向的是恢复
        let category = '技术'
        if (r.training_item_name?.includes('休息') || r.training_item_name?.includes('恢复') || r.training_item_name?.includes('拉伸') || r.training_item_name?.includes('按摩')) {
          category = '恢复'
        } else if (r.training_item_name?.includes('战术') || r.training_item_name?.includes('站位') || r.training_item_name?.includes('配合')) {
          category = '战术'
        }
        map.set(key, {
          training_item_id: r.training_item_id,
          training_item_name: r.training_item_name || r.training_item_id,
          category,
          count: 1,
          totalFitnessDelta: r.fitness_after - r.fitness_before,
          totalFatigueDelta: r.fatigue_after - r.fatigue_before,
          totalBreakthroughs: r.breakthroughs?.length ?? 0,
        })
      }
    }
    return Array.from(map.values())
  }, [results])

  const filtered = useMemo(() => {
    if (filter === '全部') return aggregated
    return aggregated.filter(r => r.category === filter)
  }, [aggregated, filter])

  const totalSessions = aggregated.reduce((s, r) => s + r.count, 0)
  const totalBreakthroughs = aggregated.reduce((s, r) => s + r.totalBreakthroughs, 0)
  const techCount = aggregated.filter(r => r.category === '技术').reduce((s, r) => s + r.count, 0)
  const tacticCount = aggregated.filter(r => r.category === '战术').reduce((s, r) => s + r.count, 0)

  if (loading) {
    return (
      <TrainingPageShell title="训练执行统计" subtitle="训练执行统计与效果分析">
        <div className="p-8 text-center text-[#466353]">加载中...</div>
      </TrainingPageShell>
    )
  }

  return (
    <TrainingPageShell title="训练执行统计" subtitle="训练执行统计与效果分析">
      <div className="space-y-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-[#466353]">总训练人次</span>
          </div>
          <p className="text-2xl font-bold text-[#173126]">{totalSessions} 次</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-[#466353]">技术训练</span>
          </div>
          <p className="text-2xl font-bold text-[#173126]">{techCount} 次</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-[#466353]">战术训练</span>
          </div>
          <p className="text-2xl font-bold text-[#173126]">{tacticCount} 次</p>
        </Card>
        <Card>
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm text-[#466353]">属性突破</span>
          </div>
          <p className="text-2xl font-bold text-[#173126]">{totalBreakthroughs} 次</p>
        </Card>
      </div>

      <div className="flex gap-2">
        {categories.map(c => (
          <button
            key={c}
            onClick={() => setFilter(c)}
            className={`px-4 py-2 border-2 text-sm font-medium transition-all duration-200 ${
              filter === c
                ? 'bg-[#1F5F43] border-[#173126] text-[#F8FFD2] shadow-pixel'
                : 'bg-[#FFF8DC] border-[#1F5F43]/20 text-[#466353] hover:border-[#1F5F43] hover:text-[#173126]'
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      <Card >
        <h3 className="text-lg font-semibold mb-4">训练执行统计</h3>
        {filtered.length === 0 ? (
          <p className="text-[#466353] text-center py-8">暂无训练记录</p>
        ) : (
          <div className="space-y-3">
            {filtered.map(r => {
              return (
                <div key={r.training_item_id} className="flex items-center gap-4 bg-white/70 border border-[#1F5F43]/20 p-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <p className="text-sm text-[#173126] font-medium">{r.training_item_name}</p>
                      <span className={`text-[10px] px-1.5 py-0.5 border ${categoryColors[r.category]}`}>
                        {r.category}
                      </span>
                    </div>
                    <p className="text-xs text-[#7b927f] mt-1">
                      体能{r.totalFitnessDelta > 0 ? '+' : ''}{r.totalFitnessDelta} ·
                      疲劳{r.totalFatigueDelta > 0 ? '+' : ''}{r.totalFatigueDelta} ·
                      突破 {r.totalBreakthroughs} 次
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-lg font-bold text-[#173126]">{r.count} 次</p>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </Card>

      {/* 最近训练明细 */}
      <Card >
        <h3 className="text-lg font-semibold mb-4">最近训练明细</h3>
        {results.length === 0 ? (
          <p className="text-[#466353] text-center py-8">暂无训练明细</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b-2 border-[#1F5F43]/20 text-[#466353]">
                  <th className="text-left py-3 px-2">球员</th>
                  <th className="text-left py-3 px-2">训练项目</th>
                  <th className="text-center py-3 px-2">第几天</th>
                  <th className="text-center py-3 px-2">时段</th>
                  <th className="text-center py-3 px-2">体能变化</th>
                  <th className="text-center py-3 px-2">疲劳变化</th>
                  <th className="text-center py-3 px-2">效率</th>
                </tr>
              </thead>
              <tbody>
                {results.slice(0, 50).map(r => (
                  <tr key={r.id} className="border-b border-[#1F5F43]/10 hover:bg-[#FFF8DC]/60 transition-colors">
                    <td className="py-3 px-2 text-[#173126]">{r.player_name || r.player_id}</td>
                    <td className="py-3 px-2 text-[#466353]">{r.training_item_name || r.training_item_id}</td>
                    <td className="py-3 px-2 text-center">{r.season_day}</td>
                    <td className="py-3 px-2 text-center text-[#466353]">{r.slot}</td>
                    <td className="py-3 px-2 text-center">
                      <span className={r.fitness_after > r.fitness_before ? 'text-[#1F5F43]' : 'text-[#FF6F59]'}>
                        {r.fitness_after > r.fitness_before ? '+' : ''}{r.fitness_after - r.fitness_before}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-center">
                      <span className={r.fatigue_after > r.fatigue_before ? 'text-[#FF6F59]' : 'text-[#1F5F43]'}>
                        {r.fatigue_after > r.fatigue_before ? '+' : ''}{r.fatigue_after - r.fatigue_before}
                      </span>
                    </td>
                    <td className="py-3 px-2 text-center text-[#C77A00]">{r.efficiency}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      </div>
    </TrainingPageShell>
  )
}
