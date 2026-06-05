import { useState, useEffect, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { AlertTriangle, X, Check } from 'lucide-react'
import {
  Plus,
  Clock,
  WarningDiamond,
  Loader,
  ChevronLeft,
  ChevronRight,
  CornerUpRight,
  Eye,
} from '../../components/ui/pixel-icons'
import api from '../../api/client'
import type { TransferListingItem, TransferOfferItem } from '../../types/transfer'
import { OFFER_STATUS_NAMES, OFFER_KIND_NAMES } from '../../types/transfer'
import { POSITION_COLORS } from '../../types/player'
import type { Player } from '../../types/player'

const navTabs = [
  { id: 'market', label: '拍卖市场', to: '/transfer/market' },
  { id: 'free', label: '自由市场', to: '/transfer/free-market' },
  { id: 'watchlist', label: '我的关注', to: '/transfer/watchlist' },
  { id: 'my-listings', label: '我的挂牌', to: '/transfer/my-listings' },
  { id: 'public-offers', label: '公开报价', to: '/transfer/public-offers' },
  { id: 'my-offers', label: '我的报价', to: '/transfer/my-offers' },
  { id: 'history', label: '转会历史', to: '/transfer/history' },
]

export default function MyListings() {
  const [teamId, setTeamId] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'listings' | 'received'>('listings')

  // Listings
  const [listings, setListings] = useState<TransferListingItem[]>([])
  const [listingsLoading, setListingsLoading] = useState(false)
  const [listingsError, setListingsError] = useState<string | null>(null)

  // Received offers
  const [offers, setOffers] = useState<TransferOfferItem[]>([])
  const [offersLoading, setOffersLoading] = useState(false)
  const [offersError, setOffersError] = useState<string | null>(null)
  const [offersPage, setOffersPage] = useState(1)
  const [offersTotalPages, setOffersTotalPages] = useState(1)

  // List player modal
  const [showListModal, setShowListModal] = useState(false)
  const [roster, setRoster] = useState<Player[]>([])
  const [rosterLoading, setRosterLoading] = useState(false)
  const [selectedPlayer, setSelectedPlayer] = useState<Player | null>(null)
  const [listPrice, setListPrice] = useState('')
  const [valuation, setValuation] = useState<number | null>(null)
  const [valuationLoading, setValuationLoading] = useState(false)
  const [listLoading, setListLoading] = useState(false)
  const [listError, setListError] = useState<string | null>(null)
  const [listSuccess, setListSuccess] = useState(false)

  // Counter modal
  const [counterOffer, setCounterOffer] = useState<TransferOfferItem | null>(null)
  const [counterAmount, setCounterAmount] = useState('')
  const [counterLoading, setCounterLoading] = useState(false)
  const [counterError, setCounterError] = useState<string | null>(null)
  const [counterSuccess, setCounterSuccess] = useState(false)

  // Action loading states
  const [actionLoading, setActionLoading] = useState<Record<string, boolean>>({})

  useEffect(() => {
    api.get<{ id: string }>('/teams/my-team').then(res => {
      if (res.success && res.data) setTeamId(res.data.id)
    })
  }, [])

  const fetchListings = useCallback(async () => {
    if (!teamId) return
    setListingsLoading(true)
    setListingsError(null)
    try {
      const res = await api.getTransferListings({ seller_team_id: teamId })
      if (res.success && res.data) {
        setListings(res.data.items)
      } else {
        setListings([])
      }
    } catch (err) {
      setListingsError(err instanceof Error ? err.message : '获取数据失败')
    } finally {
      setListingsLoading(false)
    }
  }, [teamId])

  const fetchOffers = useCallback(async () => {
    if (!teamId) return
    setOffersLoading(true)
    setOffersError(null)
    try {
      const res = await api.getReceivedOffers({ team_id: teamId, page: offersPage, page_size: 20 })
      if (res.success && res.data) {
        setOffers(res.data.items)
        setOffersTotalPages(res.data.total_pages)
      } else {
        setOffers([])
        setOffersTotalPages(1)
      }
    } catch (err) {
      setOffersError(err instanceof Error ? err.message : '获取数据失败')
    } finally {
      setOffersLoading(false)
    }
  }, [teamId, offersPage])

  useEffect(() => {
    if (teamId) {
      fetchListings()
      fetchOffers()
    }
  }, [teamId, fetchListings, fetchOffers])

  // Cancel listing
  const handleCancel = async (listingId: string) => {
    if (!teamId) return
    setActionLoading(prev => ({ ...prev, [`cancel-${listingId}`]: true }))
    try {
      await api.cancelListing(listingId, teamId)
      fetchListings()
    } catch (err) {
      alert(err instanceof Error ? err.message : '撤销失败')
    } finally {
      setActionLoading(prev => ({ ...prev, [`cancel-${listingId}`]: false }))
    }
  }

  // Accept offer
  const handleAccept = async (offerId: string) => {
    if (!teamId) return
    setActionLoading(prev => ({ ...prev, [`accept-${offerId}`]: true }))
    try {
      await api.acceptTransferOffer(offerId, teamId)
      fetchOffers()
      fetchListings()
    } catch (err) {
      alert(err instanceof Error ? err.message : '接受失败')
    } finally {
      setActionLoading(prev => ({ ...prev, [`accept-${offerId}`]: false }))
    }
  }

  // Reject offer
  const handleReject = async (offerId: string) => {
    if (!teamId) return
    setActionLoading(prev => ({ ...prev, [`reject-${offerId}`]: true }))
    try {
      await api.rejectTransferOffer(offerId, teamId)
      fetchOffers()
    } catch (err) {
      alert(err instanceof Error ? err.message : '拒绝失败')
    } finally {
      setActionLoading(prev => ({ ...prev, [`reject-${offerId}`]: false }))
    }
  }

  // Open list modal
  const openListModal = async () => {
    setShowListModal(true)
    setSelectedPlayer(null)
    setListPrice('')
    setValuation(null)
    setListError(null)
    setListSuccess(false)
    setRosterLoading(true)
    try {
      const res = await api.get<{ players: Player[] }>(`/teams/${teamId}/players`)
      if (res.success && res.data) {
        setRoster(res.data.players)
      }
    } catch (err) {
      setListError(err instanceof Error ? err.message : '获取 roster 失败')
    } finally {
      setRosterLoading(false)
    }
  }

  // Select player and get valuation
  const selectPlayerForListing = async (player: Player) => {
    setSelectedPlayer(player)
    setListPrice('')
    setValuationLoading(true)
    try {
      const res = await api.getPlayerValuation(player.id, teamId || undefined)
      if (res.success && res.data) {
        setValuation(res.data.market_value)
        setListPrice(String(Math.round(res.data.market_value / 10000)))
      }
    } catch {
      setValuation(null)
    } finally {
      setValuationLoading(false)
    }
  }

  // Submit listing
  const submitListing = async () => {
    if (!selectedPlayer || !teamId || !listPrice) return
    setListLoading(true)
    setListError(null)
    try {
      const res = await api.listPlayer(selectedPlayer.id, {
        team_id: teamId,
        list_price: Number(listPrice) * 10000,
      })
      if (res.success && res.data) {
        setListSuccess(true)
        fetchListings()
      } else {
        setListError(res.message || '挂牌失败')
      }
    } catch (err) {
      setListError(err instanceof Error ? err.message : '挂牌请求失败')
    } finally {
      setListLoading(false)
    }
  }

  // Counter offer
  const openCounterModal = (offer: TransferOfferItem) => {
    setCounterOffer(offer)
    setCounterAmount('')
    setCounterError(null)
    setCounterSuccess(false)
  }

  const closeCounterModal = () => {
    setCounterOffer(null)
    setCounterAmount('')
    setCounterError(null)
    setCounterSuccess(false)
  }

  const submitCounter = async () => {
    if (!counterOffer || !teamId || !counterAmount) return
    setCounterLoading(true)
    setCounterError(null)
    try {
      const res = await api.counterTransferOffer(counterOffer.offer_id, {
        seller_team_id: teamId,
        amount: Number(counterAmount) * 10000,
      })
      if (res.success && res.data) {
        setCounterSuccess(true)
        fetchOffers()
      } else {
        setCounterError(res.message || '反报价失败')
      }
    } catch (err) {
      setCounterError(err instanceof Error ? err.message : '反报价请求失败')
    } finally {
      setCounterLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">转会市场</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">我的挂牌与报价处理</p>
        </div>
        <button
          onClick={openListModal}
          className="btn-primary flex items-center gap-2 text-sm"
        >
          <Plus className="w-4 h-4" />
          挂牌新球员
        </button>
      </div>

      <div className="flex flex-wrap gap-2 border-b-2 border-[#2D2D44]">
        {navTabs.map((tab) => (
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

      {/* Inner tabs */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('listings')}
          className={clsx(
            'px-4 py-2 text-sm font-medium border-2 transition-colors',
            activeTab === 'listings'
              ? 'border-[#0D7377] text-[#0D7377] bg-[#0D7377]/10'
              : 'border-[#2D2D44] text-[#4B4B6A] hover:text-[#8B8BA7]'
          )}
        >
          我的挂牌
        </button>
        <button
          onClick={() => setActiveTab('received')}
          className={clsx(
            'px-4 py-2 text-sm font-medium border-2 transition-colors',
            activeTab === 'received'
              ? 'border-[#0D7377] text-[#0D7377] bg-[#0D7377]/10'
              : 'border-[#2D2D44] text-[#4B4B6A] hover:text-[#8B8BA7]'
          )}
        >
          收到的报价
        </button>
      </div>

      {/* Tip */}
      <div className="flex items-center gap-3 p-3 bg-[#0D4A4D]/20 border-2 border-[#0D7377]/30">
        <WarningDiamond className="w-4 h-4 text-[#0D7377] flex-shrink-0" />
        <p className="text-sm text-[#8B8BA7]">
          挂牌价不得低于系统估值的80%。挂牌后3天内无法成交，期间可接收报价。成交后收取5%交易税。
        </p>
      </div>

      {/* My Listings Tab */}
      {activeTab === 'listings' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">当前挂牌中</h3>
          {listingsLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
            </div>
          )}
          {listingsError && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4" />
              {listingsError}
            </div>
          )}
          {!listingsLoading && !listingsError && (
            <div className="space-y-3">
              {listings.map((l) => (
                <div key={l.listing_id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                  <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                    <span className={clsx('text-xs font-bold', POSITION_COLORS[l.position as keyof typeof POSITION_COLORS] || 'text-[#8B8BA7]')}>
                      {l.position}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <Link to={`/players/${l.player_id}`} className="text-sm font-medium text-white hover:text-[#0D7377] transition-colors">
                      {l.name}
                    </Link>
                    <p className="text-xs text-[#4B4B6A]">{l.age}岁 · OVR {l.ovr} · 估值 {(l.market_value / 10000).toFixed(1)}万</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-[#0D7377]">{(l.list_price / 10000).toFixed(1)}万</p>
                    <p className="text-xs text-[#4B4B6A]">挂牌价</p>
                  </div>
                  <div className="text-right">
                    {l.deadline && (
                      <p className="text-xs text-yellow-400 flex items-center gap-1">
                        <Clock className="w-3 h-3" />
                        截止 {new Date(l.deadline).toLocaleDateString()}
                      </p>
                    )}
                  </div>
                  <button
                    onClick={() => handleCancel(l.listing_id)}
                    disabled={actionLoading[`cancel-${l.listing_id}`]}
                    className="px-3 py-1.5 bg-[#2D2D44] hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/50 text-[#8B8BA7] text-xs font-bold border-2 border-[#2D2D44] transition-colors disabled:opacity-50"
                  >
                    {actionLoading[`cancel-${l.listing_id}`] ? '...' : '撤牌'}
                  </button>
                </div>
              ))}
              {listings.length === 0 && (
                <div className="text-center py-8 text-[#8B8BA7]">
                  <p className="text-sm">暂无挂牌中的球员</p>
                  <p className="text-xs mt-1">点击上方「挂牌新球员」开始</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Received Offers Tab */}
      {activeTab === 'received' && (
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">收到的报价</h3>
          {offersLoading && (
            <div className="flex items-center justify-center py-8">
              <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
            </div>
          )}
          {offersError && (
            <div className="flex items-center gap-2 p-3 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
              <AlertTriangle className="w-4 h-4" />
              {offersError}
            </div>
          )}
          {!offersLoading && !offersError && (
            <>
              <div className="space-y-3">
                {offers.map((o) => (
                  <div key={o.offer_id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-white">
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
                      {o.status === 'PENDING' && (
                        <>
                          <button
                            onClick={() => handleAccept(o.offer_id)}
                            disabled={actionLoading[`accept-${o.offer_id}`]}
                            className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold border-2 border-emerald-700 transition-colors disabled:opacity-50"
                          >
                            {actionLoading[`accept-${o.offer_id}`] ? '...' : '接受'}
                          </button>
                          {o.can_counter && o.offer_kind === 'INITIAL' && (
                            <button
                              onClick={() => openCounterModal(o)}
                              className="px-3 py-1.5 bg-yellow-600 hover:bg-yellow-700 text-white text-xs font-bold border-2 border-yellow-700 transition-colors"
                            >
                              反报价
                            </button>
                          )}
                          <button
                            onClick={() => handleReject(o.offer_id)}
                            disabled={actionLoading[`reject-${o.offer_id}`]}
                            className="px-3 py-1.5 bg-[#2D2D44] hover:bg-red-500/20 hover:text-red-400 hover:border-red-500/50 text-[#8B8BA7] text-xs font-bold border-2 border-[#2D2D44] transition-colors disabled:opacity-50"
                          >
                            {actionLoading[`reject-${o.offer_id}`] ? '...' : '拒绝'}
                          </button>
                        </>
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
                  <div className="text-center py-8 text-[#8B8BA7]">
                    <p className="text-sm">暂无收到的报价</p>
                  </div>
                )}
              </div>
              {offersTotalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <button
                    onClick={() => setOffersPage(p => Math.max(1, p - 1))}
                    disabled={offersPage === 1}
                    className="p-2 bg-[#12121A] border-2 border-[#2D2D44] text-[#8B8BA7] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <span className="text-sm text-[#8B8BA7]">第 {offersPage} / {offersTotalPages} 页</span>
                  <button
                    onClick={() => setOffersPage(p => Math.min(offersTotalPages, p + 1))}
                    disabled={offersPage === offersTotalPages}
                    className="p-2 bg-[#12121A] border-2 border-[#2D2D44] text-[#8B8BA7] hover:text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* List Player Modal */}
      {showListModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-lg bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-lg max-h-[80vh] flex flex-col">
            <div className="flex items-center justify-between p-4 border-b-2 border-[#2D2D44]">
              <h3 className="text-lg font-bold text-white">
                {listSuccess ? '挂牌成功' : '挂牌新球员'}
              </h3>
              <button
                onClick={() => setShowListModal(false)}
                className="text-[#8B8BA7] hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-4 overflow-y-auto flex-1">
              {listSuccess ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <Check className="w-5 h-5" />
                    <span className="font-bold">球员已成功挂牌！</span>
                  </div>
                  <button
                    onClick={() => setShowListModal(false)}
                    className="w-full py-2 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                  >
                    确定
                  </button>
                </div>
              ) : (
                <>
                  {rosterLoading && (
                    <div className="flex items-center justify-center py-8">
                      <Loader className="w-6 h-6 text-[#0D7377] animate-spin" />
                    </div>
                  )}

                  {listError && (
                    <div className="flex items-center gap-2 p-3 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
                      <AlertTriangle className="w-4 h-4" />
                      {listError}
                    </div>
                  )}

                  {!rosterLoading && (
                    <>
                      <div className="space-y-2">
                        <label className="text-xs text-[#8B8BA7]">选择球员</label>
                        <div className="max-h-48 overflow-y-auto space-y-1 border-2 border-[#2D2D44]">
                          {roster.map((p) => (
                            <button
                              key={p.id}
                              onClick={() => selectPlayerForListing(p)}
                              className={clsx(
                                'w-full flex items-center gap-3 p-2 text-left transition-colors',
                                selectedPlayer?.id === p.id
                                  ? 'bg-[#0D7377]/20 border border-[#0D7377]/50'
                                  : 'hover:bg-[#1E1E2D] border border-transparent'
                              )}
                            >
                              <span className={clsx('text-xs px-1.5 py-0.5 font-bold', POSITION_COLORS[p.position] || 'bg-[#2D2D44] text-white')}>
                                {p.position}
                              </span>
                              <span className="text-sm text-white flex-1">{p.name}</span>
                              <span className="text-xs text-[#8B8BA7]">OVR {p.ovr}</span>
                            </button>
                          ))}
                          {roster.length === 0 && (
                            <p className="text-sm text-[#8B8BA7] p-3">暂无可用球员</p>
                          )}
                        </div>
                      </div>

                      {selectedPlayer && (
                        <div className="space-y-3 pt-2">
                          <div className="flex justify-between text-sm">
                            <span className="text-[#8B8BA7]">球员</span>
                            <span className="text-white font-medium">{selectedPlayer.name}</span>
                          </div>
                          <div className="flex justify-between text-sm">
                            <span className="text-[#8B8BA7]">系统估值</span>
                            <span className="text-[#0D7377] font-bold">
                              {valuationLoading ? '计算中...' : valuation !== null ? `${(valuation / 10000).toFixed(1)}万` : '未知'}
                            </span>
                          </div>
                          {valuation !== null && (
                            <p className="text-xs text-[#4B4B6A]">
                              最低挂牌价: {Math.round(valuation * 0.8 / 10000)}万（估值的80%）
                            </p>
                          )}
                          <div>
                            <label className="text-xs text-[#8B8BA7] mb-1 block">挂牌价（万）</label>
                            <input
                              type="number"
                              value={listPrice}
                              onChange={e => setListPrice(e.target.value)}
                              className="w-full bg-[#1A1A2E] border-2 border-[#2D2D44] px-3 py-2 text-sm text-white focus:border-[#0D7377] outline-none"
                              placeholder="输入挂牌价格"
                            />
                          </div>
                        </div>
                      )}

                      <div className="flex gap-2 pt-2">
                        <button
                          onClick={() => setShowListModal(false)}
                          className="flex-1 py-2 bg-[#2D2D44] hover:bg-[#3D3D5C] text-white text-sm font-bold border-2 border-[#2D2D44] transition-colors"
                        >
                          取消
                        </button>
                        <button
                          onClick={submitListing}
                          disabled={listLoading || !selectedPlayer || !listPrice || (valuation !== null && Number(listPrice) < valuation * 0.8 / 10000)}
                          className="flex-1 py-2 bg-[#0D7377] hover:bg-[#0A5A5D] disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                        >
                          {listLoading ? '处理中...' : '确认挂牌'}
                        </button>
                      </div>
                    </>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Counter Offer Modal */}
      {counterOffer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md bg-[#12121A] border-2 border-[#2D2D44] shadow-pixel-lg">
            <div className="flex items-center justify-between p-4 border-b-2 border-[#2D2D44]">
              <h3 className="text-lg font-bold text-white">
                {counterSuccess ? '反报价已发送' : `反报价: ${counterOffer.player_name}`}
              </h3>
              <button onClick={closeCounterModal} className="text-[#8B8BA7] hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="p-4 space-y-4">
              {counterSuccess ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 text-emerald-400">
                    <CornerUpRight className="w-5 h-5" />
                    <span className="font-bold">反报价发送成功！</span>
                  </div>
                  <button
                    onClick={closeCounterModal}
                    className="w-full py-2 bg-[#0D7377] hover:bg-[#0A5A5D] text-white text-sm font-bold border-2 border-[#0A5A5D] transition-colors"
                  >
                    确定
                  </button>
                </div>
              ) : (
                <>
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">球员</span>
                      <span className="text-white">{counterOffer.player_name}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8B8BA7]">对方报价</span>
                      <span className="text-[#0D7377] font-bold">{(counterOffer.amount / 10000).toFixed(1)}万</span>
                    </div>
                  </div>
                  <div>
                    <label className="text-xs text-[#8B8BA7] mb-1 block">反报价金额（万）</label>
                    <input
                      type="number"
                      value={counterAmount}
                      onChange={e => setCounterAmount(e.target.value)}
                      className="w-full bg-[#1A1A2E] border-2 border-[#2D2D44] px-3 py-2 text-sm text-white focus:border-[#0D7377] outline-none"
                      placeholder="输入反报价金额（不超过对方报价150%）"
                    />
                  </div>
                  {counterError && (
                    <div className="flex items-center gap-2 p-3 bg-red-500/10 border-2 border-red-500/30 text-red-400 text-sm">
                      <AlertTriangle className="w-4 h-4" />
                      {counterError}
                    </div>
                  )}
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeCounterModal}
                      className="flex-1 py-2 bg-[#2D2D44] hover:bg-[#3D3D5C] text-white text-sm font-bold border-2 border-[#2D2D44] transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={submitCounter}
                      disabled={counterLoading || !counterAmount || Number(counterAmount) <= 0}
                      className="flex-1 py-2 bg-yellow-600 hover:bg-yellow-700 disabled:opacity-40 disabled:cursor-not-allowed text-white text-sm font-bold border-2 border-yellow-700 transition-colors"
                    >
                      {counterLoading ? '发送中...' : '确认反报价'}
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
