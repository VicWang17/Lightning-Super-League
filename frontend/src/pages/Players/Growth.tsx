import { useParams, Link } from 'react-router-dom'
import { useEffect, useState, useMemo } from 'react'
import { Card } from '../../components/ui/Card'
import { PlayerTabs } from '../../components/players/PlayerTabs'
import { api } from '../../api/client'
import type { PlayerGrowthData } from '../../types/player'

function PlayerGrowth() {
  const { id } = useParams<{ id: string }>()
  const [data, setData] = useState<PlayerGrowthData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    api.get<PlayerGrowthData>(`/players/${id}/growth`)
      .then(res => {
        if (res.success) {
          setData(res.data)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [id])

  const chartBars = useMemo(() => {
    if (!data) return []
    const maxOvr = Math.max(...data.projected_curve.map(p => p.ovr), 1)
    const minOvr = Math.min(...data.projected_curve.map(p => p.ovr), 1)
    const range = maxOvr - minOvr || 1
    return data.projected_curve.map(point => ({
      ...point,
      heightPct: ((point.ovr - minOvr) / range) * 60 + 20,
    }))
  }, [data])

  if (loading) {
    return <div className="max-w-[1200px] p-8 text-center text-[#466353]">加载中...</div>
  }

  if (!data) {
    return <div className="max-w-[1200px] p-8 text-center text-[#FF6F59]">数据加载失败</div>
  }

  return (
    <div className="max-w-[1200px]">
      <Link
        to={`/players/${id}`}
        className="text-sm text-[#466353] hover:text-[#173126] transition-colors mb-4"
      >
        返回球员档案
      </Link>

      <PlayerTabs playerId={id!} />

      {/* 成长概览 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        <Card>
          <div className="mb-2">
            <span className="text-xs text-[#466353]">当前年龄 / OVR</span>
          </div>
          <div className="text-2xl font-bold stat-number pixel-number text-[#173126]">
            {data.current_age} 岁 / {data.current_ovr}
          </div>
        </Card>
        <Card>
          <div className="mb-2">
            <span className="text-xs text-[#466353]">巅峰年龄</span>
          </div>
          <div className="text-2xl font-bold stat-number pixel-number text-[#173126]">
            {data.peak_age} 岁
          </div>
        </Card>
        <Card>
          <div className="mb-2">
            <span className="text-xs text-[#466353]">成长类型</span>
          </div>
          <div className="text-2xl font-bold stat-number pixel-number text-[#1F5F43]">
            {data.curve_type_label}
          </div>
        </Card>
        <Card>
          <div className="mb-2">
            <span className="text-xs text-[#466353]">成长速度</span>
          </div>
          <div className="text-2xl font-bold stat-number pixel-number text-[#173126]">
            {data.growth_speed.toFixed(2)}x
          </div>
        </Card>
      </div>

      {/* 成长曲线图表 */}
      <Card className="mb-6">
        <h3 className="text-lg font-semibold mb-6">
          能力成长曲线（预测）
        </h3>

        <div className="relative h-64 flex items-end gap-1 md:gap-2 px-2">
          {chartBars.map((bar) => {
            const isCurrent = bar.age === data.current_age
            const isPast = bar.age < data.current_age
            return (
              <div key={bar.age} className="flex-1 flex flex-col items-center gap-1">
                <div className="relative w-full flex justify-center">
                  <div
                    className={`w-full max-w-[20px] transition-all ${
                      isCurrent
                        ? 'bg-[#B9EF3F]'
                        : isPast
                        ? 'bg-[#1F5F43]/50'
                        : 'bg-[#1F5F43]'
                    }`}
                    style={{ height: `${bar.heightPct * 2.5}px` }}
                  />
                  {isCurrent && (
                    <div className="absolute -top-5 text-xs font-bold text-[#1F5F43]">
                      {bar.ovr}
                    </div>
                  )}
                </div>
                <span className={`text-[10px] ${isCurrent ? 'text-[#1F5F43] font-bold' : 'text-[#466353]'}`}>
                  {bar.age}
                </span>
              </div>
            )
          })}
        </div>

        <div className="flex items-center gap-4 mt-4 text-xs text-[#466353]">
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 bg-[#1F5F43]/50" />
            <span>过往（推算）</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 bg-[#B9EF3F]" />
            <span>当前</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div className="w-3 h-3 bg-[#1F5F43]" />
            <span>未来（预测）</span>
          </div>
        </div>
      </Card>

      {/* 属性成长进度 */}
      <Card>
        <h3 className="text-lg font-semibold mb-4">
          属性成长进度（当前值 / 隐藏上限）
        </h3>

        {data.attribute_progress.length === 0 ? (
          <p className="text-[#466353] text-center py-8">暂无属性成长数据</p>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {data.attribute_progress.map((attr) => (
              <div key={attr.attribute} className="p-3 bg-[#FFF8DC]/80">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm">{attr.label}</span>
                  <span className="text-sm font-bold stat-number pixel-number">
                    <span className="text-[#173126]">{attr.current}</span>
                    <span className="text-[#466353]"> / </span>
                    <span className="text-[#1F5F43]">{attr.cap.toFixed(1)}</span>
                  </span>
                </div>
                <div className="pixel-progress-track">
                  <div
                    className={`pixel-progress-fill ${
                      attr.progress_pct >= 90
                        ? 'bg-[#FF6F59]'
                        : attr.progress_pct >= 70
                        ? 'bg-[#FFC247]'
                        : 'bg-[#1F5F43]'
                    }`}
                    style={{ width: `${Math.min(100, attr.progress_pct)}%` }}
                  />
                </div>
                <div className="text-right mt-1">
                  <span className={`text-xs ${
                    attr.progress_pct >= 90 ? 'text-[#FF6F59]' : 'text-[#466353]'
                  }`}>
                    {attr.progress_pct.toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}

export default PlayerGrowth
