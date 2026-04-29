import { Link } from 'react-router-dom'
import { History } from 'lucide-react'
import { 
  Sword, 
  Shield, 
  Target,
  Clock,
  ChevronRight
} from '../../components/ui/pixel-icons'

const mockMyTeam = {
  name: '雷霆龙骑',
  formation: '1-3-2',
  mentality: '攻守平衡',
  attack: 72,
  defense: 68,
  midfield: 75,
}

const mockOpponent = {
  name: '南海蛟龙',
  formation: '2-1-3',
  mentality: '控球型',
  attack: 70,
  defense: 65,
  midfield: 78,
}

const mockHistory = [
  { season: 'S1', myScore: 2, oppScore: 1, result: 'W' as const },
  { season: 'S1', myScore: 1, oppScore: 1, result: 'D' as const },
  { season: 'S1', myScore: 0, oppScore: 2, result: 'L' as const },
]

const mockLineup = [
  { name: '王强', pos: 'GK', ovr: 72 },
  { name: '李明', pos: 'CB', ovr: 68 },
  { name: '张伟', pos: 'CB', ovr: 70 },
  { name: '刘洋', pos: 'CMF', ovr: 74 },
  { name: '陈浩', pos: 'WF', ovr: 71 },
  { name: '赵雷', pos: 'ST', ovr: 76 },
  { name: '孙凯', pos: 'WF', ovr: 69 },
]

export default function PreMatch() {
  return (
    <div className="space-y-6 max-w-[1200px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">赛前准备</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">下一场比赛情报与战术调整</p>
        </div>
        <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white transition-colors">
          返回赛程 →
        </Link>
      </div>

      {/* 比赛预告 */}
      <div className="card bg-[#0D4A4D]/20 border-[#0D7377]/30">
        <div className="flex items-center justify-center gap-8 py-6">
          {/* 主队 */}
          <div className="text-center">
            <div className="w-20 h-20 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center mx-auto mb-3 shadow-pixel-green">
              <span className="text-3xl">🐉</span>
            </div>
            <h2 className="text-xl font-bold">{mockMyTeam.name}</h2>
            <p className="text-sm text-[#8B8BA7]">{mockMyTeam.formation} · {mockMyTeam.mentality}</p>
          </div>

          {/* VS */}
          <div className="text-center px-6">
            <p className="text-4xl font-bold pixel-number text-[#0D7377]">VS</p>
            <div className="flex items-center gap-2 mt-2 text-xs text-[#8B8BA7]">
              <Clock className="w-3 h-3" />
              <span>Day 15 · 20:00</span>
            </div>
            <span className="inline-block mt-2 px-3 py-1 bg-[#0D7377]/20 text-[#0D7377] text-xs border border-[#0D7377]/30">
              联赛第8轮
            </span>
          </div>

          {/* 客队 */}
          <div className="text-center">
            <div className="w-20 h-20 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-3">
              <span className="text-3xl">🌊</span>
            </div>
            <h2 className="text-xl font-bold">{mockOpponent.name}</h2>
            <p className="text-sm text-[#8B8BA7]">{mockOpponent.formation} · {mockOpponent.mentality}</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 实力对比 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Sword className="w-4 h-4 text-[#0D7377]" />
            实力对比
          </h3>
          
          {[
            { label: '进攻', my: mockMyTeam.attack, opp: mockOpponent.attack, color: 'bg-red-500' },
            { label: '中场', my: mockMyTeam.midfield, opp: mockOpponent.midfield, color: 'bg-[#0D7377]' },
            { label: '防守', my: mockMyTeam.defense, opp: mockOpponent.defense, color: 'bg-blue-500' },
          ].map((stat) => (
            <div key={stat.label} className="mb-4 last:mb-0">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-white">{stat.my}</span>
                <span className="text-xs text-[#8B8BA7]">{stat.label}</span>
                <span className="text-sm font-bold text-white">{stat.opp}</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="flex-1">
                  <div className="pixel-progress-track h-3">
                    <div className="pixel-progress-fill bg-[#0D7377]" style={{ width: `${stat.my}%`, marginLeft: 'auto', marginRight: 0 }} />
                  </div>
                </div>
                <div className="flex-1">
                  <div className="pixel-progress-track h-3">
                    <div className="pixel-progress-fill bg-[#4B4B6A]" style={{ width: `${stat.opp}%` }} />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 历史交锋 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <History className="w-4 h-4 text-[#0D7377]" />
            历史交锋
          </h3>
          <div className="space-y-3">
            {mockHistory.map((h, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b-2 border-[#2D2D44] last:border-0">
                <span className="text-xs text-[#4B4B6A]">{h.season}</span>
                <div className="flex items-center gap-4">
                  <span className="text-sm font-medium">雷霆龙骑</span>
                  <span className={clsx(
                    'text-lg font-bold pixel-number',
                    h.result === 'W' ? 'text-emerald-400' : h.result === 'L' ? 'text-red-400' : 'text-[#8B8BA7]'
                  )}>
                    {h.myScore} : {h.oppScore}
                  </span>
                  <span className="text-sm font-medium">南海蛟龙</span>
                </div>
                <span className={clsx(
                  'text-xs px-2 py-0.5 border',
                  h.result === 'W' ? 'text-emerald-400 border-emerald-400/30' :
                  h.result === 'L' ? 'text-red-400 border-red-400/30' :
                  'text-[#8B8BA7] border-[#2D2D44]'
                )}>
                  {h.result === 'W' ? '胜' : h.result === 'L' ? '负' : '平'}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 预计首发 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">预计首发阵容</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          {mockLineup.map((p) => (
            <div key={p.name} className="bg-[#0A0A0F] border-2 border-[#2D2D44] p-3 text-center hover:border-[#0D7377]/50 transition-colors">
              <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
                <span className="text-xs font-bold text-[#8B8BA7]">{p.pos}</span>
              </div>
              <p className="text-xs text-white font-medium">{p.name}</p>
              <p className="text-[10px] text-[#4B4B6A]">OVR {p.ovr}</p>
            </div>
          ))}
        </div>
      </div>

      {/* 战术调整 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">战术调整</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link to="/team/tactics" className="flex items-center gap-3 p-4 bg-[#0A0A0F] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all hover:-translate-x-0.5 hover:-translate-y-0.5">
            <Target className="w-5 h-5 text-[#0D7377]" />
            <div>
              <p className="text-sm font-medium">调整阵型</p>
              <p className="text-xs text-[#4B4B6A]">当前: {mockMyTeam.formation}</p>
            </div>
            <ChevronRight className="w-4 h-4 text-[#4B4B6A] ml-auto" />
          </Link>
          <Link to="/team/players" className="flex items-center gap-3 p-4 bg-[#0A0A0F] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all hover:-translate-x-0.5 hover:-translate-y-0.5">
            <Shield className="w-5 h-5 text-[#0D7377]" />
            <div>
              <p className="text-sm font-medium">更换首发</p>
              <p className="text-xs text-[#4B4B6A]">调整出场球员</p>
            </div>
            <ChevronRight className="w-4 h-4 text-[#4B4B6A] ml-auto" />
          </Link>
          <Link to="/team/training" className="flex items-center gap-3 p-4 bg-[#0A0A0F] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-all hover:-translate-x-0.5 hover:-translate-y-0.5">
            <Sword className="w-5 h-5 text-[#0D7377]" />
            <div>
              <p className="text-sm font-medium">赛前训练</p>
              <p className="text-xs text-[#4B4B6A]">针对性备战</p>
            </div>
            <ChevronRight className="w-4 h-4 text-[#4B4B6A] ml-auto" />
          </Link>
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
