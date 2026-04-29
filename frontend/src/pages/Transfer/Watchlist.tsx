import { Link } from 'react-router-dom'
import { 
  Eye,
  Clock,
  Cancel
} from '../../components/ui/pixel-icons'

const mockWatchlist = [
  { id: '1', name: '王磊', position: 'ST', age: 22, ovr: 74, currentBid: 920, timeLeft: '2小时15分', seller: '北方狼队' },
  { id: '2', name: '李华', position: 'CMF', age: 19, ovr: 68, currentBid: 1100, timeLeft: '45分钟', seller: '东方明珠' },
]

export default function Watchlist() {
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">关注列表（{mockWatchlist.length}/20）</p>
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
              tab.id === 'watchlist'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      <div className="card">
        {mockWatchlist.length === 0 ? (
          <div className="text-center py-12 text-[#4B4B6A]">
            <Eye className="w-8 h-8 mx-auto mb-3" />
            <p>暂无关注球员</p>
            <p className="text-xs mt-1">在拍卖市场点击关注图标添加</p>
          </div>
        ) : (
          <div className="space-y-3">
            {mockWatchlist.map((p) => (
              <div key={p.id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-colors">
                <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                  <span className="text-xs font-bold text-[#8B8BA7]">{p.position}</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{p.name}</p>
                  <p className="text-xs text-[#4B4B6A]">{p.age}岁 · OVR {p.ovr} · {p.seller}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-[#0D7377]">{p.currentBid}万</p>
                  <p className="text-xs text-red-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {p.timeLeft}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <button className="px-3 py-1.5 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-xs font-bold border-2 border-[#0A5A5D] transition-colors">
                    出价
                  </button>
                  <button className="p-1.5 bg-[#12121A] border-2 border-[#2D2D44] hover:border-red-500/50 text-[#4B4B6A] hover:text-red-400 transition-colors">
                    <Cancel className="w-3 h-3" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
