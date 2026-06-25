import { useState, useEffect, useCallback, useMemo } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { clsx } from 'clsx'
import { Eye, ChevronLeft, ChevronRight, Search } from '../../components/ui/pixel-icons'
import { TransferTabs } from '../../components/transfer/TransferTabs'
import { PageHeader } from '../../components/ui/PageHeader'
import { Modal } from '../../components/ui/Modal'
import Button from '../../components/ui/Button'
import api from '../../api/client'
import type { MarketPlayer } from '../../types/transfer'
import { POSITION_COLORS } from '../../types/player'

const positionOptions = [
  { value: '', label: '全部位置' },
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

const ovrOptions = [
  { value: '', label: '全部能力' },
  { value: '60', label: '60+' },
  { value: '65', label: '65+' },
  { value: '70', label: '70+' },
  { value: '75', label: '75+' },
]

interface Filters {
  position: string
  min_ovr: string
  max_ovr: string
  min_age: string
  max_age: string
  is_listed: string
  search: string
}

const potentialTone: Record<string, string> = {
  S: 'tone-lime',
  A: 'tone-sky',
  B: 'tone-amber',
  C: 'tone-coral',
  D: 'tone-coral',
}

function formatMoney(n: number) {
  return `${(n / 10000).toFixed(1)}万`
}

export default function TransferMarket() {
  const navigate = useNavigate()
  const [players, setPlayers] = useState<MarketPlayer[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [filters, setFilters] = useState<Filters>({
    position: '',
    min_ovr: '',
    max_ovr: '',
    min_age: '',
    max_age: '',
    is_listed: '',
    search: '',
  })

  const [offerPlayer, setOfferPlayer] = useState<MarketPlayer | null>(null)
  const [offerAmount, setOfferAmount] = useState('')
  const [offerLoading, setOfferLoading] = useState(false)
  const [offerError, setOfferError] = useState<string | null>(null)
  const [offerSuccess, setOfferSuccess] = useState(false)

  const fetchPlayers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, unknown> = { page, page_size: 20 }
      if (filters.position) params.position = filters.position
      if (filters.min_ovr) params.min_ovr = Number(filters.min_ovr)
      if (filters.max_ovr) params.max_ovr = Number(filters.max_ovr)
      if (filters.min_age) params.min_age = Number(filters.min_age)
      if (filters.max_age) params.max_age = Number(filters.max_age)
      if (filters.is_listed) {
        params.is_listed = filters.is_listed === 'listed'
      }

      const res = await api.getTransferMarket(params)
      if (res.success && res.data) {
        let items = res.data.items
        if (filters.search) {
          const s = filters.search.toLowerCase()
          items = items.filter(p => p.name.toLowerCase().includes(s) || p.team_name.toLowerCase().includes(s))
        }
        setPlayers(items)
        setTotalPages(res.data.total_pages)
      } else {
        setPlayers([])
        setTotalPages(1)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取数据失败')
    } finally {
      setLoading(false)
    }
  }, [page, filters])

  useEffect(() => {
    fetchPlayers()
  }, [fetchPlayers])

  const handleFilterChange = (key: keyof Filters, value: string) => {
    setFilters(prev => ({ ...prev, [key]: value }))
    setPage(1)
  }

  const openOfferModal = (player: MarketPlayer) => {
    setOfferPlayer(player)
    setOfferAmount(player.list_price ? String(Math.round(player.list_price / 10000)) : String(Math.round(player.market_value / 10000)))
    setOfferError(null)
    setOfferSuccess(false)
  }

  const closeOfferModal = () => {
    setOfferPlayer(null)
    setOfferAmount('')
    setOfferError(null)
    setOfferSuccess(false)
  }

  const submitOffer = async () => {
    if (!offerPlayer || !offerAmount) return
    setOfferLoading(true)
    setOfferError(null)
    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setOfferError('无法获取球队信息')
        setOfferLoading(false)
        return
      }
      const res = await api.createTransferOffer({
        player_id: offerPlayer.player_id,
        buyer_team_id: teamRes.data.id,
        amount: Number(offerAmount) * 10000,
        listing_id: offerPlayer.listing_id || undefined,
      })
      if (res.success && res.data) {
        setOfferSuccess(true)
      } else {
        setOfferError(res.message || '报价失败')
      }
    } catch (err) {
      setOfferError(err instanceof Error ? err.message : '报价请求失败')
    } finally {
      setOfferLoading(false)
    }
  }

  const list = useMemo(() => players, [players])

  return (
    <div className="fresh-page-shell space-y-6">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm font-bold text-[#466353] hover:text-[#173126] transition-colors"
      >
        <ChevronLeft className="w-4 h-4" />
        返回上一页
      </button>

      <PageHeader title="球员拍卖市场" subtitle="浏览球员并发送转会报价" />

      <TransferTabs />

      <section className="fresh-filter-strip">
        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#7b927f]" />
          <input
            type="text"
            placeholder="搜索球员或球队..."
            value={filters.search}
            onChange={e => handleFilterChange('search', e.target.value)}
            className="w-full pl-9 pr-4 py-2 text-sm outline-none focus:border-[#59C7EE] transition-colors"
          />
        </div>
        <select
          value={filters.position}
          onChange={e => handleFilterChange('position', e.target.value)}
          className="px-3 py-2 text-sm outline-none focus:border-[#59C7EE]"
        >
          {positionOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={filters.min_ovr}
          onChange={e => handleFilterChange('min_ovr', e.target.value)}
          className="px-3 py-2 text-sm outline-none focus:border-[#59C7EE]"
        >
          {ovrOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <input
          type="number"
          placeholder="最低年龄"
          value={filters.min_age}
          onChange={e => handleFilterChange('min_age', e.target.value)}
          className="w-24 px-3 py-2 text-sm outline-none focus:border-[#59C7EE]"
        />
        <input
          type="number"
          placeholder="最高年龄"
          value={filters.max_age}
          onChange={e => handleFilterChange('max_age', e.target.value)}
          className="w-24 px-3 py-2 text-sm outline-none focus:border-[#59C7EE]"
        />
        <select
          value={filters.is_listed}
          onChange={e => handleFilterChange('is_listed', e.target.value)}
          className="px-3 py-2 text-sm outline-none focus:border-[#59C7EE]"
        >
          <option value="">全部状态</option>
          <option value="listed">仅挂牌</option>
          <option value="unlisted">未挂牌</option>
        </select>
      </section>

      {loading && (
        <div className="fresh-loading-lines">
          {Array.from({ length: 6 }).map((_, i) => <span key={`load-${i}`} />)}
        </div>
      )}

      {error && (
        <div className="p-4 bg-[#FF6F59]/12 border-2 border-[#FF6F59]/40 text-[#FF6F59] text-sm font-bold">
          {error}
        </div>
      )}

      {!loading && !error && (
        <>
          <section className="fresh-section-title">
            <h2>球员清单</h2>
            <span>共 {players.length} 名</span>
          </section>

          <div className="space-y-2">
            {list.map((p) => (
              <div key={p.player_id} className="fresh-roster-row group" style={{ gridTemplateColumns: '48px minmax(0, 1fr) repeat(5, auto)' }}>
                <div className="fresh-player-initial w-12 h-12">{p.name.charAt(0)}</div>

                <div className="min-w-0 px-2">
                  <div className="fresh-row-title">
                    <strong>{p.name}</strong>
                    <span className={clsx('px-1.5 py-0.5 text-[10px]', POSITION_COLORS[p.position as keyof typeof POSITION_COLORS] || 'bg-[#F8FFD2] text-[#173126] border border-[#1F5F43]/20')}>
                      {p.position}
                    </span>
                  </div>
                  <p>{p.team_name}</p>
                </div>

                <div className="text-center min-w-[56px]">
                  <span className="block text-[10px] font-black text-[#466353]">年龄</span>
                  <strong className="text-sm font-black text-[#173126]">{p.age}</strong>
                </div>
                <div className="text-center min-w-[56px]">
                  <span className="block text-[10px] font-black text-[#466353]">OVR</span>
                  <strong className="text-sm font-black text-[#173126]">{p.ovr}</strong>
                </div>
                <div className="text-center min-w-[48px]">
                  <span className="block text-[10px] font-black text-[#466353]">潜力</span>
                  <span className={clsx('inline-block min-w-[24px] px-1 py-0.5 text-xs font-black border border-[#1F5F43]', potentialTone[p.potential_letter] || 'bg-white text-[#173126]')}>
                    {p.potential_letter}
                  </span>
                </div>
                <div className="text-right min-w-[90px]">
                  <span className="block text-[10px] font-black text-[#466353]">估值</span>
                  <strong className="text-sm font-black text-[#173126]">{formatMoney(p.market_value)}</strong>
                </div>
                <div className="flex items-center justify-end gap-2 min-w-[140px]">
                  {p.is_listed && p.list_price && (
                    <span className="text-xs font-black text-[#C77A00]">{formatMoney(p.list_price)}</span>
                  )}
                  {p.is_listed && (
                    <span className="px-2 py-0.5 text-[10px] font-black bg-[#B9EF3F]/35 text-[#1F5F43] border border-[#1F5F43]/30">
                      挂牌
                    </span>
                  )}
                  <Link
                    to={`/players/${p.player_id}`}
                    className="p-1.5 bg-white border-2 border-[#1F5F43]/30 text-[#466353] hover:text-[#173126] hover:border-[#1F5F43] transition-colors"
                    title="查看球员"
                  >
                    <Eye className="w-3.5 h-3.5" />
                  </Link>
                  <Button size="sm" onClick={() => openOfferModal(p)}>
                    报价
                  </Button>
                </div>
              </div>
            ))}

            {players.length === 0 && (
              <div className="fresh-empty">暂无符合条件的球员</div>
            )}
          </div>

          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-2">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 bg-white border-2 border-[#1F5F43]/30 text-[#466353] hover:text-[#173126] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm font-black text-[#466353]">第 {page} / {totalPages} 页</span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 bg-white border-2 border-[#1F5F43]/30 text-[#466353] hover:text-[#173126] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}

      <Modal
        isOpen={!!offerPlayer}
        onClose={closeOfferModal}
        title={offerSuccess ? '报价已发送' : `报价: ${offerPlayer?.name}`}
        size="md"
        footer={
          offerSuccess ? (
            <Button onClick={closeOfferModal}>确定</Button>
          ) : (
            <>
              <Button variant="ghost" onClick={closeOfferModal}>取消</Button>
              <Button onClick={submitOffer} isLoading={offerLoading} disabled={!offerAmount || Number(offerAmount) <= 0}>
                确认报价
              </Button>
            </>
          )
        }
      >
        {offerSuccess ? (
          <div className="space-y-3">
            <p className="text-[#1F5F43] font-black">报价发送成功！</p>
            <p className="text-sm font-bold text-[#466353]">报价金额：<span className="text-[#173126] font-black">{offerAmount}万</span></p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="fresh-stat-tile">
                <span>球员</span>
                <strong>{offerPlayer?.name}</strong>
              </div>
              <div className="fresh-stat-tile">
                <span>所属球队</span>
                <strong>{offerPlayer?.team_name}</strong>
              </div>
              <div className="fresh-stat-tile">
                <span>系统估值</span>
                <strong>{offerPlayer && formatMoney(offerPlayer.market_value)}</strong>
              </div>
              {offerPlayer?.list_price && (
                <div className="fresh-stat-tile">
                  <span>挂牌价</span>
                  <strong className="text-[#C77A00]">{formatMoney(offerPlayer.list_price)}</strong>
                </div>
              )}
            </div>

            <div>
              <label className="block text-xs font-black text-[#466353] mb-1">报价金额（万）</label>
              <input
                type="number"
                value={offerAmount}
                onChange={e => setOfferAmount(e.target.value)}
                className="w-full px-3 py-2 bg-white/90 border-2 border-[#1F5F43]/30 text-sm text-[#173126] outline-none focus:border-[#59C7EE]"
                placeholder="输入报价金额"
              />
            </div>

            {offerError && (
              <div className="p-3 bg-[#FF6F59]/12 border-2 border-[#FF6F59]/40 text-[#FF6F59] text-sm font-bold">
                {offerError}
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  )
}
