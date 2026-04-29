import { Link } from 'react-router-dom'
import { 
  Wallet,
  TrendingUp,
  TrendingDown,
  WarningDiamond,
  Check,
  ChevronRight
} from '../../components/ui/pixel-icons'

const mockFinance = {
  totalIncome: 108,
  totalExpense: 85,
  balance: 23,
  salaryCap: { current: 52, max: 70, pct: 74 },
  healthRating: 'B' as const,
  breakdown: {
    broadcast: 35,
    sponsor: 25,
    matchday: 18,
    cup: 10,
    bonus: 20,
  },
  expenses: {
    salary: 52,
    youth: 15,
    facility: 8,
    transfer: 10,
  }
}

const ratingConfig = {
  A: { color: 'text-emerald-400', bg: 'bg-emerald-500/20', border: 'border-emerald-500/30', label: '优秀' },
  B: { color: 'text-[#0D7377]', bg: 'bg-[#0D4A4D]/30', border: 'border-[#0D7377]/30', label: '健康' },
  C: { color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30', label: '紧张' },
  D: { color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30', label: '危险' },
}

export default function FinanceOverview() {
  const rating = ratingConfig[mockFinance.healthRating]

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">财务中心</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">球队财务总览与预算管理</p>
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
              tab.id === 'overview'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      {/* 核心指标 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Wallet className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">赛季结余</span>
          </div>
          <p className={clsx('text-2xl font-bold stat-number', mockFinance.balance >= 0 ? 'text-emerald-400' : 'text-red-400')}>
            {mockFinance.balance >= 0 ? '+' : ''}{mockFinance.balance}万
          </p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingUp className="w-4 h-4 text-emerald-400" />
            <span className="text-sm text-[#8B8BA7]">总收入</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">{mockFinance.totalIncome}万</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span className="text-sm text-[#8B8BA7]">总支出</span>
          </div>
          <p className="text-2xl font-bold text-white stat-number">{mockFinance.totalExpense}万</p>
        </div>
        <div className="card">
          <div className="flex items-center gap-2 mb-2">
            <Check className="w-4 h-4 text-[#0D7377]" />
            <span className="text-sm text-[#8B8BA7]">财务评级</span>
          </div>
          <div className="flex items-center gap-2">
            <span className={clsx('text-2xl font-bold', rating.color)}>{mockFinance.healthRating}</span>
            <span className={clsx('text-xs px-2 py-0.5 border', rating.color, rating.border, rating.bg)}>
              {rating.label}
            </span>
          </div>
        </div>
      </div>

      {/* 工资帽 */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">工资帽监控</h3>
          <span className={clsx(
            'text-xs px-2 py-0.5 border',
            mockFinance.salaryCap.pct > 90 ? 'text-red-400 border-red-400/30 bg-red-500/10' :
            mockFinance.salaryCap.pct > 70 ? 'text-yellow-400 border-yellow-400/30 bg-yellow-500/10' :
            'text-emerald-400 border-emerald-400/30 bg-emerald-500/10'
          )}>
            {mockFinance.salaryCap.pct}%
          </span>
        </div>
        <div className="pixel-progress-track h-4">
          <div 
            className={clsx(
              'pixel-progress-fill h-full',
              mockFinance.salaryCap.pct > 90 ? 'bg-red-500' :
              mockFinance.salaryCap.pct > 70 ? 'bg-yellow-500' :
              'bg-emerald-500'
            )}
            style={{ width: `${mockFinance.salaryCap.pct}%` }}
          />
        </div>
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-[#4B4B6A]">当前: {mockFinance.salaryCap.current}万</span>
          <span className="text-xs text-[#4B4B6A]">上限: {mockFinance.salaryCap.max}万</span>
        </div>
        {mockFinance.salaryCap.pct > 90 && (
          <div className="flex items-center gap-2 mt-3 p-2 bg-red-500/10 border border-red-500/20">
            <WarningDiamond className="w-4 h-4 text-red-400" />
            <span className="text-xs text-red-400">工资帽即将超限！请考虑出售高薪球员。</span>
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 收入构成 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">收入构成</h3>
          <div className="space-y-3">
            {[
              { label: '转播收入', value: mockFinance.breakdown.broadcast, color: 'bg-blue-500' },
              { label: '商业赞助', value: mockFinance.breakdown.sponsor, color: 'bg-purple-500' },
              { label: '比赛日收入', value: mockFinance.breakdown.matchday, color: 'bg-emerald-500' },
              { label: '杯赛奖金', value: mockFinance.breakdown.cup, color: 'bg-yellow-500' },
              { label: '联赛分红', value: mockFinance.breakdown.bonus, color: 'bg-[#0D7377]' },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-[#E2E2F0]">{item.label}</span>
                  <span className="text-sm text-white">{item.value}万</span>
                </div>
                <div className="pixel-progress-track h-2">
                  <div className={clsx('pixel-progress-fill h-full', item.color)} style={{ width: `${(item.value / mockFinance.totalIncome) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
          <Link to="/finance/income" className="flex items-center gap-1 text-sm text-[#0D7377] hover:text-white transition-colors mt-4">
            查看明细 <ChevronRight className="w-3 h-3" />
          </Link>
        </div>

        {/* 支出构成 */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">支出构成</h3>
          <div className="space-y-3">
            {[
              { label: '球员工资', value: mockFinance.expenses.salary, color: 'bg-red-500' },
              { label: '青训投入', value: mockFinance.expenses.youth, color: 'bg-emerald-500' },
              { label: '设施维护', value: mockFinance.expenses.facility, color: 'bg-blue-500' },
              { label: '转会支出', value: mockFinance.expenses.transfer, color: 'bg-yellow-500' },
            ].map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-[#E2E2F0]">{item.label}</span>
                  <span className="text-sm text-white">{item.value}万</span>
                </div>
                <div className="pixel-progress-track h-2">
                  <div className={clsx('pixel-progress-fill h-full', item.color)} style={{ width: `${(item.value / mockFinance.totalExpense) * 100}%` }} />
                </div>
              </div>
            ))}
          </div>
          <Link to="/finance/expense" className="flex items-center gap-1 text-sm text-[#0D7377] hover:text-white transition-colors mt-4">
            查看明细 <ChevronRight className="w-3 h-3" />
          </Link>
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
