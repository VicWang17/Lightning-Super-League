import { useState } from 'react'
import { Calendar, Clock, Zap, Shield, Target } from '../../components/ui/pixel-icons'

const weeks = ['第 12 周', '第 11 周', '第 10 周', '第 9 周']

const weekData: Record<string, Array<{ day: string; am: string; pm: string; eve: string; intensity: number }>> = {
  '第 12 周': [
    { day: '周一', am: '射门特训', pm: '进攻战术', eve: '轻度拉伸', intensity: 75 },
    { day: '周二', am: '传球特训', pm: '防守站位', eve: '录像分析', intensity: 70 },
    { day: '周三', am: '体能特训', pm: '团队配合', eve: '按摩恢复', intensity: 85 },
    { day: '周四', am: '全队休息', pm: '轻度拉伸', eve: '全队休息', intensity: 20 },
    { day: '周五', am: '盘带特训', pm: '定位球专项', eve: '战术课堂', intensity: 72 },
    { day: '周六', am: '友谊赛模拟', pm: '进攻战术', eve: '轻度拉伸', intensity: 80 },
    { day: '周日', am: '全队休息', pm: '全队休息', eve: '按摩恢复', intensity: 15 },
  ],
  '第 11 周': [
    { day: '周一', am: '防守特训', pm: '防守站位', eve: '轻度拉伸', intensity: 68 },
    { day: '周二', am: '传球特训', pm: '进攻战术', eve: '录像分析', intensity: 70 },
    { day: '周三', am: '射门特训', pm: '团队配合', eve: '按摩恢复', intensity: 78 },
    { day: '周四', am: '全队休息', pm: '轻度拉伸', eve: '全队休息', intensity: 18 },
    { day: '周五', am: '体能特训', pm: '定位球专项', eve: '战术课堂', intensity: 82 },
    { day: '周六', am: '盘带特训', pm: '进攻战术', eve: '轻度拉伸', intensity: 75 },
    { day: '周日', am: '全队休息', pm: '全队休息', eve: '按摩恢复', intensity: 15 },
  ],
  '第 10 周': [
    { day: '周一', am: '头球特训', pm: '防守站位', eve: '轻度拉伸', intensity: 65 },
    { day: '周二', am: '传球特训', pm: '进攻战术', eve: '录像分析', intensity: 68 },
    { day: '周三', am: '射门特训', pm: '团队配合', eve: '按摩恢复', intensity: 76 },
    { day: '周四', am: '全队休息', pm: '轻度拉伸', eve: '全队休息', intensity: 18 },
    { day: '周五', am: '体能特训', pm: '定位球专项', eve: '战术课堂', intensity: 80 },
    { day: '周六', am: '点球特训', pm: '进攻战术', eve: '轻度拉伸', intensity: 72 },
    { day: '周日', am: '全队休息', pm: '全队休息', eve: '按摩恢复', intensity: 15 },
  ],
  '第 9 周': [
    { day: '周一', am: '防守特训', pm: '防守站位', eve: '轻度拉伸', intensity: 66 },
    { day: '周二', am: '传球特训', pm: '进攻战术', eve: '录像分析', intensity: 69 },
    { day: '周三', am: '射门特训', pm: '团队配合', eve: '按摩恢复', intensity: 77 },
    { day: '周四', am: '全队休息', pm: '轻度拉伸', eve: '全队休息', intensity: 18 },
    { day: '周五', am: '体能特训', pm: '定位球专项', eve: '战术课堂', intensity: 81 },
    { day: '周六', am: '任意球特训', pm: '进攻战术', eve: '轻度拉伸', intensity: 74 },
    { day: '周日', am: '全队休息', pm: '全队休息', eve: '按摩恢复', intensity: 15 },
  ],
}

function getIntensityColor(v: number) {
  if (v >= 80) return 'bg-red-500'
  if (v >= 60) return 'bg-yellow-500'
  return 'bg-emerald-500'
}

function getIntensityText(v: number) {
  if (v >= 80) return 'text-red-400'
  if (v >= 60) return 'text-yellow-400'
  return 'text-emerald-400'
}

