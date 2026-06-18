import { useState, useEffect } from 'react'
import { 
  Check,
  Loader,
  Store,
  TrendingUp,
  Shield
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import { PageHeader } from '../../components/ui/PageHeader'
import { FinanceTabs } from '../../components/finance/FinanceTabs'

type BudgetPolicy = 'balanced' | 'youth_focus' | 'transfer_push' | 'wage_control' | 'custom'

const POLICY_PRESETS: Record<BudgetPolicy, { transfer: number; youth: number; salary: number; reserve: number; label: string }> = {
  balanced: { transfer: 25, youth: 15, salary: 50, reserve: 10, label: '均衡' },
  youth_focus: { transfer: 20, youth: 25, salary: 45, reserve: 10, label: '青训侧重' },
  transfer_push: { transfer: 40, youth: 10, salary: 45, reserve: 5, label: '转会侧重' },
  wage_control: { transfer: 20, youth: 15, salary: 55, reserve: 10, label: '工资控制' },
  custom: { transfer: 25, youth: 15, salary: 50, reserve: 10, label: '自定义' },
}

function formatWan(value: number): string {
  return (value / 10000).toFixed(0)
}

export default function BudgetPlanning() {
  const [budget, setBudget] = useState({ transfer: 25, youth: 15, salary: 50, reserve: 10 })
  const [policy, setPolicy] = useState<BudgetPolicy>('balanced')
  const [expectedIncome, setExpectedIncome] = useState(0)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMsg, setSuccessMsg] = useState<string | null>(null)
  const [locked, setLocked] = useState(false)
  const [teamId, setTeamId] = useState<string | null>(null)
  const [seasonId, setSeasonId] = useState<string | null>(null)
  const [sponsorOptions, setSponsorOptions] = useState<any[]>([])
  const [currentSponsor, setCurrentSponsor] = useState<any>(null)
  const [signingSponsor, setSigningSponsor] = useState(false)

  useEffect(() => {
    let cancelled = false
    async function load() {
      try {
        setLoading(true)
        const teamRes = await api.get<{ id: string; current_season_id?: string }>('/teams/my-team')
        if (!teamRes.success || !teamRes.data?.id) {
          setError('未找到球队信息')
          return
        }
        const tid = teamRes.data.id
        const sid = teamRes.data.current_season_id || ''
        setTeamId(tid)
        setSeasonId(sid)

        // 加载财务概览（获取预算计划和赞助商）
        const financeRes = await api.getFinanceOverview(tid)
        if (!cancelled && financeRes.success && financeRes.data) {
          const total = financeRes.data.locked_budget_total || financeRes.data.current_balance
          setExpectedIncome(total)
          if (financeRes.data.budget_plan) {
            const p = financeRes.data.budget_plan
            setBudget({ transfer: p.transfer_pct, youth: p.youth_pct, salary: p.wage_pct, reserve: p.reserve_pct })
            setPolicy(p.policy as BudgetPolicy)
            setLocked(!!p.locked_at)
          }
          if (financeRes.data.sponsor_contract) {
            setCurrentSponsor(financeRes.data.sponsor_contract)
          }
        }

        // 加载赞助商选项
        if (sid) {
          const sponsorRes = await api.getSponsorOptions(tid, sid)
          if (!cancelled && sponsorRes.success && sponsorRes.data) {
            setSponsorOptions(sponsorRes.data)
          }
        }
      } catch (e: any) {
        if (!cancelled) setError(e.message || '加载失败')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const total = budget.transfer + budget.youth + budget.salary + budget.reserve
  const isValid = total === 100

  const transferAmount = Math.round(expectedIncome * budget.transfer / 100 / 10000)
  const youthAmount = Math.round(expectedIncome * budget.youth / 100 / 10000)
  const salaryAmount = Math.round(expectedIncome * budget.salary / 100 / 10000)
  const reserveAmount = Math.round(expectedIncome * budget.reserve / 100 / 10000)

  const applyPolicy = (p: BudgetPolicy) => {
    setPolicy(p)
    if (p !== 'custom') {
      const preset = POLICY_PRESETS[p]
      setBudget({ transfer: preset.transfer, youth: preset.youth, salary: preset.salary, reserve: preset.reserve })
    }
  }

  const handleSave = async () => {
    if (!teamId || !seasonId || !isValid) return
    try {
      setSaving(true)
      setSuccessMsg(null)
      const res = await api.confirmBudgetPlan(
        teamId, seasonId, policy,
        budget.transfer, budget.youth, budget.salary, budget.reserve
      )
      if (res.success) {
        setSuccessMsg('预算计划已保存')
      }
    } catch (e: any) {
      setError(e.message || '保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleSignSponsor = async (sponsorPolicy: string) => {
    if (!teamId || !seasonId) return
    try {
      setSigningSponsor(true)
      const res = await api.signSponsorContract(teamId, seasonId, sponsorPolicy)
      if (res.success && res.data) {
        setCurrentSponsor(res.data)
        setSuccessMsg('赞助合同已签署')
      }
    } catch (e: any) {
      setError(e.message || '签署失败')
    } finally {
      setSigningSponsor(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader className="w-8 h-8 text-[#0D7377] animate-spin" />
      </div>
    )
  }

  if (error && !teamId) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-[800px]">
      <PageHeader icon={Store} title="预算规划" subtitle="下赛季预算规划与赞助商选择" />

      <FinanceTabs />

      {successMsg && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 text-sm">
          {successMsg}
        </div>
      )}

      {/* 预算规划 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">预算分配</h3>
          <span className="text-sm text-[#8B8BA7]">
            预计总额: {formatWan(expectedIncome)}万
          </span>
        </div>

        {locked && (
          <div className="mb-4 p-3 bg-yellow-500/10 border border-yellow-500/30 text-yellow-400 text-sm flex items-center gap-2">
            <Shield className="w-4 h-4" />
            预算计划已锁定，无法修改
          </div>
        )}

        {/* 策略选择 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2 mb-6">
          {(Object.keys(POLICY_PRESETS) as BudgetPolicy[]).filter(p => p !== 'custom').map((p) => (
            <button
              key={p}
              onClick={() => !locked && applyPolicy(p)}
              disabled={locked}
              className={clsx(
                'px-3 py-2 text-xs font-medium border-2 transition-colors',
                policy === p
                  ? 'border-[#0D7377] bg-[#0D4A4D]/30 text-[#0D7377]'
                  : 'border-[#2D2D44] text-[#8B8BA7] hover:border-[#4B4B6A]'
              )}
            >
              {POLICY_PRESETS[p].label}
            </button>
          ))}
        </div>

        <div className="space-y-6">
          {/* 转会预算 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-[#E2E2F0]">转会预算</label>
              <span className="text-sm font-bold text-[#0D7377]">{budget.transfer}% ({transferAmount}万)</span>
            </div>
            <input
              type="range"
              min="0"
              max="60"
              value={budget.transfer}
              disabled={locked}
              onChange={(e) => { setPolicy('custom'); setBudget(prev => ({ ...prev, transfer: parseInt(e.target.value) })) }}
              className="w-full h-2 bg-[#0A0A0F] border-2 border-[#2D2D44] appearance-none cursor-pointer disabled:opacity-50"
              style={{ accentColor: '#0D7377' }}
            />
          </div>

          {/* 青训投入 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-[#E2E2F0]">青训投入</label>
              <span className="text-sm font-bold text-[#0D7377]">{budget.youth}% ({youthAmount}万)</span>
            </div>
            <input
              type="range"
              min="5"
              max="25"
              value={budget.youth}
              disabled={locked}
              onChange={(e) => { setPolicy('custom'); setBudget(prev => ({ ...prev, youth: parseInt(e.target.value) })) }}
              className="w-full h-2 bg-[#0A0A0F] border-2 border-[#2D2D44] appearance-none cursor-pointer disabled:opacity-50"
            />
          </div>

          {/* 工资预留 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-[#E2E2F0]">工资预留</label>
              <span className="text-sm font-bold text-[#0D7377]">{budget.salary}% ({salaryAmount}万)</span>
            </div>
            <input
              type="range"
              min="40"
              max="80"
              value={budget.salary}
              disabled={locked}
              onChange={(e) => { setPolicy('custom'); setBudget(prev => ({ ...prev, salary: parseInt(e.target.value) })) }}
              className="w-full h-2 bg-[#0A0A0F] border-2 border-[#2D2D44] appearance-none cursor-pointer disabled:opacity-50"
            />
          </div>

          {/* 应急储备 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-[#E2E2F0]">应急储备</label>
              <span className="text-sm font-bold text-[#0D7377]">{budget.reserve}% ({reserveAmount}万)</span>
            </div>
            <input
              type="range"
              min="0"
              max="20"
              value={budget.reserve}
              disabled={locked}
              onChange={(e) => { setPolicy('custom'); setBudget(prev => ({ ...prev, reserve: parseInt(e.target.value) })) }}
              className="w-full h-2 bg-[#0A0A0F] border-2 border-[#2D2D44] appearance-none cursor-pointer disabled:opacity-50"
            />
          </div>
        </div>

        {/* 总计 */}
        <div className="mt-6 pt-4 border-t-2 border-[#2D2D44]">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-[#E2E2F0]">总计</span>
            <span className={clsx('text-xl font-bold stat-number', isValid ? 'text-emerald-400' : 'text-red-400')}>
              {total}%
            </span>
          </div>
          <div className="pixel-progress-track h-3">
            <div 
              className={clsx('pixel-progress-fill h-full', isValid ? 'bg-emerald-500' : 'bg-red-500')}
              style={{ width: `${Math.min(total, 100)}%` }}
            />
          </div>
          {!isValid && (
            <p className="text-xs text-red-400 mt-2">分配总和必须等于100%</p>
          )}
        </div>

        {!locked && (
          <button 
            onClick={handleSave}
            disabled={!isValid || saving}
            className="btn-primary w-full mt-6 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {saving ? <Loader className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
            {saving ? '保存中...' : '确认预算分配'}
          </button>
        )}
      </div>

      {/* 赞助商选择 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">商业赞助</h3>
          {currentSponsor && (
            <span className={clsx(
              'text-xs px-2 py-0.5 border',
              currentSponsor.policy === 'stable'
                ? 'text-blue-400 border-blue-400/30 bg-blue-500/10'
                : 'text-purple-400 border-purple-400/30 bg-purple-500/10'
            )}>
              {currentSponsor.policy === 'stable' ? '稳定型' : '绩效型'} · 已签署
            </span>
          )}
        </div>

        {currentSponsor ? (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm text-[#8B8BA7]">基础收入</span>
              <span className="text-sm text-white">{formatWan(currentSponsor.base_amount)}万/赛季</span>
            </div>
            {currentSponsor.win_bonus > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">胜场奖金</span>
                <span className="text-sm text-emerald-400">+{formatWan(currentSponsor.win_bonus)}万</span>
              </div>
            )}
            {currentSponsor.max_bonus > 0 && (
              <div className="flex items-center justify-between">
                <span className="text-sm text-[#8B8BA7]">奖金上限</span>
                <span className="text-sm text-yellow-400">{formatWan(currentSponsor.max_bonus)}万</span>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-3">
            {sponsorOptions.length === 0 && (
              <p className="text-sm text-[#4B4B6A]">加载赞助商选项中...</p>
            )}
            {sponsorOptions.map((opt) => (
              <div key={opt.policy} className="p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <Store className="w-4 h-4 text-[#0D7377]" />
                    <span className="text-sm font-medium text-white">{opt.label}</span>
                  </div>
                  <span className="text-sm font-bold text-[#0D7377]">{formatWan(opt.base_amount)}万</span>
                </div>
                <p className="text-xs text-[#4B4B6A] mb-3">{opt.description}</p>
                <button
                  onClick={() => handleSignSponsor(opt.policy)}
                  disabled={signingSponsor}
                  className="btn-primary w-full text-xs py-1.5 flex items-center justify-center gap-1 disabled:opacity-50"
                >
                  {signingSponsor ? <Loader className="w-3 h-3 animate-spin" /> : <TrendingUp className="w-3 h-3" />}
                  选择此赞助商
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
