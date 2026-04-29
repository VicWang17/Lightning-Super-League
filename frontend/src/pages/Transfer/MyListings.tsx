import { Link } from 'react-router-dom'
import { 
  Plus,
  Clock,
  WarningDiamond
} from '../../components/ui/pixel-icons'

const mockListings = [
  { id: '1', name: '吴东', position: 'SB', age: 26, ovr: 64, startPrice: 200, buyNow: 400, currentBid: 280, bids: 5, timeLeft: '1天', status: 'active' as const },
  { id: '2', name: '郑南', position: 'AMF', age: 30, ovr: 66, startPrice: 150, buyNow: 300, currentBid: 150, bids: 0, timeLeft: '3天', status: 'active' as const },
]

const mockHistory = [
  { id: '3', name: '钱北', position: 'GK', age: 28, ovr: 60, soldPrice: 180, buyer: '西部雄鹰', date: '2026-04-20' },
]

export default function MyListings() {
  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">我的挂牌与历史</p>
        </div>
        <button className="btn-primary flex items-center gap-2 text-sm">
          <Plus className="w-4 h-4" />
          挂牌新球员
        </button>
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
              tab.id === 'my-listings'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* 提示 */}
      <div className="flex items-center gap-3 p-3 bg-[#0D4A4D]/20 border-2 border-[#0D7377]/30">
        <WarningDiamond className="w-4 h-4 text-[#0D7377] flex-shrink-0" />
        <p className="text-sm text-[#8B8BA7]">
          挂牌费为起拍价的2%（最低1万）。成交后收取5%交易税。同一球员7天内只能上架1次。
        </p>
      </div>

      {/* 当前挂牌 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">当前拍卖中</h3>
        {mockListings.length === 0 ? (
          <p className="text-sm text-[#4B4B6A] text-center py-8">暂无挂牌中的球员</p>
        ) : (
          <div className="space-y-3">
            {mockListings.map((p) => (
              <div key={p.id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                  <span className="text-xs font-bold text-[#8B8BA7]">{p.position}</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{p.name}</p>
                  <p className="text-xs text-[#4B4B6A]">{p.age}岁 · OVR {p.ovr}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-[#4B4B6A]">起拍 {p.startPrice}万</p>
                  <p className="text-sm font-bold text-[#0D7377]">当前 {p.currentBid}万</p>
                </div>
                <div className="text-right">
                  <p className="text-xs text-[#4B4B6A]">{p.bids}次出价</p>
                  <p className="text-xs text-yellow-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {p.timeLeft}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 历史挂牌 */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">历史成交</h3>
        {mockHistory.length === 0 ? (
          <p className="text-sm text-[#4B4B6A] text-center py-8">暂无历史记录</p>
        ) : (
          <div className="space-y-3">
            {mockHistory.map((p) => (
              <div key={p.id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                  <span className="text-xs font-bold text-[#8B8BA7]">{p.position}</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{p.name}</p>
                  <p className="text-xs text-[#4B4B6A]">{p.age}岁 · OVR {p.ovr}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-emerald-400">{p.soldPrice}万</p>
                  <p className="text-xs text-[#4B4B6A]">买家: {p.buyer}</p>
                </div>
                <span className="text-xs text-[#4B4B6A]">{p.date}</span>
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
