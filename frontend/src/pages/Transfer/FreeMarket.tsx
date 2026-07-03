import { useState, useEffect, useCallback } from 'react'
import { X } from 'lucide-react'
import { Link } from 'react-router-dom'
import { 
  ChevronLeft,
  ChevronRight,
  Loader,
} from '../../components/ui/pixel-icons'
import { TransferTabs } from '../../components/transfer/TransferTabs'
import { PageHeader } from '../../components/ui/PageHeader'
import Avatar from '../../components/ui/Avatar'
import api from '../../api/client'
import type { FreeMarketPlayer, FreeMarketPreview, FreeMarketSignResult } from '../../types/free_market'
import { ORIGIN_NAMES, ORIGIN_COLORS } from '../../types/free_market'

const positionOptions = [
  { value: '', label: '全部位置' },
  { value: 'FW', label: '前锋' },
  { value: 'MF', label: '中场' },
  { value: 'DF', label: '后卫' },
  { value: 'GK', label: '门将' },
]

const originOptions = [
  { value: '', label: '全部来源' },
  { value: 'contract_expired', label: '合同到期' },
  { value: 'released', label: '解约球员' },
  { value: 'academy_released', label: '青训新人' },
  { value: 'auto_generated', label: '系统兜底' },
]

const positionColors: Record<string, string> = {
  FW: 'bg-[#FF6F59] text-[#F8FFD2]',
  MF: 'bg-[#1F5F43] text-[#173126]',
  DF: 'bg-[#59C7EE] text-[#173126]',
  GK: 'bg-[#FFC247] text-[#173126]',
}

interface Filters {
  position: string
  min_ovr: string
  max_ovr: string
  min_age: string
  max_age: string
  origin: string
}

interface FreeMarketProps {
  embedded?: boolean
}

