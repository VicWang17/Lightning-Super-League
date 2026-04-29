import { Link } from 'react-router-dom'
import { 
  Tv,
  Store,
  Users,
  Trophy,
  Sparkles
} from '../../components/ui/pixel-icons'

const mockIncomeItems = [
  { id: '1', type: 'broadcast', label: '转播收入', amount: 35, date: '赛季初', icon: Tv },
  { id: '2', type: 'sponsor', label: '商业赞助', amount: 25, date: '赛季初', icon: Store },
  { id: '3', type: 'matchday', label: '比赛日收入', amount: 3, date: 'Day 5', icon: Users },
  { id: '4', type: 'matchday', label: '比赛日收入', amount: 3, date: 'Day 10', icon: Users },
  { id: '5', type: 'matchday', label: '比赛日收入', amount: 3, date: 'Day 15', icon: Users },
  { id: '6', type: 'cup', label: '杯赛奖金', amount: 6, date: 'Day 8', icon: Trophy },
  { id: '7', type: 'bonus', label: '联赛分红', amount: 10, date: '赛季中', icon: Sparkles },
]

const typeColors: Record<string, string> = {
  broadcast: 'text-blue-400',
  sponsor: 'text-purple-400',
  matchday: 'text-emerald-400',
  cup: 'text-yellow-400',
  bonus: 'text-[#0D7377]',
}

export default function IncomeDetails() {
  const total = mockIncomeItems.reduce((s, i) => s + i.amount, 0)

  return (
    <div className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">财务中心</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">收入明细</p>
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
              tab.id === 'income'
                ? 'border-[#0D7377] text-[#0D7377]'
                : 'border-transparent text-[#4B4B6A] hover:text-[#8B8BA7]'
            )}
          >
            {tab.label}
          </Link>
        ))}
      </div>

      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">收入记录</h3>
          <span className="text-sm font-bold text-emerald-400">合计: {total}万</span>
        </div>
        
        <div className="space-y-2">
          {mockIncomeItems.map((item) => (
            <div key={item.id} className="flex items-center gap-4 p-3 bg-[#0A0A0F] border-2 border-[#2D2D44]">
              <div className="w-10 h-10 bg-[#1E1E2D] border-2 border-[#2D2D44] flex items-center justify-center">
                <item.icon className={clsx('w-5 h-5', typeColors[item.type])} />
              </div>
              <div className="flex-1">
                <p className="text-sm font-medium text-white">{item.label}</p>
                <p className="text-xs text-[#4B4B6A]">{item.date}</p>
              </div>
              <span className="text-sm font-bold text-emerald-400">+{item.amount}万</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

function clsx(...args: (string | false | undefined)[]) {
  return args.filter(Boolean).join(' ')
}
