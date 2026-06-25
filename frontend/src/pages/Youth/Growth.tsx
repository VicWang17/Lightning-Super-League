import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import { Loader, TrendingUp } from '../../components/ui/pixel-icons'
import { PageHeader } from '../../components/ui/PageHeader'
import { YouthTabs } from '../../components/youth/YouthTabs'
import { Card, CardContent, CardHeader } from '../../components/ui/Card'
import Avatar from '../../components/ui/Avatar'
import { useYouthAcademy } from '../../hooks/useYouthAcademy'
import { useAcademyGrowth } from '../../hooks/useAcademyGrowth'

const positionColors: Record<string, string> = {
  FW: 'bg-[#FF6F59] text-[#F8FFD2]',
  MF: 'bg-[#1F5F43] text-[#173126]',
  DF: 'bg-[#59C7EE] text-[#173126]',
  GK: 'bg-[#FFC247] text-[#173126]',
}

export default function YouthGrowth() {
  const { data, loading, error } = useYouthAcademy()
  const players = data?.players ?? []
  const [selectedId, setSelectedId] = useState<string | null>(players[0]?.academy_player_id ?? null)

  const selectedPlayer = useMemo(
    () => players.find((p) => p.academy_player_id === selectedId) ?? null,
    [players, selectedId]
  )

  const { data: growthData, loading: growthLoading } = useAcademyGrowth(selectedId)

  const chartData = useMemo(
    () =>
      growthData.map((d) => ({
        day: d.season_day,
        ovr: d.ovr,
      })),
    [growthData]
  )

  if (loading) {
    return (
      <div className="max-w-[1400px] p-8 text-center text-[#466353]">
        <Loader className="w-6 h-6 animate-spin mx-auto mb-2" />
        加载青训数据中...
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-[1400px] p-8">
        <div className="p-4 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <Link
        to="/youth/academy"
        className="inline-flex items-center gap-1 text-sm text-[#466353] hover:text-[#173126] transition-colors"
      >
        返回青训营
      </Link>

      <PageHeader
        title="青训成长曲线"
        subtitle="对比青训球员在营期间的 OVR 变化"
      />

      <YouthTabs />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader title="选择球员" />
          <CardContent className="p-4">
            {players.length === 0 ? (
              <p className="text-sm text-[#466353] text-center py-8">暂无在营球员</p>
            ) : (
              <div className="space-y-2 max-h-[480px] overflow-y-auto pr-1">
                {players.map((p) => {
                  const isSelected = selectedId === p.academy_player_id
                  return (
                    <button
                      key={p.academy_player_id}
                      onClick={() => setSelectedId(p.academy_player_id)}
                      className={`w-full flex items-center gap-3 p-2 text-left border-2 transition-all ${
                        isSelected
                          ? 'border-[#1F5F43] bg-[#B9EF3F]/20'
                          : 'border-[#1F5F43]/10 bg-white/50 hover:border-[#1F5F43]/30'
                      }`}
                    >
                      <Avatar
                        src={p.avatar_url ? `/${p.avatar_url}` : undefined}
                        name={p.name}
                        size="sm"
                      />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-bold text-[#173126] truncate">{p.name}</span>
                          <span className={`text-[10px] px-1.5 py-0.5 font-bold ${positionColors[p.position] || 'bg-[#F8FFD2] text-[#173126]'}`}>
                            {p.position}
                          </span>
                        </div>
                        <div className="text-xs text-[#466353]">
                          OVR {p.ovr} · 潜力 {p.potential_letter} · 入营第{p.joined_day}天
                        </div>
                      </div>
                    </button>
                  )
                })}
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader
            title={selectedPlayer ? `${selectedPlayer.name} 的成长曲线` : '成长曲线'}
            subtitle={selectedPlayer ? `OVR ${selectedPlayer.ovr} · 潜力 ${selectedPlayer.potential_letter}` : '请选择球员'}
          />
          <CardContent className="p-4">
            {!selectedPlayer ? (
              <p className="text-sm text-[#466353] text-center py-16">请先选择左侧球员</p>
            ) : growthLoading ? (
              <div className="text-center py-16 text-[#466353]">
                <Loader className="w-5 h-5 animate-spin mx-auto mb-2" />
                加载成长曲线...
              </div>
            ) : chartData.length === 0 ? (
              <p className="text-sm text-[#466353] text-center py-16">暂无成长记录</p>
            ) : (
              <>
                <div className="flex items-center gap-2 mb-4">
                  <TrendingUp className="w-4 h-4 text-[#1F5F43]" />
                  <span className="text-xs text-[#466353]">
                    OVR {Math.min(...chartData.map((d) => d.ovr))} → {Math.max(...chartData.map((d) => d.ovr))}
                  </span>
                </div>
                <div className="h-72">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={chartData} margin={{ top: 8, right: 16, bottom: 8, left: -16 }}>
                      <CartesianGrid stroke="rgba(31,95,67,0.12)" />
                      <XAxis
                        dataKey="day"
                        tick={{ fill: '#466353', fontSize: 12 }}
                        stroke="#1F5F43"
                        label={{ value: '赛季天数', position: 'insideBottom', offset: -2, fill: '#466353', fontSize: 12 }}
                      />
                      <YAxis
                        domain={['dataMin - 1', 'dataMax + 1']}
                        tick={{ fill: '#466353', fontSize: 12 }}
                        stroke="#1F5F43"
                      />
                      <Tooltip
                        contentStyle={{
                          background: '#FFF8DC',
                          border: '2px solid #1F5F43',
                          borderRadius: 0,
                          fontSize: 12,
                        }}
                        labelStyle={{ color: '#466353' }}
                        itemStyle={{ color: '#173126' }}
                        formatter={(value: number) => [`OVR ${value}`, '']}
                        labelFormatter={(day: number) => `第 ${day} 天`}
                      />
                      <Line
                        type="monotone"
                        dataKey="ovr"
                        stroke="#1F5F43"
                        strokeWidth={2}
                        dot={{ r: 3, fill: '#B9EF3F', stroke: '#1F5F43', strokeWidth: 2 }}
                        activeDot={{ r: 5, fill: '#FFC247' }}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