export default function FreeMarket({ embedded }: FreeMarketProps = {}) {
  const [players, setPlayers] = useState<FreeMarketPlayer[]>([])
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
    origin: '',
  })
  const [showFilters, setShowFilters] = useState(false)

  // Modal states
  const [selectedPlayer, setSelectedPlayer] = useState<FreeMarketPlayer | null>(null)
  const [preview, setPreview] = useState<FreeMarketPreview | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewError, setPreviewError] = useState<string | null>(null)
  const [signing, setSigning] = useState(false)
  const [signSuccess, setSignSuccess] = useState<FreeMarketSignResult | null>(null)

  const fetchPlayers = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const params: Record<string, string | number> = { page, page_size: 24 }
      if (filters.position) params.position = filters.position
      if (filters.min_ovr) params.min_ovr = Number(filters.min_ovr)
      if (filters.max_ovr) params.max_ovr = Number(filters.max_ovr)
      if (filters.min_age) params.min_age = Number(filters.min_age)
      if (filters.max_age) params.max_age = Number(filters.max_age)
      if (filters.origin) params.origin = filters.origin

      const res = await api.getFreeMarketList(params)
      if (res.success && res.data) {
        setPlayers(res.data.items)
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

  const resetFilters = () => {
    setFilters({ position: '', min_ovr: '', max_ovr: '', min_age: '', max_age: '', origin: '' })
    setPage(1)
  }

  const openSignModal = async (player: FreeMarketPlayer) => {
    setSelectedPlayer(player)
    setPreview(null)
    setPreviewError(null)
    setSignSuccess(null)
    setPreviewLoading(true)

    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setPreviewError('无法获取球队信息')
        setPreviewLoading(false)
        return
      }
      const teamId = teamRes.data.id

      const res = await api.previewFreeMarketSign(player.listing_id, {
        team_id: teamId,
        years: 2,
        wage: player.recommended_wage,
        squad_role: 'rotation',
      })
      if (res.success && res.data) {
        setPreview(res.data)
      } else {
        setPreviewError(res.message || '预览失败')
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : '预览请求失败')
    } finally {
      setPreviewLoading(false)
    }
  }

  const handleSign = async () => {
    if (!selectedPlayer || !preview) return
    setSigning(true)
    setPreviewError(null)
    try {
      const teamRes = await api.get<{ id: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setPreviewError('无法获取球队信息')
        setSigning(false)
        return
      }
      const teamId = teamRes.data.id

      const res = await api.signFreeMarketPlayer(selectedPlayer.listing_id, {
        team_id: teamId,
        years: 2,
        wage: selectedPlayer.recommended_wage,
        squad_role: 'rotation',
      })
      if (res.success && res.data) {
        setSignSuccess(res.data)
        // 刷新列表
        fetchPlayers()
      } else {
        setPreviewError(res.message || '签约失败')
      }
    } catch (err) {
      setPreviewError(err instanceof Error ? err.message : '签约请求失败')
    } finally {
      setSigning(false)
    }
  }

  const closeModal = () => {
    setSelectedPlayer(null)
    setPreview(null)
    setPreviewError(null)
    setSignSuccess(null)
  }

  return (
    <div className={embedded ? 'space-y-4' : 'space-y-6 max-w-[1400px]'}>
      {!embedded && (
        <>
          <PageHeader
            title="自由市场"
            subtitle="签约自由球员"
            action={
              <button
                onClick={() => setShowFilters(!showFilters)}
                className="px-3 py-2 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-sm text-[#466353] hover:text-[#173126] hover:border-[#1F5F43] transition-colors"
              >
                筛选
              </button>
            }
          />

          <TransferTabs />
        </>
      )}

      {embedded && (
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-bold text-[#173126]">自由球员</h3>
          <button
            onClick={() => setShowFilters(!showFilters)}
            className="px-3 py-2 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-sm text-[#466353] hover:text-[#173126] hover:border-[#1F5F43] transition-colors"
          >
            筛选
          </button>
        </div>
      )}

      {/* 筛选面板 */}
      {showFilters && (
        <div className="p-4 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 space-y-3">
          <div className="flex flex-wrap gap-3">
            <select
              value={filters.position}
              onChange={e => handleFilterChange('position', e.target.value)}
              className="px-3 py-2 bg-white border-2 border-[#1F5F43]/20 text-sm text-[#173126] focus:border-[#1F5F43] outline-none"
            >
              {positionOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <select
              value={filters.origin}
              onChange={e => handleFilterChange('origin', e.target.value)}
              className="px-3 py-2 bg-white border-2 border-[#1F5F43]/20 text-sm text-[#173126] focus:border-[#1F5F43] outline-none"
            >
              {originOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
            <input
              type="number"
              placeholder="最低OVR"
              value={filters.min_ovr}
              onChange={e => handleFilterChange('min_ovr', e.target.value)}
              className="w-24 px-3 py-2 bg-white border-2 border-[#1F5F43]/20 text-sm text-[#173126] placeholder:text-[#8B5A2B]/40 focus:border-[#1F5F43] outline-none"
            />
            <input
              type="number"
              placeholder="最高OVR"
              value={filters.max_ovr}
              onChange={e => handleFilterChange('max_ovr', e.target.value)}
              className="w-24 px-3 py-2 bg-white border-2 border-[#1F5F43]/20 text-sm text-[#173126] placeholder:text-[#8B5A2B]/40 focus:border-[#1F5F43] outline-none"
            />
            <input
              type="number"
              placeholder="最低年龄"
              value={filters.min_age}
              onChange={e => handleFilterChange('min_age', e.target.value)}
              className="w-24 px-3 py-2 bg-white border-2 border-[#1F5F43]/20 text-sm text-[#173126] placeholder:text-[#8B5A2B]/40 focus:border-[#1F5F43] outline-none"
            />
            <input
              type="number"
              placeholder="最高年龄"
              value={filters.max_age}
              onChange={e => handleFilterChange('max_age', e.target.value)}
              className="w-24 px-3 py-2 bg-white border-2 border-[#1F5F43]/20 text-sm text-[#173126] placeholder:text-[#8B5A2B]/40 focus:border-[#1F5F43] outline-none"
            />
            <button
              onClick={resetFilters}
              className="px-3 py-2 text-sm text-[#466353] hover:text-[#173126] border-2 border-[#1F5F43]/20 hover:border-[#1F5F43] transition-colors"
            >
              重置
            </button>
          </div>
        </div>
      )}

      {/* 加载 & 错误 */}
      {loading && (
        <div className="flex items-center justify-center py-12 text-sm text-[#466353]">
          加载中...
        </div>
      )}
      {error && (
        <div className="p-4 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">
          {error}
        </div>
      )}

      {/* 球员列表 */}
      {!loading && !error && (
        <>
          <div className="space-y-2">
            <div
              className="fresh-roster-row text-[10px] font-black text-[#466353] uppercase tracking-wider opacity-80 pointer-events-none"
              style={{ gridTemplateColumns: '56px minmax(0, 1fr) repeat(3, 72px) 110px 110px 90px 100px' }}
            >
              <span className="text-center">头像</span>
              <span className="px-2">球员 / 来源</span>
              <span className="text-center">年龄</span>
              <span className="text-center">OVR</span>
              <span className="text-center">潜力</span>
              <span className="text-center">签字费</span>
              <span className="text-center">建议周薪</span>
              <span className="text-center">上架</span>
              <span className="text-right px-2">操作</span>
            </div>

            {players.map((p) => (
              <div
                key={p.listing_id}
                className="fresh-roster-row group"
                style={{ gridTemplateColumns: '56px minmax(0, 1fr) repeat(3, 72px) 110px 110px 90px 100px' }}
              >
                <Avatar src={p.avatar_url} name={p.name} size="lg" />

                <div className="min-w-0 px-2 overflow-hidden">
                  <div className="flex items-center gap-2">
                    <Link
                      to={`/players/${p.player_id}`}
                      className="truncate text-sm font-black text-[#173126] hover:text-[#1F5F43] transition-colors"
                    >
                      {p.name}
                    </Link>
                    <span className={clsx('px-1.5 py-0.5 text-[10px]', positionColors[p.position] || 'bg-[#F8FFD2] text-[#173126]')}>
                      {p.position}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-xs">
                    <span className={clsx(ORIGIN_COLORS[p.origin as keyof typeof ORIGIN_COLORS] || 'text-[#466353]')}>
                      {ORIGIN_NAMES[p.origin as keyof typeof ORIGIN_NAMES] || p.origin}
                    </span>
                    {p.is_rookie_protected && (
                      <span className="px-1.5 py-0.5 bg-[#B9EF3F]/20 text-[#1F5F43] border border-[#1F5F43]/30">
                        新人保护
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-center">
                  <strong className="text-sm font-black text-[#173126]">{p.age}</strong>
                </div>
                <div className="text-center">
                  <strong className="text-sm font-black text-[#173126]">{p.ovr}</strong>
                </div>
                <div className="text-center">
                  <strong className="text-sm font-black text-[#173126]">{p.potential_letter}</strong>
                </div>
                <div className="text-center">
                  <strong className="text-sm font-black text-[#1F5F43]">{p.signing_fee}万</strong>
                </div>
                <div className="text-center">
                  <strong className="text-sm font-black text-[#173126]">{p.recommended_wage}万</strong>
                </div>
                <div className="text-center">
                  <strong className="text-sm font-black text-[#466353]">第{p.listed_at_day}天</strong>
                </div>
                <div className="flex items-center justify-end">
                  <button
                    onClick={() => openSignModal(p)}
                    className="px-4 py-1.5 bg-[#1F5F43] hover:bg-[#173126] text-[#F8FFD2] text-xs font-bold border-2 border-[#173126] transition-colors"
                  >
                    签约
                  </button>
                </div>
              </div>
            ))}
          </div>

          {players.length === 0 && (
            <div className="text-center py-12 text-[#466353]">
              <p className="text-sm">暂无符合条件的自由球员</p>
            </div>
          )}

          {/* 分页 */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-2 pt-4">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="p-2 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#466353] hover:text-[#173126] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-[#466353]">
                第 {page} / {totalPages} 页
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="p-2 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 text-[#466353] hover:text-[#173126] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}

      {/* 签约弹窗 */}
      {selectedPlayer && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1F5F43]/35 p-4">
          <div className="w-full max-w-md bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 shadow-pixel-lg">
            <div className="flex items-center justify-between p-4 border-b-2 border-[#1F5F43]/20">
              <h3 className="text-lg font-bold text-[#173126]">
                {signSuccess ? '签约成功' : `签约 ${selectedPlayer.name}`}
              </h3>
              <button onClick={closeModal} className="text-[#466353] hover:text-[#173126]">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-4 space-y-4">
              {previewLoading && (
                <div className="flex items-center justify-center py-8">
                  <Loader className="w-6 h-6 text-[#1F5F43] animate-spin" />
                </div>
              )}

              {previewError && (
                <div className="p-3 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">
                  {previewError}
                </div>
              )}

              {signSuccess && (
                <div className="space-y-3">
                  <div className="text-[#1F5F43]">
                    <span className="font-bold">签约完成！</span>
                  </div>
                  <div className="space-y-2 text-sm text-[#466353]">
                    <p>合同ID: <span className="text-[#173126] font-mono">{signSuccess.contract_id}</span></p>
                    <p>球员ID: <span className="text-[#173126] font-mono">{signSuccess.player_id}</span></p>
                    <p>签字费: <span className="text-[#1F5F43] font-bold">{signSuccess.signing_fee}万</span></p>
                  </div>
                  <button
                    onClick={closeModal}
                    className="w-full py-2 bg-[#1F5F43] hover:bg-[#173126] text-[#F8FFD2] text-sm font-bold border-2 border-[#173126] transition-colors"
                  >
                    确定
                  </button>
                </div>
              )}

              {preview && !signSuccess && (
                <div className="space-y-3">
                  <div className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span className="text-[#466353]">签字费</span>
                      <span className="text-[#1F5F43] font-bold">{preview.signing_fee}万</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#466353]">周薪</span>
                      <span className="text-[#173126]">{preview.offered_wage}万</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#466353]">建议周薪</span>
                      <span className="text-[#173126]">{preview.recommended_wage}万</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#466353]">薪资满意度</span>
                      <span className={preview.wage_ratio >= 1 ? 'text-[#1F5F43]' : preview.wage_ratio >= 0.8 ? 'text-[#C77A00]' : 'text-[#FF6F59]'}>
                        {Math.round(preview.wage_ratio * 100)}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#466353]">球员反应</span>
                      <span className="text-[#173126]">{preview.visible_reaction}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#466353]">签约后薪资帽占比</span>
                      <span className="text-[#173126]">{Math.round(preview.wage_cap_after_pct * 100)}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#466353]">余额（扣签字费后）</span>
                      <span className={preview.can_pay_signing_fee ? 'text-[#1F5F43]' : 'text-[#FF6F59]'}>
                        {preview.balance_after_fee}万
                      </span>
                    </div>
                  </div>

                  {preview.warnings.length > 0 && (
                    <div className="space-y-1">
                      {preview.warnings.map((w, i) => (
                        <p key={i} className="text-xs text-[#C77A00]">
                          {w}
                        </p>
                      ))}
                    </div>
                  )}

                  {!preview.can_submit && (
                    <div className="p-2 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-xs">
                      当前条件不满足签约要求
                    </div>
                  )}
                  {!preview.can_pay_signing_fee && (
                    <div className="p-2 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-xs">
                      余额不足以支付签字费
                    </div>
                  )}

                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeModal}
                      className="flex-1 py-2 bg-[#F8FFD2] hover:bg-[#F8FFD2] text-[#173126] text-sm font-bold border-2 border-[#1F5F43]/20 transition-colors"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleSign}
                      disabled={signing || !preview.can_submit || !preview.can_pay_signing_fee}
                      className="flex-1 py-2 bg-[#1F5F43] hover:bg-[#173126] disabled:opacity-40 disabled:cursor-not-allowed text-[#173126] text-sm font-bold border-2 border-[#173126] transition-colors"
                    >
                      {signing ? '签约中...' : '确认签约'}
                    </button>
                  </div>
                </div>
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
