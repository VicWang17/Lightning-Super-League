import { Link } from 'react-router-dom'
import { Star } from 'lucide-react'
import { 
  Target
} from '../../components/ui/pixel-icons'

const mockResult = {
  homeTeam: '雷霆龙骑',
  awayTeam: '南海蛟龙',
  homeScore: 2,
  awayScore: 1,
  homeEmoji: '🐉',
  awayEmoji: '🌊',
}

const mockPlayerStats = [
  { name: '赵雷', pos: 'ST', goals: 1, assists: 0, rating: 8.5, mvp: true },
  { name: '陈浩', pos: 'WF', goals: 1, assists: 1, rating: 8.2, mvp: false },
  { name: '刘洋', pos: 'CMF', goals: 0, assists: 0, rating: 7.4, mvp: false },
  { name: '王强', pos: 'GK', goals: 0, assists: 0, rating: 7.1, mvp: false },
  { name: '李明', pos: 'CB', goals: 0, assists: 0, rating: 6.8, mvp: false },
  { name: '张伟', pos: 'CB', goals: 0, assists: 0, rating: 6.5, mvp: false },
  { name: '孙凯', pos: 'WF', goals: 0, assists: 0, rating: 6.3, mvp: false },
]

const mockMatchStats = {
  possession: [52, 48],
  shots: [12, 9],
  shotsOn: [6, 4],
  corners: [5, 4],
  fouls: [8, 10],
  yellows: [1, 1],
  reds: [0, 0],
}

export default function PostMatch() {
  return (
    <div className="space-y-6 max-w-[1200px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">赛后统计</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">联赛第8轮 · 全场结束</p>
        </div>
        <Link to="/match/schedule" className="text-sm text-[#0D7377] hover:text-white transition-colors">
          返回赛程 →
        </Link>
      </div>

      {/* 比分结果 */}
      <div className="card bg-[#0D4A4D]/20 border-[#0D7377]/30">
        <div className="flex items-center justify-center gap-8 py-8">
          <div className="text-center">
            <div className="w-20 h-20 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center mx-auto mb-3 shadow-pixel-green">
              <span className="text-3xl">{mockResult.homeEmoji}</span>
            </div>
            <h2 className="text-xl font-bold">{mockResult.homeTeam}</h2>
          </div>

          <div className="text-center">
            <div className="pixel-scoreboard">
              <span className="score-home">{mockResult.homeScore}</span>
              <span className="score-divider">:</span>
              <span className="score-away">{mockResult.awayScore}</span>
            </div>
            <span className="inline-block mt-3 px-3 py-1 bg-emerald-500/20 text-emerald-400 text-xs border border-emerald-500/30">
              胜利
            </span>
          </div>

          <div className="text-center">
            <div className="w-20 h-20 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center mx-auto mb-3">
              <span className="text-3xl">{mockResult.awayEmoji}</span>
            </div>
            <h2 className="text-xl font-bold">{mockResult.awayTeam}</h2>
          </div>
        </div>
      </div>

      {/* MVP */}
      <div className="card border-yellow-500/30">
        <div className="flex items-center gap-4">
          <div className="w-16 h-16 bg-yellow-500/20 border-2 border-yellow-500/50 flex items-center justify-center">
            <Star className="w-8 h-8 text-yellow-400" />
          </div>
          <div>
            <p className="text-xs text-yellow-400 font-bold uppercase tracking-wider">本场最佳</p>
            <h3 className="text-2xl font-bold text-white">赵雷</h3>
            <p className="text-sm text-[#8B8BA7]">前锋 · 评分 8.5 · 1进球</p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 球员评分 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Star className="w-4 h-4 text-[#0D7377]" />
            球员评分
          </h3>
          <div className="space-y-2">
            {mockPlayerStats.map((p) => (
              <div key={p.name} className="flex items-center gap-3 p-2 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                <div className="w-8 h-8 bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center">
                  <span className="text-[10px] font-bold text-[#8B8BA7]">{p.pos}</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{p.name}</p>
                  <div className="flex items-center gap-2 text-[10px] text-[#4B4B6A]">
                    {p.goals > 0 && <span className="text-yellow-400">⚽{p.goals}</span>}
                    {p.assists > 0 && <span className="text-[#0D7377]">🅰️{p.assists}</span>}
                  </div>
                </div>
                <div className={clsx(
                  'w-10 h-8 flex items-center justify-center text-sm font-bold pixel-number',
                  p.rating >= 8 ? 'bg-yellow-500/20 text-yellow-400' :
                  p.rating >= 7 ? 'bg-emerald-500/20 text-emerald-400' :
                  p.rating >= 6 ? 'bg-[#2D2D44] text-[#8B8BA7]' :
                  'bg-red-500/20 text-red-400'
                )}>
                  {p.rating}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 全场数据 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Target className="w-4 h-4 text-[#0D7377]" />
            全场数据
          </h3>
          <div className="space-y-4">
            <StatRow label="控球率" home={mockMatchStats.possession[0]} away={mockMatchStats.possession[1]} unit="%" />
            <StatRow label="射门" home={mockMatchStats.shots[0]} away={mockMatchStats.shots[1]} />
            <StatRow label="射正" home={mockMatchStats.shotsOn[0]} away={mockMatchStats.shotsOn[1]} />
            <StatRow label="角球" home={mockMatchStats.corners[0]} away={mockMatchStats.corners[1]} />
            <StatRow label="犯规" home={mockMatchStats.fouls[0]} away={mockMatchStats.fouls[1]} />
            <StatRow label="黄牌" home={mockMatchStats.yellows[0]} away={mockMatchStats.yellows[1]} />
            <StatRow label="红牌" home={mockMatchStats.reds[0]} away={mockMatchStats.reds[1]} />
          </div>
        </div>
      </div>
    </div>
  )
}

function StatRow({ label, home, away, unit = '' }: { label: string; home: number; away: number; unit?: string }) {
  const total = home + away
  const homePct = total > 0 ? (home / total) * 100 : 50
  
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-sm font-bold text-white">{home}{unit}</span>
        <span className="text-xs text-[#8B8BA7]">{label}</span>
        <span className="text-sm font-bold text-white">{away}{unit}</span>
      </div>
      <div className="flex h-2">
        <div className="bg-[#0D7377]" style={{ width: `${homePct}%` }} />
        <div className="bg-[#4B4B6A]" style={{ width: `${100 - homePct}%` }} />
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
