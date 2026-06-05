import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, X } from 'lucide-react'
import {
  Loader,
  ChevronLeft,
  ChevronRight,
  Send,
  CornerUpRight,
  Eye,
} from '../../components/ui/pixel-icons'
import api from '../../api/client'
import type { TransferOfferItem } from '../../types/transfer'
import { OFFER_STATUS_NAMES, OFFER_KIND_NAMES } from '../../types/transfer'

const navTabs = [
  { id: 'market', label: '拍卖市场', to: '/transfer/market' },
  { id: 'free', label: '自由市场', to: '/transfer/free-market' },
  { id: 'watchlist', label: '我的关注', to: '/transfer/watchlist' },
  { id: 'my-listings', label: '我的挂牌', to: '/transfer/my-listings' },
  { id: 'public-offers', label: '公开报价', to: '/transfer/public-offers' },
  { id: 'my-offers', label: '我的报价', to: '/transfer/my-offers' },
  { id: 'history', label: '转会历史', to: '/transfer/history' },
]

export default function MyOffers() {
  const [offers, setOffers] = useState<TransferOfferItem[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [teamId, setTeamId] = useState<string | null>(null)

  // Final offer modal
   const [finalNegotiation, setFinalNegotiation] = useState<{ negotiationId: string; playerName: string } | null>(null)
  const [finalAmount, setFinalAmount] = useState('')
  const [finalLoading, setFinalLoading] = useState(false)
  const [finalError, setFinalError] = useState<string | null>(null)
  const [finalSuccess, setFinalSuccess] = useState(false)

  useEffect(() => {
    api.get<{ id: string }>('/teams/my-team').then(res => {
      if (res.success && res.data) setTeamId(res.data.id)
    })
  }, [])

  const fetchOffers = useCallback(async () => {
    if (!teamId) return
    setLoading(true)
    setError(null)
    try {
      const res = await api.getSentOffers({ team_id: teamId, page, page_size: 20 })
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
  }, [teamId, page])

  useEffect(() => {
    if (teamId) fetchOffers()
  }, [fetchOffers, teamId])

  const openFinalModal = (offer: TransferOfferItem) => {
    setFinalNegotiation({ negotiationId: offer.negotiation_id, playerName: offer.player_name })
    setFinalAmount('')
    setFinalError(null)
    setFinalSuccess(false)
  }

  const closeFinalModal = () => {
    setFinalNegotiation(null)
    setFinalAmount('')
    setFinalError(null)
    setFinalSuccess(false)
  }

  const submitFinalOffer = async () => {
    if (!finalNegotiation || !finalAmount || !teamId) return
    setFinalLoading(true)
    setFinalError(null)
    try {
      const res = await api.createFinalOffer(finalNegotiation.negotiationId, {
        buyer_team_id: teamId,
        amount: Number(finalAmount) * 10000,
      })
      if (res.success && res.data) {
        setFinalSuccess(true)
        fetchOffers()
      } else {
        setFinalError(res.message || '最终报价失败')
      }
    } catch (err) {
      setFinalError(err instanceof Error ? err.message : '请求失败')
    } finally {
      setFinalLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">我发出的报价</p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2 border-b-2 border-[#2D2D44]">
        {navTabs.map((tab) => (
          <Link
            key={tab.id}
            to={tab.to}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-0.5',
              tab.id === 'my-offers'
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
              <h3 className="text-lg font-semibold">已发报价</h3>
              <span className="text-xs text-[#4B4B6A]">共 {offers.length} 条</span>
            </div>
            <div className="space-y-3">
              {offers.map((o) => (
                <div key={o.offer_id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                  <div className={clsx(
                    'w-8 h-8 flex items-center justify-center border-2',
                    o.offer_kind === 'INITIAL' ? 'bg-blue-500/20 border-blue-500/30 text-blue-400' :
                    o.offer_kind === 'COUNTER' ? 'bg-yellow-500/20 border-yellow-500/30 text-yellow-400' :
                    'bg-purple-500/20 border-purple-500/30 text-purple-400'
                  )}>
                    {o.offer_kind === 'INITIAL' ? <Send className="w-4 h-4" /> :
                     o.offer_kind === 'COUNTER' ? <CornerUpRight className="w-4 h-4" /> :
                     <Send className="w-4 h-4" />}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white truncate">
                      <Link to={`/players/${o.player_id}`} className="hover:text-[#0D7377] transition-colors">
                        {o.player_name}
                      </Link>
                    </p>
                    <p className="text-xs text-[#4B4B6A]">
                      {OFFER_KIND_NAMES[o.offer_kind]} · {(o.amount / 10000).toFixed(1)}万
                    </p>
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
                  <div className="flex items-center gap-2">
                    {o.status === 'PENDING' && o.offer_kind === 'COUNTER' && (
                      <button
                        onClick={() => openFinalModal(o)}
                        className="px-3 py-1.5 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-xs font-bold border-2 border-[#0A5A5D] transition-colors"
                      >
                        最终报价
                      </button>
                    )}
                    <Link
                      to={`/players/${o.player_id}`}
                      className="p-1.5 bg-[#12121A] border-2 border-[#2D2D44] hover:border-[#0D7377]/50 text-[#8B8BA7] hover:text-white transition-colors"
                    >
                      <Eye className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              ))}
              {offers.length === 0 && (
                <div className="text-center py-12 text-[#8B8BA7]">
                  <p className="text-sm">暂无发出的报价</p>
                  <p className="text-xs mt-1">在拍卖市场找到心仪球员后点击「报价」</p>
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

      {/* Final Offer Modal */}
      {finalNegotiation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-lg">
            <div className="flex items-center justify-between p-4 border-b-2 border-[#2D2D44]">
              <h3 className="text-lg font-bold text-white">
                {finalSuccess ? '最终报价已发送' : `最终报价: ${finalNegotiation.playerName}`}
              </h3>
              <button onClick={closeFinalModal} className="text-[#8B8BA7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              {finalSuccess ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <Send className="w-5 h-5" />
                    <span className="font-bold">最终报价发送成功！</span>
                  </div>
                  <p className="text-sm text-[#8B8BA7]">
                    报价金额: <span className="text-white font-bold">{finalAmount}万</span>
                  </p>
                  <button
                    onClick={closeFinalModal}
                    className="w-full py-2 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                  >
                    确定
                  </button>
                </div>
              ) : (
                <>
                  <div className="pt-2">
                    <label className="text-xs text-[#8B8BA7] mb-1 block">最终报价金额（万）</label>
                    <input
                      type="number"
                      value={finalAmount}
                      onChange={e => setFinalAmount(e.target.value)}
                      className="w-full bg-[#1A1A2E] border-2 border-[#2D2D44] px-3 py-2 text-sm text-white focus:border-[#0D7377] outline-none"
                      placeholder="输入最终报价金额（需高于初始报价）"
                    />
                  </div>
                  {finalError && (
                    <div className="flex items-center gap-2 p-3 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
                      <AlertTriangle className="w-4 h-4" />
                      {finalError}
                    </div>
                  )}
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeFinalModal}
                      className="flex-1 py-2 bg-[#2D2D44] hover:bg-[#3D3D5C] text-white text-sm font-bold border-2 border-[#2D2D44] transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={submitFinalOffer}
                      disabled={finalLoading || !finalAmount || Number(finalAmount) <= 0}
                      className="flex-1 py-2 bg-[#0D7377] hover:bg-[#0A5A5D] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                    >
                      {finalLoading ? '发送中...' : '提交最终报价'}
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