export default function TrainingCalendar() {
  const [selectedWeek, setSelectedWeek] = useState(weeks[0])
  const data = weekData[selectedWeek]

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-2xl font-bold text-white">训练日历</h1>
        <p className="text-sm text-[#8B8BA7] mt-1">查看过去训练记录与比赛成绩关联</p>
      </div>

      <div className="flex gap-2">
        {weeks.map((w) => (
          <button
            key={w}
            onClick={() => setSelectedWeek(w)}
            className={clsx(
              'px-4 py-2 border-2 text-sm font-medium transition-all duration-200',
              selectedWeek === w
                ? 'bg-[#0D7377] border-[#0A5A5D] text-white shadow-pixel-green'
                : 'bg-[#0A0A0F] border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50 hover:text-white'
            )}
          >
            {w}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Zap className="w-4 h-4 text-yellow-500" />
            <span className="text-sm text-[#8B8BA7]">平均强度</span>
          </div>
          <p className="text-2xl font-bold text-white">
            {Math.round(data.reduce((s, d) => s + d.intensity, 0) / 7)}%
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Target className="w-4 h-4 text-blue-400" />
            <span className="text-sm text-[#8B8BA7]">战术训练</span>
          </div>
          <p className="text-2xl font-bold text-white">3 次</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Shield className="w-4 h-4 text-red-400" />
            <span className="text-sm text-[#8B8BA7]">技术训练</span>
          </div>
          <p className="text-2xl font-bold text-white">5 次</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">恢复训练</span>
          </div>
          <p className="text-2xl font-bold text-white">4 次</p>
        </div>
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Calendar className="w-4 h-4 text-[#0D7377]" />
          {selectedWeek} 训练明细
        </h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-[#2D2D44]">
                <th className="text-left text-xs text-[#4B4B6A] py-2 pr-4">日期</th>
                <th className="text-left text-xs text-[#4B4B6A] py-2 px-3">上午</th>
                <th className="text-left text-xs text-[#4B4B6A] py-2 px-3">下午</th>
                <th className="text-left text-xs text-[#4B4B6A] py-2 px-3">晚上</th>
                <th className="text-left text-xs text-[#4B4B6A] py-2 pl-3">强度</th>
              </tr>
            </thead>
            <tbody>
              {data.map((row) => (
                <tr key={row.day} className="border-b border-[#2D2D44]/50">
                  <td className="py-3 pr-4 text-sm text-white font-medium">{row.day}</td>
                  <td className="py-3 px-3 text-sm text-[#8B8BA7]">{row.am}</td>
                  <td className="py-3 px-3 text-sm text-[#8B8BA7]">{row.pm}</td>
                  <td className="py-3 px-3 text-sm text-[#8B8BA7]">{row.eve}</td>
                  <td className="py-3 pl-3">
                    <div className="flex items-center gap-2">
                      <div className="pixel-progress-track h-2 w-24">
                        <div
                          className={clsx('pixel-progress-fill h-full', getIntensityColor(row.intensity))}
                          style={{ width: `${row.intensity}%` }}
                        />
                      </div>
                      <span className={clsx('text-xs', getIntensityText(row.intensity))}>
                        {row.intensity}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4">训练强度 vs 比赛成绩</h3>
        <div className="h-48 flex items-end gap-4 px-4 pb-4 border-b-2 border-[#2D2D44]">
          {weeks.map((w, i) => {
            const avg = Math.round(weekData[w].reduce((s, d) => s + d.intensity, 0) / 7)
            const results = [3, 1, 3, 0]
            return (
              <div key={w} className="flex-1 flex flex-col items-center gap-2">
                <div className="flex items-center gap-1">
                  <span className="text-xs text-[#8B8BA7]">{results[i]}分</span>
                </div>
                <div
                  className="w-full bg-[#0D7377]/30 border border-[#0D7377]/50"
                  style={{ height: `${avg * 1.8}px` }}
                />
                <span className="text-xs text-[#4B4B6A]">{w}</span>
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
