import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Modal } from '../ui/Modal'
import Button from '../ui/Button'
import api from '../../api/client'
import type { SquadRole } from '../../types/player'

interface ActionPlayer {
  id: string
  name: string
  market_value?: number
  team_id?: string | null
  wage?: number
  squad_role?: SquadRole
  contract_type?: string
}

const SQUAD_ROLE_OPTIONS = [
  { value: 'key_player', label: '核心' },
  { value: 'first_team', label: '主力' },
  { value: 'rotation', label: '轮换' },
  { value: 'backup', label: '替补' },
  { value: 'hot_prospect', label: '新星' },
  { value: 'youngster', label: '青训' },
]

function formatMoney(n: number) {
  return `${(n / 10000).toFixed(1)}万`
}

interface PlayerActionBarProps {
  player: ActionPlayer
  myTeamId?: string | null
  onChange?: () => void
}

export default function PlayerActionBar({ player, myTeamId, onChange }: PlayerActionBarProps) {
  const navigate = useNavigate()
  const isOwn = player.team_id && myTeamId && player.team_id === myTeamId
  const isFree = !player.team_id

  // 挂牌
  const [listOpen, setListOpen] = useState(false)
  const [listPrice, setListPrice] = useState(String(Math.round((player.market_value || 0) / 10000)))
  const [listLoading, setListLoading] = useState(false)
  const [listError, setListError] = useState<string | null>(null)
  const [listSuccess, setListSuccess] = useState(false)

  // 续约
  const [renewOpen, setRenewOpen] = useState(false)
  const [renewYears, setRenewYears] = useState(2)
  const [renewWage, setRenewWage] = useState(String(Math.round((player.wage || 0) / 10000)))
  const [renewRole, setRenewRole] = useState(player.squad_role || 'rotation')
  const [renewLoading, setRenewLoading] = useState(false)
  const [renewError, setRenewError] = useState<string | null>(null)
  const [renewSuccess, setRenewSuccess] = useState(false)

  // 报价
  const [offerOpen, setOfferOpen] = useState(false)
  const [offerAmount, setOfferAmount] = useState(String(Math.round((player.market_value || 0) / 10000)))
  const [offerLoading, setOfferLoading] = useState(false)
  const [offerError, setOfferError] = useState<string | null>(null)
  const [offerSuccess, setOfferSuccess] = useState(false)

  const handleList = async () => {
    if (!myTeamId) return
    setListLoading(true)
    setListError(null)
    try {
      const res = await api.listPlayer(player.id, { team_id: myTeamId, list_price: Number(listPrice) * 10000 })
      if (res.success && res.data) {
        setListSuccess(true)
        onChange?.()
      } else {
        setListError(res.message || '挂牌失败')
      }
    } catch (err) {
      setListError(err instanceof Error ? err.message : '请求失败')
    } finally {
      setListLoading(false)
    }
  }

  const handleRenew = async () => {
    if (!myTeamId) return
    setRenewLoading(true)
    setRenewError(null)
    try {
      const res = await api.renewContract(player.id, {
        team_id: myTeamId,
        contract_type: (player.contract_type || 'NORMAL') as any,
        years: renewYears,
        wage: Number(renewWage) * 10000,
        squad_role: renewRole as any,
      })
      if (res.success && res.data) {
        setRenewSuccess(true)
        onChange?.()
      } else {
        setRenewError(res.message || '续约失败')
      }
    } catch (err) {
      setRenewError(err instanceof Error ? err.message : '请求失败')
    } finally {
      setRenewLoading(false)
    }
  }

  const handleOffer = async () => {
    if (!myTeamId) return
    setOfferLoading(true)
    setOfferError(null)
    try {
      const res = await api.createTransferOffer({
        player_id: player.id,
        buyer_team_id: myTeamId,
        amount: Number(offerAmount) * 10000,
      })
      if (res.success && res.data) {
        setOfferSuccess(true)
        onChange?.()
      } else {
        setOfferError(res.message || '报价失败')
      }
    } catch (err) {
      setOfferError(err instanceof Error ? err.message : '请求失败')
    } finally {
      setOfferLoading(false)
    }
  }

  const closeList = () => {
    setListOpen(false)
    setListError(null)
    setListSuccess(false)
  }
  const closeRenew = () => {
    setRenewOpen(false)
    setRenewError(null)
    setRenewSuccess(false)
  }
  const closeOffer = () => {
    setOfferOpen(false)
    setOfferError(null)
    setOfferSuccess(false)
  }

  if (!myTeamId) return null

  return (
    <div className="flex items-center gap-2">
      {isOwn && (
        <>
          <Button size="sm" variant="secondary" onClick={() => setRenewOpen(true)}>续约</Button>
          <Button size="sm" onClick={() => setListOpen(true)}>挂牌</Button>
        </>
      )}
      {isFree && (
        <Button size="sm" onClick={() => navigate('/transfer/market?tab=free')}>
          签约
        </Button>
      )}
      {!isOwn && !isFree && (
        <Button size="sm" onClick={() => setOfferOpen(true)}>报价</Button>
      )}

      {/* 挂牌弹窗 */}
      <Modal
        isOpen={listOpen}
        onClose={closeList}
        title={listSuccess ? '挂牌成功' : `挂牌 ${player.name}`}
        size="sm"
        footer={
          listSuccess ? (
            <Button onClick={closeList}>确定</Button>
          ) : (
            <>
              <Button variant="ghost" onClick={closeList}>取消</Button>
              <Button onClick={handleList} isLoading={listLoading} disabled={!listPrice || Number(listPrice) <= 0}>确认挂牌</Button>
            </>
          )
        }
      >
        {listSuccess ? (
          <p className="text-[#1F5F43] font-bold">球员已挂牌，等待报价。</p>
        ) : (
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-[#466353]">系统估值</span>
              <strong className="text-[#173126]">{formatMoney(player.market_value || 0)}</strong>
            </div>
            <div>
              <label className="block text-xs font-bold text-[#466353] mb-1">挂牌价（万）</label>
              <input
                type="number"
                value={listPrice}
                onChange={e => setListPrice(e.target.value)}
                className="w-full px-3 py-2 bg-white/90 border-2 border-[#1F5F43]/30 text-sm outline-none focus:border-[#59C7EE]"
              />
            </div>
            {listError && <div className="p-3 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">{listError}</div>}
          </div>
        )}
      </Modal>

      {/* 续约弹窗 */}
      <Modal
        isOpen={renewOpen}
        onClose={closeRenew}
        title={renewSuccess ? '续约成功' : `续约 ${player.name}`}
        size="sm"
        footer={
          renewSuccess ? (
            <Button onClick={closeRenew}>确定</Button>
          ) : (
            <>
              <Button variant="ghost" onClick={closeRenew}>取消</Button>
              <Button onClick={handleRenew} isLoading={renewLoading} disabled={!renewWage || Number(renewWage) <= 0}>确认续约</Button>
            </>
          )
        }
      >
        {renewSuccess ? (
          <p className="text-[#1F5F43] font-bold">续约完成。</p>
        ) : (
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-[#466353]">建议周薪</span>
              <strong className="text-[#173126]">{formatMoney(player.wage || 0)}</strong>
            </div>
            <div>
              <label className="block text-xs font-bold text-[#466353] mb-1">周薪（万）</label>
              <input
                type="number"
                value={renewWage}
                onChange={e => setRenewWage(e.target.value)}
                className="w-full px-3 py-2 bg-white/90 border-2 border-[#1F5F43]/30 text-sm outline-none focus:border-[#59C7EE]"
              />
            </div>
            <div>
              <label className="block text-xs font-bold text-[#466353] mb-1">年限</label>
              <select
                value={renewYears}
                onChange={e => setRenewYears(Number(e.target.value))}
                className="w-full px-3 py-2 bg-white/90 border-2 border-[#1F5F43]/30 text-sm outline-none focus:border-[#59C7EE]"
              >
                {[1, 2, 3, 4].map(y => <option key={y} value={y}>{y} 年</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-[#466353] mb-1">阵容角色</label>
              <select
                value={renewRole}
                onChange={e => setRenewRole(e.target.value as any)}
                className="w-full px-3 py-2 bg-white/90 border-2 border-[#1F5F43]/30 text-sm outline-none focus:border-[#59C7EE]"
              >
                {SQUAD_ROLE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </div>
            {renewError && <div className="p-3 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">{renewError}</div>}
          </div>
        )}
      </Modal>

      {/* 报价弹窗 */}
      <Modal
        isOpen={offerOpen}
        onClose={closeOffer}
        title={offerSuccess ? '报价已发送' : `报价 ${player.name}`}
        size="sm"
        footer={
          offerSuccess ? (
            <Button onClick={closeOffer}>确定</Button>
          ) : (
            <>
              <Button variant="ghost" onClick={closeOffer}>取消</Button>
              <Button onClick={handleOffer} isLoading={offerLoading} disabled={!offerAmount || Number(offerAmount) <= 0}>确认报价</Button>
            </>
          )
        }
      >
        {offerSuccess ? (
          <p className="text-[#1F5F43] font-bold">报价发送成功。</p>
        ) : (
          <div className="space-y-3">
            <div className="flex justify-between text-sm">
              <span className="text-[#466353]">系统估值</span>
              <strong className="text-[#173126]">{formatMoney(player.market_value || 0)}</strong>
            </div>
            <div>
              <label className="block text-xs font-bold text-[#466353] mb-1">报价金额（万）</label>
              <input
                type="number"
                value={offerAmount}
                onChange={e => setOfferAmount(e.target.value)}
                className="w-full px-3 py-2 bg-white/90 border-2 border-[#1F5F43]/30 text-sm outline-none focus:border-[#59C7EE]"
              />
            </div>
            {offerError && <div className="p-3 bg-[#FF6F59]/10 border-2 border-[#FF6F59]/30 text-[#FF6F59] text-sm">{offerError}</div>}
          </div>
        )}
      </Modal>
    </div>
  )
}
