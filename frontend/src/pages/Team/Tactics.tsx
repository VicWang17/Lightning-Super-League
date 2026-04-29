import { useState } from 'react'
import { 
  Sword, 
  Target,
  Download
} from '../../components/ui/pixel-icons'

// 七人制阵型定义
const formations = [
  { id: '1-2-3', name: '1-2-3', label: '进攻型', desc: '1门将 + 2后卫 + 3前锋', attack: 85, defense: 45, control: 50 },
  { id: '1-3-2', name: '1-3-2', label: '均衡型', desc: '1门将 + 3中场 + 2前锋', attack: 60, defense: 60, control: 70 },
  { id: '2-1-3', name: '2-1-3', label: '控球型', desc: '2后卫 + 1后腰 + 3前锋', attack: 70, defense: 50, control: 80 },
  { id: '2-3-1', name: '2-3-1', label: '防守反击', desc: '2后卫 + 3中场 + 1前锋', attack: 45, defense: 80, control: 60 },
  { id: '1-1-4', name: '1-1-4', label: '全攻型', desc: '1门将 + 1后卫 + 4前锋', attack: 95, defense: 30, control: 40 },
]

// 战术心态
const mentalities = [
  { id: 'ultra-attacking', name: '全力进攻', desc: '高风险高回报', color: 'text-red-400' },
  { id: 'attacking', name: '积极进攻', desc: '主动压迫', color: 'text-orange-400' },
  { id: 'balanced', name: '攻守平衡', desc: '标准打法', color: 'text-[#0D7377]' },
  { id: 'defensive', name: '稳守反击', desc: '收缩防线', color: 'text-blue-400' },
  { id: 'ultra-defensive', name: '死守', desc: '铁桶阵', color: 'text-[#4B4B6A]' },
]

// Mock 球员
const mockPlayers = [
  { id: '1', name: '王强', position: 'GK', ovr: 72, x: 50, y: 90 },
  { id: '2', name: '李明', position: 'CB', ovr: 68, x: 35, y: 65 },
  { id: '3', name: '张伟', position: 'CB', ovr: 70, x: 65, y: 65 },
  { id: '4', name: '刘洋', position: 'CMF', ovr: 74, x: 50, y: 50 },
  { id: '5', name: '陈浩', position: 'WF', ovr: 71, x: 20, y: 30 },
  { id: '6', name: '赵雷', position: 'ST', ovr: 76, x: 50, y: 20 },
  { id: '7', name: '孙凯', position: 'WF', ovr: 69, x: 80, y: 30 },
]

const positionColors: Record<string, string> = {
  GK: 'bg-amber-500',
  CB: 'bg-blue-500',
  DMF: 'bg-blue-400',
  CMF: 'bg-emerald-500',
  AMF: 'bg-emerald-400',
  WF: 'bg-red-400',
  ST: 'bg-red-500',
}

