import { useState } from 'react'
import { Link } from 'react-router-dom'
import { 
  Clock,
  Check
} from '../../components/ui/pixel-icons'

export default function BudgetPlanning() {
  const [budget, setBudget] = useState({ transfer: 30, youth: 15, salary: 50, reserve: 5 })
  const total = budget.transfer + budget.youth + budget.salary + budget.reserve
  const isValid = total === 100

  const expectedIncome = 108
  const transferAmount = Math.round(expectedIncome * budget.transfer / 100)
  const youthAmount = Math.round(expectedIncome * budget.youth / 100)
  const salaryAmount = Math.round(expectedIncome * budget.salary / 100)
  const reserveAmount = Math.round(expectedIncome * budget.reserve / 100)

  const applyRecommended = () => {
    setBudget({ transfer: 25, youth: 15, salary: 55, reserve: 5 })
  }

  return (
    <div className="space-y-6 max-w-[800px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">财务中心</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">下赛季预算规划</p>
        </div>
      </div>

      {/* 子导航 */}
      <div className="flex gap-2 border-b-2 border-[#2D2D44]">
        {[
          { id: 'overview', label: '财务总览', to: '/finance/overview' },
          { id: 'budget', label: '预算规划', to: '/finance/budget' },
          { id: 'income', label: '收入明细', to: '/finance/income' },
          { id: 'expense', label: '支出明细', to: '/finance/expense' },
        ].map((tab) => (
          <Link
            key={tab.id}
            to={tab.to}
            className={clsx(
              'px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-0.5',
              tab.id === 'budget'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* 倒计时 */}
      <div className="bg-[#0D4A4D]/20 border-2 border-[#0D7377]/30 p-4">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-[#0D7377]" />
          <span className="text-sm text-[#E2E2F0]">
            预算规划截止: <span className="text-[#0D7377] font-bold">第25天</span> · 未设置将沿用上赛季比例
          </span>
        </div>
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-lg font-semibold">预算分配</h3>
          <button 
            onClick={applyRecommended}
            className="text-xs text-[#0D7377] hover:text-white transition-colors"
          >
            应用建议方案
          </button>
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
              onChange={(e) => setBudget(prev => ({ ...prev, transfer: parseInt(e.target.value) }))}
              className="w-full h-2 bg-[#0A0A0F] border-2 border-[#2D2D44] appearance-none cursor-pointer"
              style={{ accentColor: '#0D7377' }}
            />
            <p className="text-xs text-[#4B4B6A] mt-1">用于拍卖市场出价和自由市场签约</p>
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
              onChange={(e) => setBudget(prev => ({ ...prev, youth: parseInt(e.target.value) }))}
              className="w-full h-2 bg-[#0A0A0F] border-2 border-[#2D2D44] appearance-none cursor-pointer"
            />
            <p className="text-xs text-[#4B4B6A] mt-1">影响青训营刷新人数和潜力概率</p>
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
              onChange={(e) => setBudget(prev => ({ ...prev, salary: parseInt(e.target.value) }))}
              className="w-full h-2 bg-[#0A0A0F] border-2 border-[#2D2D44] appearance-none cursor-pointer"
            />
            <p className="text-xs text-[#4B4B6A] mt-1">覆盖球员工资和续约支出</p>
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
              onChange={(e) => setBudget(prev => ({ ...prev, reserve: parseInt(e.target.value) }))}
              className="w-full h-2 bg-[#0A0A0F] border-2 border-[#2D2D44] appearance-none cursor-pointer"
            />
            <p className="text-xs text-[#4B4B6A] mt-1">意外支出和追加转会</p>
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

        <button 
          disabled={!isValid}
          className="btn-primary w-full mt-6 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Check className="w-4 h-4" />
          确认预算分配
        </button>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
