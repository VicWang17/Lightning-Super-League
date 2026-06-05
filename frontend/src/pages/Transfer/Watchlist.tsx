import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Eye,
  Clock
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import type { TransferListingItem } from '../../types/transfer'
import { Card } from '../../components/ui/Card'

export default function Watchlist() {
  const [listings, setListings] = useState<TransferListingItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    async function fetch() {
      try {
        const res = await api.getTransferListings({ page_size: 50 })
        if (!cancelled && res.success) {
          setListings(res.data?.items || [])
        }
      } catch {
        // ignore
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    fetch()
    return () => { cancelled = true }
  }, [])

  const tabs = [
    { id: 'market', label: '拍卖市场', to: '/transfer/market' },
    { id: 'free', label: '自由市场', to: '/transfer/free-market' },
    { id: 'watchlist', label: '活跃挂牌', to: '/transfer/watchlist' },
    { id: 'my-listings', label: '我的挂牌', to: '/transfer/my-listings' },
    { id: 'public-offers', label: '公开报价', to: '/transfer/public-offers' },
    { id: 'my-offers', label: '我的报价', to: '/transfer/my-offers' },
    { id: 'history', label: '转会历史', to: '/transfer/history' },
  ]

  if (loading) {
    return <div className="max-w-[1400px] p-8 text-center text-[#8B8BA7]">加载中...</div>
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">活跃挂牌列表</p>
        </div>
      </div>

      {/* 子导航 */}
      <div className="flex gap-2 border-b-2 border-[#2D2D44] flex-wrap">
        {tabs.map(tab => (
          <Link
            key={tab.id}
            to={tab.to}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-0.5 ${
              tab.id === 'watchlist'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            }`}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      <Card>
        {listings.length === 0 ? (
          <div className="text-center py-12 text-[#4B4B6A]">
            <Eye className="w-8 h-8 mx-auto mb-3" />
            <p>暂无活跃挂牌</p>
            <p className="text-xs mt-1">转会市场中暂无球员挂牌</p>
          </div>
        ) : (
          <div className="space-y-3">
            {listings.map(p => (
              <div key={p.listing_id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 transition-colors">
                <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                  <span className="text-xs font-bold text-[#8B8BA7]">{p.position}</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-white">{p.name}</p>
                  <p className="text-xs text-[#4B4B6A]">{p.age}岁 · OVR {p.ovr}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-[#0D7377]">€{(p.list_price / 1000000).toFixed(1)}M</p>
                  <p className="text-xs text-[#8B8BA7] flex items-center gap-1 justify-end">
                    <Clock className="w-3 h-3" />
                    市值 €{(p.market_value / 1000000).toFixed(1)}M
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/transfer/market`}
                    className="px-3 py-1.5 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-xs font-bold border-2 border-[#0A5A5D] transition-colors"
                  >
                    查看
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
