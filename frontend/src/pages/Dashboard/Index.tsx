import { 
  TrendingUp, 
  TrendingDown, 
  Minus,
  Calendar,
  ChevronRight,
  Target,
  Shield,
  Zap,
  Trophy,
  Users
} from 'lucide-react'

// 数据卡片组件
function StatCard({ 
  label, 
  value, 
  subtext, 
  trend,
  trendValue 
}: { 
  label: string
  value: string
  subtext: string
  trend?: 'up' | 'down' | 'neutral'
  trendValue?: string
}) {
  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-[#4B4B6A]'

  return (
    <div className="card card-hover">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-[#8B8BA7] mb-1">{label}</p>
          <p className="text-3xl font-bold stat-number text-white">{value}</p>
        </div>
        {trend && (
          <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
            <TrendIcon className="w-3 h-3" />
            <span>{trendValue}</span>
          </div>
        )}
      </div>
      <p className="text-xs text-[#4B4B6A] mt-2">{subtext}</p>
    </div>
  )
}

// 快捷操作卡片
function QuickAction({ icon: Icon, label, desc }: { icon: any, label: string, desc: string }) {
  return (
    <button className="flex items-center gap-4 p-4 rounded-xl bg-[#12121A] border border-[#2D2D44] hover:border-[#0D7377]/50 transition-all duration-200 group text-left w-full">
      <div className="w-10 h-10 rounded-lg bg-[#0D4A4D]/40 border border-[#0D7377]/30 flex items-center justify-center flex-shrink-0">
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-white group-hover:text-[#0D7377] transition-colors">{label}</p>
        <p className="text-xs text-[#4B4B6A] truncate">{desc}</p>
      </div>
      <ChevronRight className="w-4 h-4 text-[#4B4B6A] group-hover:text-white transition-colors" />
    </button>
  )
}

// 比赛记录
function MatchResult({ opponent, result, score, date }: { opponent: string, result: 'W' | 'D' | 'L', score: string, date: string }) {
  const resultConfig = {
    W: { bg: 'bg-emerald-500/20', text: 'text-emerald-400', label: '胜' },
    D: { bg: 'bg-[#2D2D44]', text: 'text-[#8B8BA7]', label: '平' },
    L: { bg: 'bg-red-500/20', text: 'text-red-400', label: '负' },
  }
  const config = resultConfig[result]

  return (
    <div className="flex items-center gap-4 py-3 border-b border-[#2D2D44] last:border-0">
      <div className={`w-8 h-8 rounded-lg ${config.bg} flex items-center justify-center text-xs font-bold ${config.text}`}>
        {config.label}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{opponent}</p>
        <p className="text-xs text-[#4B4B6A]">{date}</p>
      </div>
      <div className="text-right">
        <p className="text-sm font-bold stat-number">{score}</p>
      </div>
    </div>
  )
}

// 动态项
function ActivityItem({ icon: Icon, text, time }: { icon: any, text: string, time: string }) {
  return (
    <div className="flex items-start gap-3 py-3 border-b border-[#2D2D44] last:border-0">
      <div className="w-8 h-8 rounded-lg bg-[#1E1E2D] flex items-center justify-center flex-shrink-0">
        <Icon className="w-4 h-4 text-[#0D7377]" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm text-[#E2E2F0]">{text}</p>
        <p className="text-xs text-[#4B4B6A] mt-0.5">{time}</p>
      </div>
    </div>
  )
}

function Dashboard() {
  return (
    <div className="space-y-6 max-w-[1600px]">
      {/* 欢迎区域 */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">欢迎回来，经理</h1>
          <p className="text-sm text-[#8B8BA7] mt-1">以下是您球队的最新概况</p>
        </div>
        <button className="btn-primary flex items-center gap-2">
          <Calendar className="w-4 h-4" />
          下一场比赛
        </button>
      </div>

      {/* 数据概览 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard 
          label="联赛排名" 
          value="#3" 
          subtext="顶级联赛 · 积分 24"
          trend="up"
          trendValue="↑ 2"
        />
        <StatCard 
          label="本赛季战绩" 
          value="8-2-1" 
          subtext="胜 - 平 - 负"
          trend="up"
          trendValue="80%"
        />
        <StatCard 
          label="球队总评" 
          value="84.5" 
          subtext="进攻 86 · 防守 83"
          trend="neutral"
          trendValue="-"
        />
        <StatCard 
          label="球队市值" 
          value="€85M" 
          subtext="较上月增长 12%"
          trend="up"
          trendValue="+€9M"
        />
      </div>

      {/* 主内容区 */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* 左侧 - 球队概览 */}
        <div className="lg:col-span-2 space-y-6">
          {/* 球队信息卡 */}
          <div className="card">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-lg font-semibold">我的球队</h3>
              <button className="text-sm text-[#0D7377] hover:text-white transition-colors">查看详情 →</button>
            </div>
            
            <div className="flex items-center gap-6 pb-6 border-b border-[#2D2D44]">
              <div className="w-20 h-20 rounded-2xl bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center">
                <span className="text-3xl">⚡</span>
              </div>
              <div className="flex-1">
                <h2 className="text-2xl font-bold">雷霆FC</h2>
                <p className="text-sm text-[#8B8BA7] mt-1">成立于 2024 · 主场: 雷霆球场</p>
                <div className="flex items-center gap-4 mt-3">
                  <div className="flex items-center gap-1.5 text-sm">
                    <Target className="w-4 h-4 text-red-400" />
                    <span>进攻 86</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Shield className="w-4 h-4 text-[#0D7377]" />
                    <span>防守 83</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-sm">
                    <Zap className="w-4 h-4 text-emerald-400" />
                    <span>体能 85</span>
                  </div>
                </div>
              </div>
            </div>

            {/* 能力条 */}
            <div className="grid grid-cols-3 gap-6 pt-6">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">进攻</span>
                  <span className="text-sm font-medium stat-number">86</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] rounded-full overflow-hidden">
                  <div className="h-full bg-red-500 rounded-full" style={{ width: '86%' }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">中场</span>
                  <span className="text-sm font-medium stat-number">84</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] rounded-full overflow-hidden">
                  <div className="h-full bg-[#0D7377] rounded-full" style={{ width: '84%' }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-[#8B8BA7]">防守</span>
                  <span className="text-sm font-medium stat-number">83</span>
                </div>
                <div className="h-1.5 bg-[#1E1E2D] rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-500 rounded-full" style={{ width: '83%' }} />
                </div>
              </div>
            </div>
          </div>

          {/* 最近比赛 */}
          <div className="card">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">最近比赛</h3>
              <button className="text-sm text-[#8B8BA7] hover:text-white transition-colors">查看全部</button>
            </div>
            <div>
              <MatchResult opponent="vs 曼城" result="W" score="3:1" date="2天前" />
              <MatchResult opponent="vs 利物浦" result="W" score="2:0" date="5天前" />
              <MatchResult opponent="vs 阿森纳" result="D" score="1:1" date="1周前" />
              <MatchResult opponent="vs 切尔西" result="W" score="4:2" date="1周前" />
              <MatchResult opponent="vs 曼联" result="L" score="0:1" date="2周前" />
            </div>
          </div>
        </div>

        {/* 右侧 - 快捷操作和动态 */}
        <div className="space-y-6">
          {/* 快捷操作 */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">快捷操作</h3>
            <div className="space-y-3">
              <QuickAction 
                icon={Target} 
                label="设置战术" 
                desc="调整阵型和球员指令"
              />
              <QuickAction 
                icon={Users} 
                label="阵容调整" 
                desc="首发11人和替补名单"
              />
              <QuickAction 
                icon={Trophy} 
                label="查看排名" 
                desc="联赛积分榜和射手榜"
              />
              <QuickAction 
                icon={Calendar} 
                label="赛程安排" 
                desc=" upcoming matches"
              />
            </div>
          </div>

          {/* 最新动态 */}
          <div className="card">
            <h3 className="text-lg font-semibold mb-4">最新动态</h3>
            <div>
              <ActivityItem 
                icon={Trophy}
                text="球队在主场 3:1 战胜曼城"
                time="2小时前"
              />
              <ActivityItem 
                icon={Users}
                text="年轻球员 张昊 能力值 +3"
                time="5小时前"
              />
              <ActivityItem 
                icon={Calendar}
                text="下轮对阵巴萨的门票已售罄"
                time="1天前"
              />
              <ActivityItem 
                icon={TrendingUp}
                text="球队市值突破 8500万"
                time="2天前"
              />
            </div>
          </div>

          {/* 下场比赛预告 */}
          <div className="card bg-gradient-to-br from-[#0D4A4D]/30 to-[#12121A]">
            <div className="flex items-center gap-2 mb-4">
              <Calendar className="w-4 h-4 text-[#0D7377]" />
              <span className="text-sm text-[#8B8BA7]">下场比赛</span>
            </div>
            <div className="flex items-center justify-between">
              <div className="text-center">
                <div className="w-12 h-12 rounded-xl bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
                  <span className="text-xl">⚡</span>
                </div>
                <p className="text-xs text-[#8B8BA7]">雷霆FC</p>
              </div>
              <div className="text-center px-4">
                <p className="text-2xl font-bold stat-number text-[#0D7377]">VS</p>
                <p className="text-xs text-[#4B4B6A] mt-1">2天后</p>
              </div>
              <div className="text-center">
                <div className="w-12 h-12 rounded-xl bg-[#1E1E2D] border border-[#2D2D44] flex items-center justify-center mx-auto mb-2">
                  <span className="text-xl">🔴</span>
                </div>
                <p className="text-xs text-[#8B8BA7]">巴萨</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
