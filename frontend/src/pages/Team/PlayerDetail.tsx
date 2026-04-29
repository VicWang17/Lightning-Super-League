import { useParams, Link } from 'react-router-dom'
import { 
 ChevronLeft, 
 User,
 Calendar,
 Ruler,
 Weight,
 Footprints,
 MapPin,
 TrendingUp,
 Award,
 Shield,
 Target,
 Zap,
 Clock,
 ChevronRight
} from 'lucide-react'
import { Card } from '../../components/ui/Card'
import { getPositionColor } from '../../types/player'

// Mock player data
const MOCK_PLAYER = {
 id: '1',
 first_name: '钱',
 last_name: '进',
 display_name: '钱进',
 nationality: '中国',
 birth_date: '1997-05-15',
 age: 27,
 height: 185,
 weight: 78,
 preferred_foot: 'right' as const,
 primary_position: 'ST' as const,
 secondary_position: 'CF' as const,
 
 // Abilities
 shooting: 78,
 finishing: 80,
 long_shots: 72,
 passing: 65,
 vision: 68,
 crossing: 60,
 dribbling: 74,
 ball_control: 76,
 defending: 35,
 tackling: 32,
 marking: 30,
 pace: 76,
 acceleration: 78,
 strength: 79,
 stamina: 75,
 diving: 20,
 handling: 20,
 kicking: 25,
 reflexes: 30,
 positioning: 82,
 aggression: 70,
 composure: 77,
 work_rate: 76,
 
 overall_rating: 76,
 potential: 80,
 
 status: 'active' as const,
 fitness: 95,
 morale: 80,
 form: 85,
 
 wage: 25000,
 contract_end: '2025-06-30',
 release_clause: 15000000,
 squad_role: 'key_player' as const,
 market_value: 8000000,
 
 matches_played: 11,
 goals: 8,
 assists: 3,
 yellow_cards: 2,
 red_cards: 0,
 average_rating: 7.4,
 minutes_played: 990,
 
 team_id: '1',
 team_name: '东方巨龙'
}

