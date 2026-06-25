import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  ChevronLeft,
  ChevronRight,
  Eye,
} from '../../components/ui/pixel-icons'
import { TransferTabs } from '../../components/transfer/TransferTabs'
import { PageHeader } from '../../components/ui/PageHeader'
import api from '../../api/client'
import type { PublicOfferItem } from '../../types/transfer'
import { OFFER_STATUS_NAMES, OFFER_KIND_NAMES } from '../../types/transfer'
import { POSITION_COLORS } from '../../types/player'

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
      <PageHeader title="公开报价" subtitle="查看收到的报价" />

      <TransferTabs />

      {loading && (
        <div className="flex items-center justify-center py-12 text-sm text-[#466353]">
          加载中...
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 p-4 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">公开报价</h3>
              <span className="text-xs text-[#8B5A2B]/40">共 {offers.length} 条</span>
            </div>
            <div className="space-y-3">
              {offers.map((o) => (
                <div key={o.offer_id} className="flex items-center gap-4 p-3 bg-white/70 border-2 border-[#1F5F43]/20">
                  <div className="w-10 h-10 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 flex items-center justify-center">
                    <span className={clsx('text-xs font-bold', POSITION_COLORS[o.position as keyof typeof POSITION_COLORS] || 'text-[#466353]')}>
                      {o.position}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#173126] truncate">
                      <Link to={`/players/${o.player_id}`} className="hover:text-[#1F5F43] transition-colors">
                        {o.player_name}
                      </Link>
                    </p>
                    <p className="text-xs text-[#8B5A2B]/40">
                      OVR {o.ovr} · {OFFER_KIND_NAMES[o.offer_kind]}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-[#1F5F43]">{(o.amount / 10000).toFixed(1)}万</p>
                    <p className="text-xs text-[#466353]">估值 {(o.market_value / 10000).toFixed(1)}万</p>
                  </div>
                  <div className="text-right min-w-[80px]">
                    <span className={clsx(
                      'text-xs px-2 py-0.5',
                      o.status === 'PENDING' ? 'bg-[#FFC247]/15 text-[#C77A00] border border-[#FFC247]/40' :
                      o.status === 'ACCEPTED' ? 'bg-[#B9EF3F]/20 text-[#1F5F43] border border-[#1F5F43]/30' :
                      o.status === 'REJECTED' ? 'bg-[#FF6F59]/10 text-[#FF6F59] border border-[#FF6F59]/30' :
                      'bg-[#F8FFD2] text-[#8B5A2B]/40'
                    )}>
                      {OFFER_STATUS_NAMES[o.status]}
                    </span>
                  </div>
                  <Link
                    to={`/players/${o.player_id}`}
                    className="p-1.5 bg-[#FFF8DC] border-2 border-[#1F5F43]/20 hover:border-[#1F5F43] text-[#466353] hover:text-[#173126] transition-colors"
                  >
                    <Eye className="w-3 h-3" />
                  </Link>
                </div>
              ))}
              {offers.length === 0 && (
                <div className="text-center py-12 text-[#466353]">
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
                className="p-2 bg-[#FFF8DC] border-2 border-[#1F5F43]/20 text-[#466353] hover:text-[#173126] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-[#466353]">第 {page} / {totalPages} 页</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 bg-[#FFF8DC] border-2 border-[#1F5F43]/20 text-[#466353] hover:text-[#173126] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
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
