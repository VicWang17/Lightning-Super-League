import { Link } from 'react-router-dom'
import { 
  Transfer,
  TrendingUp,
  TrendingDown
} from '../../components/ui/pixel-icons'

const mockTransfers = [
  { id: '1', player: '王磊', position: 'ST', type: 'in' as const, price: 920, from: '北方狼队', date: '2026-04-25', ovr: 74 },
  { id: '2', player: '钱北', position: 'GK', type: 'out' as const, price: 180, to: '西部雄鹰', date: '2026-04-20', ovr: 60 },
  { id: '3', player: '李华', position: 'CMF', type: 'in' as const, price: 1100, from: '东方明珠', date: '2026-04-15', ovr: 68 },
  { id: '4', player: '吴东', position: 'SB', type: 'out' as const, price: 320, to: '南方猛虎', date: '2026-04-10', ovr: 64 },
  { id: '5', player: '周伟', position: 'DMF', type: 'in' as const, price: 180, from: '自由市场', date: '2026-04-05', ovr: 62 },
]

export default function TransferHistory() {
  const totalIn = mockTransfers.filter(t => t.type === 'in').reduce((s, t) => s + t.price, 0)
  const totalOut = mockTransfers.filter(t => t.type === 'out').reduce((s, t) => s + t.price, 0)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">本赛季转会记录</p>
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
              tab.id === 'history'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span className="text-sm text-[#8B8BA7]">总支出</span>
          </div>
          <p className="text-2xl font-bold text-red-400 stat-number">{totalIn}万</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">总收入</span>
          </div>
          <p className="text-2xl font-bold text-emerald-400 stat-number">{totalOut}万</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Transfer className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">净投入</span>
          </div>
          <p className={clsx('text-2xl font-bold stat-number', totalIn - totalOut > 0 ? 'text-red-400' : 'text-emerald-400')}>
            {totalIn - totalOut > 0 ? '+' : ''}{totalIn - totalOut}万
          </p>
        </div>
      </div>

      <div className="card">
        <h3 className="text-lg font-semibold mb-4">转会记录</h3>
        <div className="space-y-3">
          {mockTransfers.map((t) => (
            <div key={t.id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
              <div className={clsx(
                'w-8 h-8 flex items-center justify-center border-2',
                t.type === 'in' ? 'bg-emerald-500/20 border-emerald-500/30 text-emerald-400' : 'bg-red-500/20 border-red-500/30 text-red-400'
              )}>
                {t.type === 'in' ? '入' : '出'}
              </div>
              <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                <span className="text-xs font-bold text-[#8B8BA7]">{t.position}</span>
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">{t.player}</p>
                <p className="text-xs text-[#4B4B6A]">
                  {t.type === 'in' ? `从 ${t.from}` : `至 ${t.to}`} · OVR {t.ovr}
                </p>
              </div>
              <div className="text-right">
                <p className={clsx('text-sm font-bold', t.type === 'in' ? 'text-red-400' : 'text-emerald-400')}>
                  {t.type === 'in' ? '-' : '+'}{t.price}万
                </p>
                <p className="text-xs text-[#4B4B6A]">{t.date}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
