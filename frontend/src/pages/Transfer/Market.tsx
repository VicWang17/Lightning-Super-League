import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Search, 
  Clock,
  Eye,
  Plus
} from '../../components/ui/pixel-icons'

// Mock 拍卖球员
const mockAuctions = [
  { id: '1', name: '王磊', position: 'ST', age: 22, ovr: 74, potential: 'A', valuation: 850, currentBid: 920, bids: 12, timeLeft: '2小时15分', seller: '北方狼队', traits: ['禁区之狐', '空霸'] },
  { id: '2', name: '李华', position: 'CMF', age: 19, ovr: 68, potential: 'S', valuation: 600, currentBid: 1100, bids: 28, timeLeft: '45分钟', seller: '东方明珠', traits: ['组织核心'] },
  { id: '3', name: '张明', position: 'CB', age: 25, ovr: 71, potential: 'B', valuation: 500, currentBid: 480, bids: 5, timeLeft: '6小时30分', seller: '西部雄鹰', traits: ['铲断专家'] },
  { id: '4', name: '陈伟', position: 'WF', age: 20, ovr: 66, potential: 'A', valuation: 400, currentBid: 520, bids: 8, timeLeft: '1天3小时', seller: '南方猛虎', traits: ['盘带大师'] },
  { id: '5', name: '刘杰', position: 'GK', age: 28, ovr: 73, potential: 'B', valuation: 550, currentBid: 550, bids: 0, timeLeft: '3天', seller: '自由身', traits: ['门线技术'] },
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

const filters = [
  { label: '全部位置', options: ['全部', '前锋', '中场', '后卫', '门将'] },
  { label: '年龄', options: ['全部', '≤20岁', '21-25岁', '26-30岁', '≥31岁'] },
  { label: '能力', options: ['全部', '60+', '65+', '70+', '75+'] },
  { label: '潜力', options: ['全部', 'S', 'A', 'B', 'C'] },
]

export default function TransferMarket() {
  const [activeTab] = useState('auction')

  return (
    <div className="space-y-6 max-w-[1400px]">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">拍卖市场与球员交易</p>
        </div>
        <Link to="/transfer/my-listings" className="btn-secondary flex items-center gap-2 text-sm">
          <Plus className="w-4 h-4" />
          挂牌球员
        </Link>
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
              activeTab === tab.id
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* 筛选栏 */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#4B4B6A]" />
          <input 
            type="text" 
            placeholder="搜索球员..."
            className="w-full bg-[#12121A] border-2 border-[#2D2D44] pl-10 pr-4 py-2 text-sm text-[#E2E2F0] placeholder:text-[#4B4B6A] focus:outline-none focus:border-[#0D7377]/50"
          />
        </div>
        {filters.map((f) => (
          <select 
            key={f.label}
            className="bg-[#12121A] border-2 border-[#2D2D44] px-3 py-2 text-sm text-[#E2E2F0] focus:outline-none focus:border-[#0D7377]/50"
          >
            {f.options.map(o => <option key={o}>{o}</option>)}
          </select>
        ))}
      </div>

      {/* 拍卖列表 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">正在拍卖</h3>
          <span className="text-xs text-[#4B4B6A]">共 {mockAuctions.length} 名球员</span>
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
                <th className="text-right text-xs text-[#4B4B6A] pb-2 font-medium">系统估值</th>
                <th className="text-right text-xs text-[#4B4B6A] pb-2 font-medium">当前出价</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">出价数</th>
                <th className="text-center text-xs text-[#4B4B6A] pb-2 font-medium">剩余时间</th>
                <th className="text-right text-xs text-[#4B4B6A] pb-2 font-medium">操作</th>
              </tr>
            </thead>
            <tbody>
              {mockAuctions.map((p) => (
                <tr key={p.id} className="border-b border-[#2D2D44]/50 hover:bg-[#1E1E2D]/50 transition-colors">
                  <td className="py-3">
                    <div>
                      <p className="text-sm font-medium text-white">{p.name}</p>
                      <div className="flex gap-1 mt-0.5">
                        {p.traits.map(t => (
                          <span key={t} className="text-[10px] px-1 py-0.5 bg-[#0D7377]/20 text-[#0D7377] border border-[#0D7377]/20">{t}</span>
                        ))}
                      </div>
                    </div>
                  </td>
                  <td className="text-center">
                    <span className={clsx('text-xs px-2 py-0.5 font-bold', positionColors[p.position] || 'bg-[#2D2D44] text-white')}>
                      {p.position}
                    </span>
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
                  <td className="text-right text-sm text-[#8B8BA7]">{p.valuation}万</td>
                  <td className="text-right text-sm font-bold text-[#0D7377]">{p.currentBid}万</td>
                  <td className="text-center text-sm text-[#8B8BA7]">{p.bids}</td>
                  <td className="text-center">
                    <span className={clsx(
                      'text-xs flex items-center justify-center gap-1',
                      p.timeLeft.includes('分钟') ? 'text-red-400' : 'text-[#8B8BA7]'
                    )}>
                      <Clock className="w-3 h-3" />
                      {p.timeLeft}
                    </span>
                  </td>
                  <td className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button className="p-1.5 bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 text-[#8B8BA7] hover:text-white transition-colors">
                        <Eye className="w-3 h-3" />
                      </button>
                      <button className="px-3 py-1.5 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-xs font-bold border-2 border-[#0A5A5D] transition-colors">
                        出价
                      </button>
                    </div>
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
