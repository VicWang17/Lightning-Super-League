import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Check,
  Clock,
  WarningDiamond
} from '../../components/ui/pixel-icons'

// Mock 选秀池
const mockDraftPool = [
  { id: '1', name: '赵小华', position: 'WF', age: 18, ovr: 42, growthSpeed: '快' as const, source: '雷霆龙骑' },
  { id: '2', name: '钱小伟', position: 'CMF', age: 18, ovr: 40, growthSpeed: '中' as const, source: '南海蛟龙' },
  { id: '3', name: '孙小强', position: 'CB', age: 17, ovr: 38, growthSpeed: '快' as const, source: '北方狼队' },
  { id: '4', name: '李小明', position: 'ST', age: 18, ovr: 41, growthSpeed: '慢' as const, source: '东方明珠' },
  { id: '5', name: '周小军', position: 'GK', age: 17, ovr: 36, growthSpeed: '中' as const, source: '西部雄鹰' },
]

export default function Draft() {
  const [draftOrder] = useState<string[]>(mockDraftPool.map(p => p.id))
  const [excluded, setExcluded] = useState<string[]>([])
  const [phase] = useState<'voting' | 'result' | 'signing'>('voting')

  const toggleExclude = (id: string) => {
    setExcluded(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
  }

  const getPlayerById = (id: string) => mockDraftPool.find(p => p.id === id)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">选秀大会</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">志愿优先级排序，系统自动分配</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/youth/academy" className="btn-secondary text-sm">青训营</Link>
        </div>
      </div>

      {/* 阶段提示 */}
      {phase === 'voting' && (
        <div className="bg-[#0D4A4D]/20 border-2 border-[#0D7377]/30 p-4">
          <div className="flex items-center gap-2">
            <Clock className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#E2E2F0]">
              志愿排序开放中！请将感兴趣的球员按优先级排序。截止后系统自动分配。
            </span>
          </div>
        </div>
      )}

      {phase === 'voting' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 选秀池 */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">选秀池</h3>
              <span className="text-xs text-[#4B4B6A]">点击加入志愿 / 标记不选</span>
            </div>
            <div className="space-y-2 max-h-[500px] overflow-y-auto">
              {mockDraftPool.map((p) => (
                <div key={p.id} className="flex items-center gap-3 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                  <button 
                    onClick={() => toggleExclude(p.id)}
                    className={clsx(
                      'w-6 h-6 border-2 flex items-center justify-center transition-colors',
                      excluded.includes(p.id) ? 'bg-red-500/20 border-red-500/50 text-red-400' : 'border-[#2D2D44] hover:border-[#0D7377]/50'
                    )}
                  >
                    {excluded.includes(p.id) && '✕'}
                  </button>
                  <div className="w-8 h-8 bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center">
                    <span className="text-[10px] font-bold text-[#8B8BA7]">{p.position}</span>
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-white">{p.name}</p>
                    <p className="text-xs text-[#4B4B6A]">{p.age}岁 · OVR {p.ovr} · {p.source}</p>
                  </div>
                  <span className={clsx(
                    'text-[10px] px-1.5 py-0.5 border',
                    p.growthSpeed === '快' ? 'text-emerald-400 border-emerald-400/30' :
                    p.growthSpeed === '中' ? 'text-yellow-400 border-yellow-400/30' :
                    'text-[#4B4B6A] border-[#2D2D44]'
                  )}>
                    {p.growthSpeed}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 我的志愿 */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">我的志愿排序</h3>
              <span className="text-xs text-[#4B4B6A]">拖拽调整优先级</span>
            </div>
            <div className="space-y-2">
              {draftOrder.map((id, idx) => {
                const p = getPlayerById(id)
                if (!p || excluded.includes(id)) return null
                return (
                  <div key={id} className="flex items-center gap-3 p-3 bg-[#0A0A0F] border-2 border-[#0D7377]/30">
                    <span className="w-6 h-6 bg-[#0D7377] flex items-center justify-center text-xs font-bold text-white">
                      {idx + 1}
                    </span>
                    <div className="w-8 h-8 bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center">
                      <span className="text-[10px] font-bold text-[#8B8BA7]">{p.position}</span>
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-white">{p.name}</p>
                      <p className="text-xs text-[#4B4B6A]">OVR {p.ovr} · {p.growthSpeed}速</p>
                    </div>
                  </div>
                )
              })}
            </div>
            <button className="btn-primary w-full mt-4 flex items-center justify-center gap-2">
              <Check className="w-4 h-4" />
              提交志愿排序
            </button>
          </div>
        </div>
      )}

      {phase === 'result' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">分配结果</h3>
          <div className="text-center py-12 text-[#4B4B6A]">
            <WarningDiamond className="w-8 h-8 mx-auto mb-3" />
            <p>选秀大会尚未开始</p>
            <p className="text-xs mt-1">第24天自动分配，请届时查看结果</p>
          </div>
        </div>
      )}
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
