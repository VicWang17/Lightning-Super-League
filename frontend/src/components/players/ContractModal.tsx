import { useState } from 'react'
import { X } from 'lucide-react'
import { Modal } from '../ui/Modal'
import Button from '../ui/Button'
import { Card } from '../ui/Card'
import type { Player, PlayerContract, ContractPreview, ContractOffer, SquadRole } from '../../types/player'
import { api } from '../../api/client'

interface ContractModalProps {
  player: Player
  teamId: string
  existingContract?: PlayerContract | null
  contractType?: 'NORMAL' | 'ROOKIE' | 'FREE'
  signingFee?: number
  onClose: () => void
  onSuccess: () => void
}

const SQUAD_ROLE_LABELS: Record<SquadRole, string> = {
  key_player: '核心球员',
  first_team: '一线队',
  rotation: '轮换',
  backup: '替补',
  hot_prospect: '希望之星',
  youngster: '青训',
  not_needed: '不需要',
}

const REACTION_COLORS: Record<string, string> = {
  '非常满意': 'text-emerald-400',
  '满意': 'text-emerald-300',
  '平常': 'text-[#8B8BA7]',
  '不满': 'text-amber-400',
  '非常不满': 'text-red-400',
}

export function ContractModal({ player, teamId, existingContract, contractType: propContractType, signingFee, onClose, onSuccess }: ContractModalProps) {
  const isRenewal = !!existingContract
  const isRookie = propContractType === 'ROOKIE'
  const [years, setYears] = useState(isRenewal ? 2 : 2)
  const [wage, setWage] = useState(Math.round(player.wage / 1000) * 1000)
  const [squadRole, setSquadRole] = useState<SquadRole>(isRookie ? 'youngster' : player.squad_role)
  const [preview, setPreview] = useState<ContractPreview | null>(null)
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handlePreview = async () => {
    setLoading(true)
    setError('')
    try {
      const offer: ContractOffer = {
        team_id: teamId,
        contract_type: propContractType || player.contract_type,
        years,
        wage,
        squad_role: squadRole,
      }
      const res = await api.previewContract(player.id, offer)
      if (res.success && res.data) {
        setPreview(res.data as ContractPreview)
      } else {
        setError(res.message || '预览失败')
      }
    } catch (err: any) {
      setError(err.message || '预览失败')
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async () => {
    if (!preview?.can_submit) return
    setSubmitting(true)
    setError('')
    try {
      const offer: ContractOffer = {
        team_id: teamId,
        contract_type: propContractType || player.contract_type,
        years,
        wage,
        squad_role: squadRole,
      }
      const fn = isRenewal ? api.renewContract : api.signContract
      const res = await fn(player.id, offer)
      if (res.success) {
        onSuccess()
        onClose()
      } else {
        setError(res.message || '签约失败')
      }
    } catch (err: any) {
      setError(err.message || '签约失败')
    } finally {
      setSubmitting(false)
    }
  }

  const quickWageButtons = preview ? [
    { label: '70%', value: Math.round(preview.recommended_wage * 0.70) },
    { label: '100%', value: preview.recommended_wage },
    { label: '130%', value: Math.round(preview.recommended_wage * 1.30) },
  ] : []

  return (
    <Modal isOpen={true} onClose={onClose}>
      <div className="w-full max-w-lg">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            {isRenewal ? '续约合同' : isRookie ? '新人合同 (ROOKIE)' : '新签合同'}
          </h2>
          <button onClick={onClose} className="text-[#8B8BA7] hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="space-y-4">
          {/* 球员信息 */}
          <div className="flex items-center gap-3 p-3 bg-[#1E1E2D] rounded">
            <span className="text-lg">👤</span>
            <div>
              <p className="font-medium text-white">{player.name}</p>
              <p className="text-xs text-[#8B8BA7]">{player.position} · OVR {player.ovr}</p>
            </div>
          </div>

          {/* 当前合同 */}
          {existingContract && (
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div className="p-2 bg-[#1E1E2D]">
                <span className="text-[#8B8BA7]">当前工资</span>
                <p className="text-white font-bold">€{(existingContract.wage / 1000).toFixed(0)}K</p>
              </div>
              <div className="p-2 bg-[#1E1E2D]">
                <span className="text-[#8B8BA7]">合同到期</span>
                <p className="text-white font-bold">第 {existingContract.end_season_number} 赛季</p>
              </div>
            </div>
          )}

          {/* 合同参数 */}
          <div className="space-y-3">
            <div>
              <label className="text-sm text-[#8B8BA7] block mb-1">合同年限</label>
              <div className="flex gap-2">
                {[1, 2, 3, 4].map(y => (
                  <button
                    key={y}
                    onClick={() => { setYears(y); setPreview(null) }}
                    className={`px-4 py-2 text-sm border-2 transition-colors ${
                      years === y
                        ? 'border-[#0D7377] text-[#0D7377] bg-[#0D7377]/10'
                        : 'border-[#2D2D44] text-[#8B8BA7] hover:border-[#0D7377]/50'
                    }`}
                  >
                    {y} 年
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-sm text-[#8B8BA7] block mb-1">赛季工资 (€)</label>
              <input
                type="number"
                value={wage}
                onChange={e => { setWage(Number(e.target.value)); setPreview(null) }}
                className="w-full px-3 py-2 bg-[#1E1E2D] border-2 border-[#2D2D44] text-white text-sm focus:border-[#0D7377] outline-none"
                step={1000}
                min={0}
              />
              {preview && (
                <div className="flex gap-2 mt-2">
                  {quickWageButtons.map(btn => (
                    <button
                      key={btn.label}
                      onClick={() => { setWage(btn.value); setPreview(null) }}
                      className="px-2 py-1 text-xs bg-[#2D2D44] text-[#8B8BA7] hover:text-white border border-[#2D2D44] hover:border-[#0D7377]/50 transition-colors"
                    >
                      {btn.label}
                    </button>
                  ))}
                </div>
              )}
            </div>

            <div>
              <label className="text-sm text-[#8B8BA7] block mb-1">阵容角色</label>
              <select
                value={squadRole}
                onChange={e => { setSquadRole(e.target.value as SquadRole); setPreview(null) }}
                className="w-full px-3 py-2 bg-[#1E1E2D] border-2 border-[#2D2D44] text-white text-sm focus:border-[#0D7377] outline-none"
              >
                {Object.entries(SQUAD_ROLE_LABELS).map(([key, label]) => (
                  <option key={key} value={key}>{label}</option>
                ))}
              </select>
            </div>
          </div>

          {/* 预览按钮 */}
          <Button
            onClick={handlePreview}
            disabled={loading}
            className="w-full"
          >
            {loading ? '计算中...' : '预览合同'}
          </Button>

          {/* 预览结果 */}
          {preview && (
            <Card className="bg-[#0D4A4D]/20 border-[#0D7377]/30">
              <div className="space-y-2 text-sm">
                {signingFee !== undefined && signingFee > 0 && (
                  <div className="flex justify-between">
                    <span className="text-[#8B8BA7]">签字费</span>
                    <span className="text-[#0D7377] font-bold">€{(signingFee / 1000).toFixed(0)}K</span>
                  </div>
                )}
                <div className="flex justify-between">
                  <span className="text-[#8B8BA7]">建议工资</span>
                  <span className="text-white">€{(preview.recommended_wage / 1000).toFixed(0)}K</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8B8BA7]">工资比例</span>
                  <span className={preview.wage_ratio >= 1.0 ? 'text-emerald-400' : 'text-amber-400'}>
                    {(preview.wage_ratio * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8B8BA7]">球员反应</span>
                  <span className={REACTION_COLORS[preview.visible_reaction] || 'text-white'}>
                    {preview.visible_reaction}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-[#8B8BA7]">工资帽压力</span>
                  <span className={preview.wage_cap_after_pct > 100 ? 'text-red-400' : 'text-white'}>
                    {preview.wage_cap_after_pct}%
                  </span>
                </div>
                {preview.warnings.length > 0 && (
                  <div className="space-y-1 text-amber-400 pt-2 border-t border-[#2D2D44]">
                    {preview.warnings.map((w, i) => (
                      <p key={i}>{w}</p>
                    ))}
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* 错误 */}
          {error && (
            <p className="text-red-400 text-sm">{error}</p>
          )}

          {/* 提交 */}
          {preview && (
            <Button
              onClick={handleSubmit}
              disabled={submitting || !preview.can_submit}
              className={`w-full ${preview.can_submit ? '' : 'opacity-50 cursor-not-allowed'}`}
            >
              {submitting ? '处理中...' : isRenewal ? '确认续约' : '确认签约'}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  )
}
