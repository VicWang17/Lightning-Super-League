import { useParams, Link } from 'react-router-dom'
import { 
  Users, ChevronLeft, Shield, Target, Zap, Trophy, 
  MapPin, Calendar, TrendingUp, ChevronRight 
} from '../../components/ui/pixel-icons'
import { Card } from '../../components/ui/Card'

// Mock team data
const MOCK_TEAM = {
 id: '1',
 name: '东方巨龙',
 short_name: '巨龙',
 logo_url: null,
 stadium: '巨龙体育场',
 city: '上海',
 founded_year: 2020,
 reputation: 1800,
 overall_rating: 72,
 attack: 74,
 midfield: 70,
 defense: 71,
 league_position: 3,
 league_name: '东区超级联赛',
 league_id: '1',
 user: {
 id: '1',
 nickname: '龙傲天',
 level: 15
 },
 stats: {
 matches_played: 11,
 wins: 8,
 draws: 0,
 losses: 3,
 goals_for: 26,
 goals_against: 14,
 points: 24
 },
 finances: {
 balance: 25000000,
 weekly_wages: 125000,
 stadium_capacity: 45000,
 ticket_price: 35
 }
}

// Mock players
const MOCK_PLAYERS = [
 { id: '1', name: '王强', position: 'GK', overall: 68, age: 28, nationality: '中国' },
 { id: '2', name: '李伟', position: 'CB', overall: 71, age: 26, nationality: '中国' },
 { id: '3', name: '张鹏', position: 'CB', overall: 70, age: 25, nationality: '中国' },
 { id: '4', name: '刘洋', position: 'LB', overall: 69, age: 24, nationality: '中国' },
 { id: '5', name: '陈明', position: 'RB', overall: 68, age: 27, nationality: '中国' },
 { id: '6', name: '周杰', position: 'CDM', overall: 72, age: 29, nationality: '中国' },
 { id: '7', name: '吴涛', position: 'CM', overall: 73, age: 26, nationality: '中国' },
 { id: '8', name: '郑华', position: 'CAM', overall: 74, age: 25, nationality: '中国' },
 { id: '9', name: '孙亮', position: 'LW', overall: 75, age: 24, nationality: '中国' },
 { id: '10', name: '钱进', position: 'ST', overall: 76, age: 27, nationality: '中国' },
 { id: '11', name: '赵飞', position: 'RW', overall: 74, age: 25, nationality: '中国' },
]

// Position colors
const POSITION_COLORS: Record<string, string> = {
 GK: 'bg-amber-500 text-black',
 DF: 'bg-blue-500 text-white',
 MF: 'bg-emerald-500 text-white',
 FW: 'bg-red-500 text-white',
}

function getPositionGroup(position: string): string {
 if (position === 'GK') return 'GK'
 if (['CB', 'LB', 'RB', 'LWB', 'RWB'].includes(position)) return 'DF'
 if (['CDM', 'CM', 'CAM', 'LM', 'RM'].includes(position)) return 'MF'
 return 'FW'
}