export default function Tactics() {
  const [selectedFormation, setSelectedFormation] = useState(formations[1])
  const [selectedMentality, setSelectedMentality] = useState(mentalities[2])
  const [saved, setDownloadd] = useState(false)

  const handleDownload = () => {
    setDownloadd(true)
    setTimeout(() => setDownloadd(false), 2000)
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">战术设置</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">配置阵型、心态与战术指令</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            onClick={handleDownload}
            className="btn-primary flex items-center gap-2"
          >
            <Download className="w-4 h-4" />
            {saved ? '已保存!' : '保存战术'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧 - 阵型选择 */}
        <div className="space-y-6">
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Target className="w-4 h-4 text-[#0D7377]" />
              阵型选择
            </h3>
            <div className="space-y-2">
              {formations.map((f) => (
                <button
                  key={f.id}
                  onClick={() => setSelectedFormation(f)}
                  className={clsx(
                    'w-full text-left p-3 border-2 transition-all duration-200',
                    selectedFormation.id === f.id
                      ? 'bg-[#0D7377]/20 border-[#0D7377] shadow-pixel-green'
                      : 'bg-[#0A0A0F] border-[#2D2D44] hover:border-[#0D7377]/50'
                  )}
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-bold text-white">{f.name}</p>
                      <p className="text-xs text-[#8B8BA7]">{f.desc}</p>
                    </div>
                    <span className={clsx(
                      'text-xs px-2 py-0.5 border',
                      f.label === '进攻型' || f.label === '全攻型' ? 'text-red-400 border-red-400/30' :
                      f.label === '防守反击' || f.label === '防守型' ? 'text-blue-400 border-blue-400/30' :
                      'text-[#0D7377] border-[#0D7377]/30'
                    )}>
                      {f.label}
                    </span>
                  </div>
                </button>
              ))}
            </div>
          </div>

          {/* 战术心态 */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
              <Sword className="w-4 h-4 text-[#0D7377]" />
              比赛心态
            </h3>
            <div className="space-y-2">
              {mentalities.map((m) => (
                <button
                  key={m.id}
                  onClick={() => setSelectedMentality(m)}
                  className={clsx(
                    'w-full text-left p-3 border-2 transition-all duration-200',
                    selectedMentality.id === m.id
                      ? 'bg-[#0D7377]/20 border-[#0D7377] shadow-pixel-green'
                      : 'bg-[#0A0A0F] border-[#2D2D44] hover:border-[#0D7377]/50'
                  )}
                >
                  <p className={clsx('font-bold', selectedMentality.id === m.id ? m.color : 'text-white')}>
                    {m.name}
                  </p>
                  <p className="text-xs text-[#8B8BA7]">{m.desc}</p>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 中间 - 战术板 */}
        <div className="lg:col-span-2 space-y-6">
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">战术板</h3>
              <div className="flex items-center gap-2 text-xs text-[#8B8BA7]">
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-amber-500"/>门将</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-blue-500"/>后卫</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-emerald-500"/>中场</span>
                <span className="flex items-center gap-1"><span className="w-2 h-2 bg-red-500"/>前锋</span>
              </div>
            </div>
            
            {/* 球场 */}
            <div className="relative w-full aspect-[3/4] bg-[#065F46] border-4 border-[#2D2D44] overflow-hidden"
              style={{
                backgroundImage: `
                  linear-gradient(rgba(255,255,255,0.05) 1px, transparent 1px),
                  linear-gradient(90deg, rgba(255,255,255,0.05) 1px, transparent 1px)
                `,
                backgroundSize: '20px 20px'
              }}
            >
              {/* 球场白线 */}
              <div className="absolute inset-4 border-2 border-white/30" />
              <div className="absolute top-1/2 left-4 right-4 h-px bg-white/30" />
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-20 h-20 border-2 border-white/30 rounded-full" />
              
              {/* 球员 */}
              {mockPlayers.map((player) => (
                <div
                  key={player.id}
                  className="absolute -translate-x-1/2 -translate-y-1/2 cursor-pointer group"
                  style={{ left: `${player.x}%`, top: `${player.y}%` }}
                >
                  <div className={clsx(
                    'w-10 h-10 border-2 border-white/80 flex items-center justify-center shadow-pixel transition-all group-hover:scale-110',
                    positionColors[player.position] || 'bg-[#2D2D44]'
                  )}>
                    <span className="text-xs font-bold text-white">{player.position}</span>
                  </div>
                  <div className="absolute -bottom-5 left-1/2 -translate-x-1/2 whitespace-nowrap">
                    <p className="text-[10px] text-white bg-black/60 px-1">{player.name}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 属性对比 */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">战术属性</h3>
            <div className="grid grid-cols-3 gap-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">进攻倾向</span>
                  <span className="text-sm font-bold stat-number text-red-400">{selectedFormation.attack}</span>
                </div>
                <div className="pixel-progress-track">
                  <div className="pixel-progress-fill bg-red-500" style={{ width: `${selectedFormation.attack}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">防守稳固</span>
                  <span className="text-sm font-bold stat-number text-blue-400">{selectedFormation.defense}</span>
                </div>
                <div className="pixel-progress-track">
                  <div className="pixel-progress-fill bg-blue-500" style={{ width: `${selectedFormation.defense}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">控球能力</span>
                  <span className="text-sm font-bold stat-number text-emerald-400">{selectedFormation.control}</span>
                </div>
                <div className="pixel-progress-track">
                  <div className="pixel-progress-fill bg-emerald-500" style={{ width: `${selectedFormation.control}%` }} />
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