function PlayerDetail() {
 const { id: _id } = useParams<{ id: string }>()
 const player = MOCK_PLAYER // In real app, fetch by _id

 const squadRoleNames: Record<string, string> = {
 'key_player': '核心球员',
 'first_team': '一线队',
 'rotation': '轮换',
 'backup': '替补',
 'hot_prospect': '希望之星',
 'youngster': '青训',
 'not_needed': '不需要'
 }

 const statusNames: Record<string, string> = {
 'active': '健康',
 'injured': '受伤',
 'suspended': '停赛',
 'retired': '退役'
 }

 const statusColors: Record<string, string> = {
 'active': 'text-emerald-400',
 'injured': 'text-red-400',
 'suspended': 'text-amber-400',
 'retired': 'text-[#8B8BA7]'
 }

 return (
 <div className="max-w-[1200px]">
 {/* 返回按钮 */}
 <Link 
 to={`/teams/${player.team_id}`}
 className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
 >
 <ChevronLeft className="w-4 h-4" />
 返回球队
 </Link>

 {/* 球员信息头部 */}
 <Card className="mb-6 bg-[#0D4A4D]/30 border-2 border-[#2D2D44] hover:-translate-y-1 hover:shadow-pixel transition-all">
 <div className="flex flex-col md:flex-row items-start md:items-center gap-6">
 <div className="w-28 h-28 bg-[#0D7377] border-2 border-[#0D7377]/50 flex items-center justify-center text-6xl shadow-pixel">
 👤
 </div>
 <div className="flex-1">
 <div className="flex items-center gap-3 mb-2">
 <h1 className="text-3xl font-bold text-white">{player.display_name}</h1>
 <span className={`px-2 py-0.5 rounded-none text-xs font-medium ${getPositionColor(player.primary_position)}`}>
 {player.primary_position}
 </span>
 </div>
 <div className="flex flex-wrap items-center gap-4 text-sm text-[#8B8BA7]">
 <div className="flex items-center gap-1.5">
 <MapPin className="w-4 h-4" />
 {player.nationality}
 </div>
 <div className="flex items-center gap-1.5">
 <Calendar className="w-4 h-4" />
 {player.age} 岁
 </div>
 <div className="flex items-center gap-1.5">
 <Ruler className="w-4 h-4" />
 {player.height} cm
 </div>
 <div className="flex items-center gap-1.5">
 <Weight className="w-4 h-4" />
 {player.weight} kg
 </div>
 <div className="flex items-center gap-1.5">
 <Footprints className="w-4 h-4" />
 {player.preferred_foot === 'right' ? '右脚' : player.preferred_foot === 'left' ? '左脚' : '双脚'}
 </div>
 </div>
 <div className="mt-3 flex items-center gap-4">
 <Link 
 to={`/teams/${player.team_id}`}
 className="inline-flex items-center gap-1.5 text-sm text-[#0D7377] hover:text-white transition-colors"
 >
 <Shield className="w-4 h-4" />
 {player.team_name}
 <ChevronRight className="w-3 h-3" />
 </Link>
 <span className={`text-sm ${statusColors[player.status]}`}>
 ● {statusNames[player.status]}
 </span>
 </div>
 </div>
 <div className="flex items-center gap-6">
 <div className="text-center">
 <div className="text-4xl font-bold stat-number pixel-number text-[#0D7377]">{player.overall_rating}</div>
 <div className="text-xs text-[#8B8BA7]">当前能力</div>
 </div>
 <div className="text-center">
 <div className="text-4xl font-bold stat-number pixel-number text-emerald-400">{player.potential}</div>
 <div className="text-xs text-[#8B8BA7]">潜力</div>
 </div>
 </div>
 </div>
 </Card>

 <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
 {/* 左侧 - 详细能力 */}
 <div className="lg:col-span-2 space-y-6">
 {/* 能力值 */}
 <Card hover>
 <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
 <TrendingUp className="w-5 h-5 text-[#0D7377]" />
 详细能力
 </h3>
 
 <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
 {/* 进攻 */}
 <div className="space-y-3">
 <h4 className="text-sm font-medium text-[#8B8BA7] flex items-center gap-2">
 <Target className="w-4 h-4 text-red-400" />
 进攻
 </h4>
 {[
 { label: '射门', value: player.shooting },
 { label: '终结', value: player.finishing },
 { label: '远射', value: player.long_shots },
 ].map(stat => (
 <div key={stat.label}>
 <div className="flex items-center justify-between mb-1">
 <span className="text-sm">{stat.label}</span>
 <span className="font-bold stat-number pixel-number">{stat.value}</span>
 </div>
 <div className="h-1.5 bg-[#1E1E2D] rounded-none overflow-hidden">
 <div 
 className="h-full bg-red-500 rounded-none" 
 style={{ width: `${stat.value}%` }} 
 />
 </div>
 </div>
 ))}
 </div>

 {/* 技术 */}
 <div className="space-y-3">
 <h4 className="text-sm font-medium text-[#8B8BA7] flex items-center gap-2">
 <Zap className="w-4 h-4 text-[#0D7377]" />
 技术
 </h4>
 {[
 { label: '传球', value: player.passing },
 { label: '视野', value: player.vision },
 { label: '传中', value: player.crossing },
 { label: '盘带', value: player.dribbling },
 { label: '控球', value: player.ball_control },
 ].map(stat => (
 <div key={stat.label}>
 <div className="flex items-center justify-between mb-1">
 <span className="text-sm">{stat.label}</span>
 <span className="font-bold stat-number pixel-number">{stat.value}</span>
 </div>
 <div className="h-1.5 bg-[#1E1E2D] rounded-none overflow-hidden">
 <div 
 className="h-full bg-[#0D7377] rounded-none" 
 style={{ width: `${stat.value}%` }} 
 />
 </div>
 </div>
 ))}
 </div>

 {/* 身体 */}
 <div className="space-y-3">
 <h4 className="text-sm font-medium text-[#8B8BA7] flex items-center gap-2">
 <User className="w-4 h-4 text-emerald-400" />
 身体
 </h4>
 {[
 { label: '速度', value: player.pace },
 { label: '加速', value: player.acceleration },
 { label: '力量', value: player.strength },
 { label: '耐力', value: player.stamina },
 ].map(stat => (
 <div key={stat.label}>
 <div className="flex items-center justify-between mb-1">
 <span className="text-sm">{stat.label}</span>
 <span className="font-bold stat-number pixel-number">{stat.value}</span>
 </div>
 <div className="h-1.5 bg-[#1E1E2D] rounded-none overflow-hidden">
 <div 
 className="h-full bg-emerald-500 rounded-none" 
 style={{ width: `${stat.value}%` }} 
 />
 </div>
 </div>
 ))}
 </div>

 {/* 精神 */}
 <div className="space-y-3">
 <h4 className="text-sm font-medium text-[#8B8BA7] flex items-center gap-2">
 <Award className="w-4 h-4 text-amber-400" />
 精神
 </h4>
 {[
 { label: '侵略性', value: player.aggression },
 { label: '镇定', value: player.composure },
 { label: '工作投入', value: player.work_rate },
 { label: '跑位', value: player.positioning },
 ].map(stat => (
 <div key={stat.label}>
 <div className="flex items-center justify-between mb-1">
 <span className="text-sm">{stat.label}</span>
 <span className="font-bold stat-number pixel-number">{stat.value}</span>
 </div>
 <div className="h-1.5 bg-[#1E1E2D] rounded-none overflow-hidden">
 <div 
 className="h-full bg-amber-500 rounded-none" 
 style={{ width: `${stat.value}%` }} 
 />
 </div>
 </div>
 ))}
 </div>
 </div>
 </Card>

 {/* 合同信息 */}
 <Card hover>
 <h3 className="text-lg font-semibold mb-4">合同信息</h3>
 <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
 <div className="p-4 bg-[#1E1E2D]">
 <p className="text-xs text-[#8B8BA7] mb-1">周薪</p>
 <p className="font-bold stat-number pixel-number text-white">€{(player.wage / 1000).toFixed(0)}K</p>
 </div>
 <div className="p-4 bg-[#1E1E2D]">
 <p className="text-xs text-[#8B8BA7] mb-1">合同到期</p>
 <p className="font-bold stat-number pixel-number text-white">{new Date(player.contract_end).toLocaleDateString('zh-CN')}</p>
 </div>
 <div className="p-4 bg-[#1E1E2D]">
 <p className="text-xs text-[#8B8BA7] mb-1">解约金</p>
 <p className="font-bold stat-number pixel-number text-emerald-400">€{(player.release_clause / 1000000).toFixed(1)}M</p>
 </div>
 <div className="p-4 bg-[#1E1E2D]">
 <p className="text-xs text-[#8B8BA7] mb-1">市场价值</p>
 <p className="font-bold stat-number pixel-number text-[#0D7377]">€{(player.market_value / 1000000).toFixed(1)}M</p>
 </div>
 </div>
 </Card>
 </div>

 {/* 右侧 - 统计和状态 */}
 <div className="space-y-6">
 {/* 本赛季统计 */}
 <Card hover>
 <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
 <Clock className="w-5 h-5 text-[#0D7377]" />
 本赛季统计
 </h3>
 <div className="grid grid-cols-2 gap-4">
 <div className="text-center p-4 bg-[#1E1E2D]">
 <div className="text-2xl font-bold stat-number pixel-number text-white">{player.matches_played}</div>
 <div className="text-xs text-[#8B8BA7]">出场</div>
 </div>
 <div className="text-center p-4 bg-[#1E1E2D]">
 <div className="text-2xl font-bold stat-number pixel-number text-emerald-400">{player.goals}</div>
 <div className="text-xs text-[#8B8BA7]">进球</div>
 </div>
 <div className="text-center p-4 bg-[#1E1E2D]">
 <div className="text-2xl font-bold stat-number pixel-number text-[#0D7377]">{player.assists}</div>
 <div className="text-xs text-[#8B8BA7]">助攻</div>
 </div>
 <div className="text-center p-4 bg-[#1E1E2D]">
 <div className="text-2xl font-bold stat-number pixel-number text-amber-400">{player.average_rating}</div>
 <div className="text-xs text-[#8B8BA7]">场均评分</div>
 </div>
 </div>
 <div className="mt-4 pt-4 border-t-2 border-[#2D2D44] space-y-2">
 <div className="flex items-center justify-between">
 <span className="text-sm text-[#8B8BA7]">黄牌</span>
 <span className="font-bold stat-number pixel-number text-yellow-400">{player.yellow_cards}</span>
 </div>
 <div className="flex items-center justify-between">
 <span className="text-sm text-[#8B8BA7]">红牌</span>
 <span className="font-bold stat-number pixel-number text-red-400">{player.red_cards}</span>
 </div>
 <div className="flex items-center justify-between">
 <span className="text-sm text-[#8B8BA7]">出场时间</span>
 <span className="font-bold stat-number pixel-number">{player.minutes_played} 分钟</span>
 </div>
 </div>
 </Card>

 {/* 状态 */}
 <Card hover>
 <h3 className="text-lg font-semibold mb-4">当前状态</h3>
 <div className="space-y-4">
 <div>
 <div className="flex items-center justify-between mb-2">
 <span className="text-sm text-[#8B8BA7]">体能</span>
 <span className="font-bold stat-number pixel-number">{player.fitness}%</span>
 </div>
 <div className="h-2 bg-[#1E1E2D] rounded-none overflow-hidden">
 <div 
 className={`h-full rounded-none ${player.fitness > 80 ? 'bg-emerald-500' : player.fitness > 50 ? 'bg-amber-500' : 'bg-red-500'}`}
 style={{ width: `${player.fitness}%` }} 
 />
 </div>
 </div>
 <div>
 <div className="flex items-center justify-between mb-2">
 <span className="text-sm text-[#8B8BA7]">士气</span>
 <span className="font-bold stat-number pixel-number">{player.morale}%</span>
 </div>
 <div className="h-2 bg-[#1E1E2D] rounded-none overflow-hidden">
 <div 
 className="h-full bg-blue-500 rounded-none"
 style={{ width: `${player.morale}%` }} 
 />
 </div>
 </div>
 <div>
 <div className="flex items-center justify-between mb-2">
 <span className="text-sm text-[#8B8BA7]">状态</span>
 <span className="font-bold stat-number pixel-number">{player.form}%</span>
 </div>
 <div className="h-2 bg-[#1E1E2D] rounded-none overflow-hidden">
 <div 
 className="h-full bg-purple-500 rounded-none"
 style={{ width: `${player.form}%` }} 
 />
 </div>
 </div>
 </div>
 </Card>

 {/* 角色 */}
 <Card hover>
 <h3 className="text-lg font-semibold mb-4">球队角色</h3>
 <div className="p-4 bg-[#0D4A4D]/30 border-2 border-[#0D7377]/30">
 <p className="font-medium text-white">{squadRoleNames[player.squad_role]}</p>
 <p className="text-xs text-[#8B8BA7] mt-1">
 {player.squad_role === 'key_player' ? '球队核心，不可或缺的主力球员' :
 player.squad_role === 'first_team' ? '常规首发球员' :
 player.squad_role === 'rotation' ? '轮换球员，适时出场' :
 player.squad_role === 'backup' ? '替补球员' : '年轻球员'}
 </p>
 </div>
 </Card>
 </div>
 </div>
 </div>
 )
}

export default PlayerDetail