function TeamDetail() {
 const { id: _id } = useParams<{ id: string }>()
 const team = MOCK_TEAM // In real app, fetch by _id

 return (
 <div className="max-w-[1200px]">
 {/* 返回按钮 */}
 <Link 
 to="/leagues"
 className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
 >
 <ChevronLeft className="w-4 h-4" />
 返回联赛
 </Link>

 {/* 球队信息头部 */}
 <Card className="mb-6 bg-[#0D4A4D]/30 border-2 border-[#2D2D44] hover:-translate-y-1 hover:shadow-pixel transition-all">
 <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
 <div className="w-24 h-24 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center text-5xl shadow-pixel">
 🐉
 </div>
 <div className="flex-1">
 <div className="flex items-center gap-3 mb-2">
 <h1 className="text-3xl font-bold text-white">{team.name}</h1>
 <span className="text-lg text-[#8B8BA7]">({team.short_name})</span>
 </div>
 <div className="flex flex-wrap items-center gap-4 text-sm text-[#8B8BA7]">
 <div className="flex items-center gap-1.5">
 <MapPin className="w-4 h-4" />
 {team.city}
 </div>
 <div className="flex items-center gap-1.5">
 <Calendar className="w-4 h-4" />
 成立于 {team.founded_year}
 </div>
 <div className="flex items-center gap-1.5">
 <Trophy className="w-4 h-4" />
 声望 {team.reputation}
 </div>
 </div>
 <div className="mt-3">
 <Link 
 to={`/leagues/${team.league_id}`}
 className="inline-flex items-center gap-1.5 text-sm text-[#0D7377] hover:text-white transition-colors"
 >
 <Shield className="w-4 h-4" />
 {team.league_name} · 排名第 {team.league_position}
 <ChevronRight className="w-3 h-3" />
 </Link>
 </div>
 </div>
 <div className="flex items-center gap-4">
 <div className="text-center">
 <div className="text-3xl font-bold stat-number pixel-number text-[#0D7377]">{team.overall_rating}</div>
 <div className="text-xs text-[#8B8BA7]">总评</div>
 </div>
 </div>
 </div>
 </Card>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* 左侧 - 能力值和统计 */}
 <div className="space-y-6">
 {/* 能力值 */}
 <Card hover>
 <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
 <Zap className="w-5 h-5 text-[#0D7377]" />
 球队能力
 </h3>
 <div className="space-y-4">
 <div>
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2">
 <Target className="w-4 h-4 text-red-400" />
 <span className="text-sm text-[#8B8BA7]">进攻</span>
 </div>
 <span className="font-bold stat-number pixel-number">{team.attack}</span>
 </div>
 <div className="pixel-progress-track">
    <div
    className="pixel-progress-fill bg-red-500"
    style={{ width: `${team.attack}%` }}
    />
    </div>
 </div>
 <div>
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2">
 <Zap className="w-4 h-4 text-[#0D7377]" />
 <span className="text-sm text-[#8B8BA7]">中场</span>
 </div>
 <span className="font-bold stat-number pixel-number">{team.midfield}</span>
 </div>
 <div className="pixel-progress-track">
    <div
    className="pixel-progress-fill bg-[#0D7377]"
    style={{ width: `${team.midfield}%` }}
    />
    </div>
 </div>
 <div>
 <div className="flex items-center justify-between mb-2">
 <div className="flex items-center gap-2">
 <Shield className="w-4 h-4 text-emerald-400" />
 <span className="text-sm text-[#8B8BA7]">防守</span>
 </div>
 <span className="font-bold stat-number pixel-number">{team.defense}</span>
 </div>
 <div className="pixel-progress-track">
    <div
    className="pixel-progress-fill bg-emerald-500"
    style={{ width: `${team.defense}%` }}
    />
    </div>
 </div>
 </div>
 </Card>

 {/* 赛季统计 */}
 <Card hover>
 <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
 <TrendingUp className="w-5 h-5 text-[#0D7377]" />
 本赛季统计
 </h3>
 <div className="grid grid-cols-2 gap-4">
 <div className="text-center p-3 bg-[#1E1E2D]">
 <div className="text-2xl font-bold stat-number pixel-number text-white">{team.stats.matches_played}</div>
 <div className="text-xs text-[#8B8BA7]">场次</div>
 </div>
 <div className="text-center p-3 bg-[#1E1E2D]">
 <div className="text-2xl font-bold stat-number pixel-number text-emerald-400">{team.stats.wins}</div>
 <div className="text-xs text-[#8B8BA7]">胜</div>
 </div>
 <div className="text-center p-3 bg-[#1E1E2D]">
 <div className="text-2xl font-bold stat-number pixel-number text-[#8B8BA7]">{team.stats.draws}</div>
 <div className="text-xs text-[#8B8BA7]">平</div>
 </div>
 <div className="text-center p-3 bg-[#1E1E2D]">
 <div className="text-2xl font-bold stat-number pixel-number text-red-400">{team.stats.losses}</div>
 <div className="text-xs text-[#8B8BA7]">负</div>
 </div>
 </div>
 <div className="mt-4 pt-4 border-t-2 border-[#2D2D44]">
 <div className="flex items-center justify-between">
 <span className="text-sm text-[#8B8BA7]">进球/失球</span>
 <span className="font-bold stat-number pixel-number">{team.stats.goals_for} / {team.stats.goals_against}</span>
 </div>
 <div className="flex items-center justify-between mt-2">
 <span className="text-sm text-[#8B8BA7]">积分</span>
 <span className="font-bold stat-number pixel-number text-[#0D7377]">{team.stats.points}</span>
 </div>
 </div>
 </Card>

 {/* 财务信息 */}
 <Card hover>
 <h3 className="text-lg font-semibold mb-4">财务状况</h3>
 <div className="space-y-3">
 <div className="flex items-center justify-between">
 <span className="text-sm text-[#8B8BA7]">资金余额</span>
 <span className="font-bold stat-number pixel-number text-emerald-400">
 €{(team.finances.balance / 1000000).toFixed(1)}M
 </span>
 </div>
 <div className="flex items-center justify-between">
 <span className="text-sm text-[#8B8BA7]">周薪支出</span>
 <span className="font-bold stat-number pixel-number text-red-400">
 €{(team.finances.weekly_wages / 1000).toFixed(0)}K
 </span>
 </div>
 <div className="flex items-center justify-between">
 <span className="text-sm text-[#8B8BA7]">球场容量</span>
 <span className="font-bold stat-number pixel-number">{team.finances.stadium_capacity.toLocaleString()}</span>
 </div>
 </div>
 </Card>
 </div>

 {/* 右侧 - 球员列表 */}
 <div className="lg:col-span-2">
 <Card hover>
 <div className="flex items-center justify-between mb-4">
 <h3 className="text-lg font-semibold flex items-center gap-2">
 <Users className="w-5 h-5 text-[#0D7377]" />
 球队阵容
 </h3>
 <span className="text-sm text-[#8B8BA7]">{MOCK_PLAYERS.length} 名球员</span>
 </div>
 
 <div className="overflow-x-auto">
 <table className="w-full">
 <thead>
 <tr className="text-left text-xs text-[#8B8BA7] border-b border-[#2D2D44]">
 <th className="py-3 px-2 font-medium">位置</th>
 <th className="py-3 px-2 font-medium">姓名</th>
 <th className="py-3 px-2 font-medium text-center">年龄</th>
 <th className="py-3 px-2 font-medium text-center">国籍</th>
 <th className="py-3 px-2 font-medium text-center">能力</th>
 </tr>
 </thead>
 <tbody>
 {MOCK_PLAYERS.map(player => (
 <tr key={player.id} className="border-b border-[#2D2D44] hover:bg-[#1E1E2D]/50 transition-colors">
 <td className="py-3 px-2">
 <span className={`inline-flex items-center justify-center w-8 h-8 text-xs font-bold ${POSITION_COLORS[getPositionGroup(player.position)]}`}>
 {player.position}
 </span>
 </td>
 <td className="py-3 px-2">
 <Link 
 to={`/players/${player.id}`}
 className="font-medium text-white hover:text-[#0D7377] transition-colors"
 >
 {player.name}
 </Link>
 </td>
 <td className="py-3 px-2 text-center stat-number text-[#8B8BA7]">{player.age}</td>
 <td className="py-3 px-2 text-center text-sm text-[#8B8BA7]">{player.nationality}</td>
 <td className="py-3 px-2 text-center">
 <span className={`font-bold stat-number pixel-number ${
 player.overall >= 75 ? 'text-emerald-400' :
 player.overall >= 70 ? 'text-[#0D7377]' :
 'text-[#8B8BA7]'
 }`}>
 {player.overall}
 </span>
 </td>
 </tr>
 ))}
 </tbody>
 </table>
 </div>
 </Card>
 </div>
 </div>
 </div>
 )
}

export default TeamDetail
