import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import {
  Loader,
  ChevronLeft,
  ChevronRight,
  Eye,
} from '../../components/ui/pixel-icons'
import api from '../../api/client'
import type { PublicOfferItem } from '../../types/transfer'
import { OFFER_STATUS_NAMES, OFFER_KIND_NAMES } from '../../types/transfer'
import { POSITION_COLORS } from '../../types/player'

const navTabs = [
  { id: 'market', label: '拍卖市场', to: '/transfer/market' },
  { id: 'free', label: '自由市场', to: '/transfer/free-market' },
  { id: 'watchlist', label: '我的关注', to: '/transfer/watchlist' },
  { id: 'my-listings', label: '我的挂牌', to: '/transfer/my-listings' },
  { id: 'public-offers', label: '公开报价', to: '/transfer/public-offers' },
  { id: 'my-offers', label: '我的报价', to: '/transfer/my-offers' },
  { id: 'history', label: '转会历史', to: '/transfer/history' },
]

export default function PublicOffers() {
  const [offers, setOffers] = useState<PublicOfferItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)

  const fetchOffers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.getPublicOffers({ page, page_size: 20 })
      if (res.success && res.data) {
        setOffers(res.data.items)
        setTotalPages(res.data.total_pages)
      } else {
        setOffers([])
        setTotalPages(1)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败')
    } finally {
      setLoading(false)
    }
  }, [page])

  useEffect(() => {
    fetchOffers()
  }, [fetchOffers])

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">全服公开报价动态</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b-2 border-[#2D2D44]">
        {navTabs.map((tab) => (
          <Link
            key={tab.id}
            to={tab.to}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-0.5',
              tab.id === 'public-offers'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {loading && (
        <div className="flex items-center justify-center py-12">
          <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
          <span className="ml-2 text-sm text-[#8B8BA7]">加载中...</span>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
          <AlertTriangle className="w-4 h-4" />
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">公开报价</h3>
              <span className="text-xs text-[#4B4B6A]">共 {offers.length} 条</span>
            </div>
            <div className="space-y-3">
              {offers.map((o) => (
                <div key={o.offer_id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                  <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                    <span className={clsx('text-xs font-bold', POSITION_COLORS[o.position as keyof typeof POSITION_COLORS] || 'text-[#8B8BA7]')}>
                      {o.position}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      <Link to={`/players/${o.player_id}`} className="hover:text-[#0D7377] transition-colors">
                        {o.player_name}
                      </Link>
                    </p>
                    <p className="text-xs text-[#4B4B6A]">
                      OVR {o.ovr} · {OFFER_KIND_NAMES[o.offer_kind]}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-[#0D7377]">{(o.amount / 10000).toFixed(1)}万</p>
                    <p className="text-xs text-[#8B8BA7]">估值 {(o.market_value / 10000).toFixed(1)}万</p>
                  </div>
                  <div className="text-right min-w-[80px]">
                    <span className={clsx(
                      'text-xs px-2 py-0.5',
                      o.status === 'PENDING' ? 'bg-yellow-500/10 text-yellow-400 border border-yellow-500/30' :
                      o.status === 'ACCEPTED' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' :
                      o.status === 'REJECTED' ? 'bg-red-500/10 text-red-400 border border-red-500/30' :
                      'bg-[#2D2D44] text-[#4B4B6A]'
                    )}>
                      {OFFER_STATUS_NAMES[o.status]}
                    </span>
                  </div>
                  <Link
                    to={`/players/${o.player_id}`}
                    className="p-1.5 bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 text-[#8B8BA7] hover:text-white transition-colors"
                  >
                    <Eye className="w-3 h-3" />
                  </Link>
                </div>
              ))}
              {offers.length === 0 && (
                <div className="text-center py-12 text-[#8B8BA7]">
                  <p className="text-sm">暂无公开报价</p>
                </div>
              )}
            </div>
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 bg-[#12121A] border-2 border-[#2D2D44] text-[#8B8BA7] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-[#8B8BA7]">第 {page} / {totalPages} 页</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 bg-[#12121A] border-2 border-[#2D2D44] text-[#8B8BA7] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
