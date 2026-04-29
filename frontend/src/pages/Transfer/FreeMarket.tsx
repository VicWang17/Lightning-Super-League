import { Link } from 'react-router-dom'
import { 
  Clock,
  WarningDiamond
} from '../../components/ui/pixel-icons'

const mockFreePlayers = [
  { id: '1', name: '周伟', position: 'DMF', age: 24, ovr: 62, price: 180, originalValuation: 300, source: '拍卖流拍', daysLeft: 2 },
  { id: '2', name: '吴刚', position: 'SB', age: 20, ovr: 58, price: 120, originalValuation: 200, source: '选秀落选', daysLeft: 5 },
  { id: '3', name: '郑强', position: 'AMF', age: 27, ovr: 65, price: 250, originalValuation: 400, source: '解约球员', daysLeft: 1 },
  { id: '4', name: '马东', position: 'ST', age: 22, ovr: 60, price: 150, originalValuation: 250, source: '系统回收', daysLeft: 3 },
  { id: '5', name: '黄磊', position: 'GK', age: 19, ovr: 55, price: 90, originalValuation: 150, source: '选秀落选', daysLeft: 4 },
]

const positionColors: Record<string, string> = {
  ST: 'bg-red-500 text-white',
  WF: 'bg-red-400 text-white',
  AMF: 'bg-emerald-400 text-white',
  CMF: 'bg-emerald-500 text-white',
  DMF: 'bg-emerald-600 text-white',
  CB: 'bg-blue-500 text-white',
  SB: 'bg-blue-400 text-white',
  GK: 'bg-amber-500 text-black',
}

const sourceColors: Record<string, string> = {
  '拍卖流拍': 'text-blue-400',
  '选秀落选': 'text-purple-400',
  '解约球员': 'text-red-400',
  '系统回收': 'text-[#8B8BA7]',
}

export default function FreeMarket() {
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">一口价签约，无需竞价</p>
        </div>
      </div>

      {/* 子导航 */}
      <div className="flex gap-2 border-b-2 border-[#2D2D44]">
        {[
          { id: 'auction', label: '拍卖市场', to: '/transfer/market' },
          { id: 'free', label: '自由市场', to: '/transfer/free-market' },
          { id: 'watchlist', label: '我的关注', to: '/transfer/watchlist' },
          { id: 'my-listings', label: '我的挂牌', to: '/transfer/my-listings' },
          { id: 'history', label: '转会历史', to: '/transfer/history' },
        ].map((tab) => (
          <Link
            key={tab.id}
            to={tab.to}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-0.5',
              tab.id === 'free'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* 提示 */}
      <div className="flex items-center gap-3 p-3 bg-yellow-500/10 border-2 border-yellow-500/30">
        <WarningDiamond className="w-4 h-4 text-yellow-400 flex-shrink-0" />
        <p className="text-sm text-yellow-400">
          每48小时内最多从自由市场签约2名球员。价格每24小时自动下调5%。
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {mockFreePlayers.map((p) => (
          <div key={p.id} className="card card-hover">
            <div className="flex items-start justify-between mb-3">
              <div>
                <h4 className="font-bold text-white">{p.name}</h4>
                <p className="text-xs text-[#8B8BA7]">{p.age}岁 · OVR {p.ovr}</p>
              </div>
              <span className={clsx('text-xs px-2 py-0.5 font-bold', positionColors[p.position] || 'bg-[#2D2D44] text-white')}>
                {p.position}
              </span>
            </div>
            
            <div className="flex items-center gap-2 mb-3">
              <span className={clsx('text-xs', sourceColors[p.source] || 'text-[#8B8BA7]')}>{p.source}</span>
            </div>

            <div className="space-y-2 mb-4">
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#4B4B6A]">原价</span>
                <span className="text-xs text-[#8B8BA7] line-through">{p.originalValuation}万</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#4B4B6A]">现价</span>
                <span className="text-lg font-bold text-[#0D7377] stat-number">{p.price}万</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-[#4B4B6A]">折扣</span>
                <span className="text-xs text-emerald-400">{Math.round((1 - p.price/p.originalValuation)*100)}% OFF</span>
              </div>
            </div>

            <div className="flex items-center justify-between pt-3 border-t-2 border-[#2D2D44]">
              <span className="text-xs text-[#4B4B6A] flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {p.daysLeft}天后降价
              </span>
              <button className="px-4 py-1.5 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-xs font-bold border-2 border-[#0A5A5D] transition-colors">
                签约
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
