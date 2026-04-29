import { Link } from 'react-router-dom'

const mockYoungPlayers = [
  { id: '1', name: '张小明', position: 'ST', age: 18, ovr: 52, potential: 'A', source: '青训', season: 1, games: 8, goals: 3 },
  { id: '2', name: '李小红', position: 'CMF', age: 19, ovr: 48, potential: 'B', source: '选秀', season: 1, games: 6, goals: 1 },
  { id: '3', name: '王小强', position: 'CB', age: 18, ovr: 45, potential: 'B', source: '青训', season: 1, games: 4, goals: 0 },
]

export default function YoungPlayers() {
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">年轻球员管理</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">青训出品球员的成长轨迹</p>
        </div>
        <div className="flex items-center gap-3">
          <Link to="/youth/academy" className="btn-secondary text-sm">青训营</Link>
          <Link to="/youth/draft" className="btn-secondary text-sm">选秀大会</Link>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">青训出品球员</h3>
          <span className="text-xs text-[#4B4B6A]">共 {mockYoungPlayers.length} 人</span>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b-2 border-[#2D2D44]">
                <th className="text-left text-xs text-[#4B4B6A] pb-2 font-medium">球员</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">位置</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">年龄</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">OVR</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">潜力</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">来源</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">赛季</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">出场</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">进球</th>
                <th className="text-right text-xs text-[#4B4B6A] pb-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {mockYoungPlayers.map((p) => (
                <tr key={p.id} className="border-b border-[#2D2D44]/50 hover:bg-[#1E1E2D]/50 transition-colors">
                  <td className="py-3">
                    <p className="text-sm font-medium text-white">{p.name}</p>
                  </td>
                  <td className="text-center">
                    <span className="text-xs px-2 py-0.5 bg-[#2D2D44] text-white">{p.position}</span>
                  </td>
                  <td className="text-center text-sm text-[#E2E2F0]">{p.age}</td>
                  <td className="text-center text-sm font-bold stat-number">{p.ovr}</td>
                  <td className="text-center">
                    <span className={clsx(
                      'text-xs font-bold',
                      p.potential === 'S' ? 'text-yellow-400' :
                      p.potential === 'A' ? 'text-[#0D7377]' :
                      'text-[#8B8BA7]'
                    )}>
                      {p.potential}
                    </span>
                  </td>
                  <td className="text-center">
                    <span className={clsx(
                      'text-xs',
                      p.source === '青训' ? 'text-emerald-400' : 'text-purple-400'
                    )}>
                      {p.source}
                    </span>
                  </td>
                  <td className="text-center text-sm text-[#8B8BA7]">S{p.season}</td>
                  <td className="text-center text-sm text-[#8B8BA7]">{p.games}</td>
                  <td className="text-center text-sm font-bold">{p.goals}</td>
                  <td className="text-right">
                    <Link to={`/players/${p.id}`} className="text-xs text-[#0D7377] hover:text-white transition-colors">
                      详情 →
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
