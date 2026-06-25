import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { X } from 'lucide-react'
import {
  ChevronLeft,
  ChevronRight,
  Eye,
} from '../../components/ui/pixel-icons'
import { TransferTabs } from '../../components/transfer/TransferTabs'
import { PageHeader } from '../../components/ui/PageHeader'
import api from '../../api/client'
import type { TransferOfferItem } from '../../types/transfer'
import { OFFER_STATUS_NAMES, OFFER_KIND_NAMES } from '../../types/transfer'

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
      <PageHeader title="我的报价" subtitle="查看发出的报价" />

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
              <h3 className="text-lg font-semibold">已发报价</h3>
              <span className="text-xs text-[#8B5A2B]/40">共 {offers.length} 条</span>
            </div>
            <div className="space-y-3">
              {offers.map((o) => (
                <div key={o.offer_id} className="flex items-center gap-4 p-3 bg-white/70 border-2 border-[#1F5F43]/20">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-[#173126] truncate">
                      <Link to={`/players/${o.player_id}`} className="hover:text-[#1F5F43] transition-colors">
                        {o.player_name}
                      </Link>
                    </p>
                    <p className="text-xs text-[#8B5A2B]/40">
                      {OFFER_KIND_NAMES[o.offer_kind]} · {(o.amount / 10000).toFixed(1)}万
                    </p>
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
                  <div className="flex items-center gap-2">
                    {o.status === 'PENDING' && o.offer_kind === 'COUNTER' && (
                      <button
                        onClick={() => openFinalModal(o)}
                        className="px-3 py-1.5 bg-[#1F5F43] hover:bg-[#173126] text-[#F8FFD2] text-xs font-bold border-2 border-[#173126] transition-colors"
                      >
                        最终报价
                      </button>
                    )}
                    <Link
                      to={`/players/${o.player_id}`}
                      className="p-1.5 bg-[#FFF8DC] border-2 border-[#1F5F43]/20 hover:border-[#1F5F43] text-[#466353] hover:text-[#173126] transition-colors"
                    >
                      <Eye className="w-3 h-3" />
                    </Link>
                  </div>
                </div>
              ))}
              {offers.length === 0 && (
                <div className="text-center py-12 text-[#466353]">
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

      {/* Final Offer Modal */}
      {finalNegotiation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1F5F43]/35 p-4">
          <div className="w-full max-w-md bg-[#FFF8DC] border-2 border-[#1F5F43]/20 shadow-pixel-lg">
            <div className="flex items-center justify-between p-4 border-b-2 border-[#1F5F43]/20">
              <h3 className="text-lg font-bold text-[#173126]">
                {finalSuccess ? '最终报价已发送' : `最终报价: ${finalNegotiation.playerName}`}
              </h3>
              <button onClick={closeFinalModal} className="text-[#466353] hover:text-[#173126]">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              {finalSuccess ? (
                <div className="space-y-4">
                  <div className="text-[#1F5F43] font-bold">
                    最终报价发送成功！
                  </div>
                  <p className="text-sm text-[#466353]">
                    报价金额: <span className="text-[#173126] font-bold">{finalAmount}万</span>
                  </p>
                  <button
                    onClick={closeFinalModal}
                    className="w-full py-2 bg-[#1F5F43] hover:bg-[#173126] text-[#F8FFD2] text-sm font-bold border-2 border-[#173126] transition-colors"
                  >
                    确定
                  </button>
                </div>
              ) : (
                <>
                  <div className="pt-2">
                    <label className="text-xs text-[#466353] mb-1 block">最终报价金额（万）</label>
                    <input
                      type="number"
                      value={finalAmount}
                      onChange={e => setFinalAmount(e.target.value)}
                      className="w-full bg-white border-2 border-[#1F5F43]/20 px-3 py-2 text-sm text-[#173126] focus:border-[#1F5F43] outline-none"
                      placeholder="输入最终报价金额（需高于初始报价）"
                    />
                  </div>
                  {finalError && (
                    <div className="flex items-center gap-2 p-3 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">
                      {finalError}
                    </div>
                  )}
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeFinalModal}
                      className="flex-1 py-2 bg-[#FFF8DC] hover:bg-[#F8FFD2] text-[#173126] text-sm font-bold border-2 border-[#1F5F43]/20 transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={submitFinalOffer}
                      disabled={finalLoading || !finalAmount || Number(finalAmount) <= 0}
                      className="flex-1 py-2 bg-[#1F5F43] hover:bg-[#173126] disabled:opacity-40 disabled:cursor-not-allowed text-[#F8FFD2] text-sm font-bold border-2 border-[#173126] transition-colors"
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
