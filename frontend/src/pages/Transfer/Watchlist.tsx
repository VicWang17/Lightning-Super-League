import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { TransferTabs } from '../../components/transfer/TransferTabs'
import { PageHeader } from '../../components/ui/PageHeader'
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

  if (loading) {
    return <div className="max-w-[1400px] p-8 text-center text-[#466353]">加载中...</div>
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <PageHeader title="我的关注" subtitle="关注的球员列表" />

      <TransferTabs />

      <Card >
        {listings.length === 0 ? (
          <div className="text-center py-12 text-[#8B5A2B]/40">
            <p>暂无活跃挂牌</p>
            <p className="text-xs mt-1">转会市场中暂无球员挂牌</p>
          </div>
        ) : (
          <div className="space-y-3">
            {listings.map(p => (
              <div key={p.listing_id} className="flex items-center gap-4 p-3 bg-white/70 border-2 border-[#1F5F43]/20 hover:border-[#1F5F43] transition-colors">
                <div className="w-10 h-10 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 flex items-center justify-center">
                  <span className="text-xs font-bold text-[#466353]">{p.position}</span>
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium text-[#173126]">{p.name}</p>
                  <p className="text-xs text-[#8B5A2B]/40">{p.age}岁 · OVR {p.ovr}</p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-bold text-[#1F5F43]">€{(p.list_price / 1000000).toFixed(1)}M</p>
                  <p className="text-xs text-[#466353] text-right">
                    市值 €{(p.market_value / 1000000).toFixed(1)}M
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Link
                    to={`/transfer/market`}
                    className="px-3 py-1.5 bg-[#1F5F43] hover:bg-[#173126] text-[#F8FFD2] text-xs font-bold border-2 border-[#173126] transition-colors"
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
