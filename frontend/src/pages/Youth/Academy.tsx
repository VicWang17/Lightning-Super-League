import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Tree,
  TrendingUp,
  Clock,
  Sparkles,
  Check,
  Cancel
} from '../../components/ui/pixel-icons'

// Mock 青训球员
const mockYouthPlayers = [
  { id: '1', name: '张小明', position: 'ST', age: 15, ovr: 32, growthSpeed: '快' as const, daysIn: 6, ovrHistory: [28, 29, 30, 31, 32, 34] },
  { id: '2', name: '李小红', position: 'CMF', age: 16, ovr: 30, growthSpeed: '中' as const, daysIn: 6, ovrHistory: [28, 29, 29, 30, 30, 31] },
  { id: '3', name: '王小强', position: 'CB', age: 17, ovr: 28, growthSpeed: '慢' as const, daysIn: 6, ovrHistory: [27, 27, 28, 28, 28, 28] },
]

const mockFacility = {
  level: 2,
  name: '标准',
  bonus: '+15%',
  upgradeCost: 150,
  maintenance: 10,
}

const mockBudget = {
  ratio: 15,
  balance: 45,
}

export default function YouthAcademy() {
  const [selectedPlayer, setSelectedPlayer] = useState<string | null>(null)

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">青训营</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">观察年轻球员成长，赛季末签约潜力新星</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/youth/draft" className="btn-secondary text-sm">选秀大会</Link>
          <Link to="/youth/young-players" className="btn-secondary text-sm">年轻球员</Link>
        </div>
      </div>

      {/* 青训概况 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Tree className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">青训投入比例</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">{mockBudget.ratio}%</p>
          <p className="text-xs text-[#4B4B6A] mt-1">每赛季自动划拨</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">青训基金余额</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">{mockBudget.balance}万</p>
          <p className="text-xs text-[#4B4B6A] mt-1">用于设施维护与签约</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">设施等级</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">{mockFacility.level}级</p>
          <p className="text-xs text-[#0D7377] mt-1">成长速度{mockFacility.bonus}</p>
        </div>
      </div>

      {/* 刷新倒计时 */}
      <div className="bg-[#0D4A4D]/20 border-2 border-[#0D7377]/30 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#E2E2F0]">距下次青训刷新还有 <span className="text-[#0D7377] font-bold">2天</span></span>
          </div>
          <span className="text-xs text-[#4B4B6A]">当前在营: {mockYouthPlayers.length}/8人</span>
        </div>
      </div>

      {/* 球员列表 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">在营球员</h3>
          <span className="text-xs text-[#4B4B6A]">成长速度 = 潜力高低</span>
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {mockYouthPlayers.map((p) => (
            <div 
              key={p.id} 
              className={clsx(
                'bg-[#0A0A0F] border-2 p-4 transition-all cursor-pointer',
                selectedPlayer === p.id ? 'border-[#0D7377] shadow-pixel-green' : 'border-[#2D2D44] hover:border-[#0D7377]/50'
              )}
              onClick={() => setSelectedPlayer(selectedPlayer === p.id ? null : p.id)}
            >
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h4 className="font-bold text-white">{p.name}</h4>
                  <p className="text-xs text-[#8B8BA7]">{p.position} · {p.age}岁 · 入营{p.daysIn}天</p>
                </div>
                <span className={clsx(
                  'text-xs px-2 py-0.5 font-bold border',
                  p.growthSpeed === '快' ? 'text-emerald-400 border-emerald-400/30 bg-emerald-500/10' :
                  p.growthSpeed === '中' ? 'text-yellow-400 border-yellow-400/30 bg-yellow-500/10' :
                  'text-[#4B4B6A] border-[#2D2D44]'
                )}>
                  {p.growthSpeed}速成长
                </span>
              </div>

              <div className="flex items-center justify-between mb-3">
                <span className="text-xs text-[#8B8BA7]">当前OVR</span>
                <span className="text-xl font-bold stat-number">{p.ovr}</span>
              </div>

              {/* 成长曲线 - 简化版 */}
              <div className="mb-3">
                <p className="text-xs text-[#4B4B6A] mb-1">成长曲线</p>
                <div className="flex items-end gap-1 h-16">
                  {p.ovrHistory.map((val, i) => (
                    <div key={i} className="flex-1 flex flex-col items-center gap-1">
                      <div 
                        className="w-full bg-[#0D7377] min-h-[2px]"
                        style={{ height: `${(val / 50) * 100}%` }}
                      />
                      <span className="text-[8px] text-[#4B4B6A]">D{i+1}</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* 操作按钮 */}
              <div className="flex gap-2 pt-3 border-t-2 border-[#2D2D44]">
                <button className="flex-1 px-3 py-2 bg-emerald-500/20 text-emerald-400 text-xs font-bold border-2 border-emerald-500/30 hover:bg-emerald-500/30 transition-colors">
                  <Check className="w-3 h-3 inline mr-1" />
                  签约
                </button>
                <button className="flex-1 px-3 py-2 bg-red-500/20 text-red-400 text-xs font-bold border-2 border-red-500/30 hover:bg-red-500/30 transition-colors">
                  <Cancel className="w-3 h-3 inline mr-1" />
                  放弃
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 设施升级 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">青训设施</h3>
        <div className="flex items-center gap-6">
          <div className="w-20 h-20 bg-[#0D4A4D] border-2 border-[#0D7377]/30 flex items-center justify-center">
            <Tree className="w-8 h-8 text-[#0D7377]" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h4 className="font-bold text-white">{mockFacility.name}设施</h4>
              <span className="text-xs px-2 py-0.5 bg-[#0D7377]/20 text-[#0D7377] border border-[#0D7377]/30">Lv.{mockFacility.level}</span>
            </div>
            <p className="text-sm text-[#8B8BA7]">成长速度加成: {mockFacility.bonus}</p>
            <p className="text-xs text-[#4B4B6A] mt-1">维护费: {mockFacility.maintenance}万/赛季</p>
          </div>
          <button className="px-4 py-2 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors">
            升级 ({mockFacility.upgradeCost}万)
          </button>
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
