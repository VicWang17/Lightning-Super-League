import type { TrainingItem, PlayerFatigueItem, PlanSlotData } from '../../../types/training'

export interface TrainingConflict {
  rule_id: string
  level: 'warn' | 'error'
  message: string
  affected_players?: string[] // player_ids
}

const INTENSITY_RANK: Record<string, number> = {
  light: 1,
  medium: 2,
  hard: 3,
}

export function checkSlotConflicts(
  dayOffset: number,
  _periodIndex: number,
  cell: PlanSlotData | undefined,
  matchDays: Map<number, { season_day: number; hasMatch: boolean }>,
  fatigue: PlayerFatigueItem[],
  items: TrainingItem[],
  startDay: number,
  getCell: (d: number, s: string) => PlanSlotData | undefined,
): TrainingConflict[] {
  const conflicts: TrainingConflict[] = []
  if (!cell || cell.isMatchDay) return conflicts

  const seasonDay = startDay + dayOffset

  const trainingItems: TrainingItem[] = []
  if (cell.mode === 'team') {
    const item = items.find(i => i.id === cell.training_item_id)
    if (item) trainingItems.push(item)
  } else {
    for (const group of cell.groups || []) {
      const item = items.find(i => i.id === group.training_item_id)
      if (item) trainingItems.push(item)
    }
  }

  if (trainingItems.length === 0) return conflicts

  // 规则1: 比赛前一日高强度训练
  const nextDay = seasonDay + 1
  if (matchDays.has(nextDay)) {
    for (const item of trainingItems) {
      if (INTENSITY_RANK[item.intensity] >= 3) {
        conflicts.push({
          rule_id: 'PRE_MATCH_HIGH',
          level: 'warn',
          message: '比赛前一日安排高强度训练，可能降低比赛状态',
        })
        break
      }
    }
  }

  // 规则2: 单日累计疲劳过载
  let dailyFatigue = 0
  for (let p = 0; p < 3; p++) {
    const slotKey = ['morning', 'afternoon', 'evening'][p]
    const otherCell = getCell(dayOffset, slotKey)
    if (!otherCell || otherCell.isMatchDay) continue
    if (otherCell.mode === 'team') {
      const item = items.find(i => i.id === otherCell.training_item_id)
      if (item) dailyFatigue += item.fatigue_delta
    } else {
      for (const group of otherCell.groups || []) {
        const item = items.find(i => i.id === group.training_item_id)
        if (item) dailyFatigue += item.fatigue_delta
      }
    }
  }
  if (dailyFatigue > 20) {
    conflicts.push({
      rule_id: 'DAILY_OVERLOAD',
      level: 'error',
      message: `当日累计疲劳 +${dailyFatigue}，超过安全阈值 20`,
    })
  }

  // 规则3: 高疲劳球员被安排疲劳训练
  const affectedPlayers: string[] = []
  for (const item of trainingItems) {
    if (item.fatigue_delta <= 5) continue
    // 确定这个训练影响哪些球员
    let targetPlayerIds: string[] = []
    if (cell.mode === 'team') {
      targetPlayerIds = fatigue.map(p => p.player_id)
    } else {
      const group = cell.groups?.find((g: { training_item_id: string | null }) => g.training_item_id === item.id)
      if (group) targetPlayerIds = group.player_ids
    }
    for (const pid of targetPlayerIds) {
      const pf = fatigue.find(p => p.player_id === pid)
      if (pf && pf.fatigue > 70) {
        affectedPlayers.push(pid)
      }
    }
  }
  if (affectedPlayers.length > 0) {
    conflicts.push({
      rule_id: 'PLAYER_FATIGUE',
      level: 'error',
      message: `有 ${affectedPlayers.length} 名疲劳 >70% 的球员不适合此项训练`,
      affected_players: affectedPlayers,
    })
  }

  return conflicts
}

export function checkDailyOverload(
  dayOffset: number,
  getCell: (d: number, s: string) => PlanSlotData | undefined,
  items: TrainingItem[],
): boolean {
  let dailyFatigue = 0
  for (let p = 0; p < 3; p++) {
    const slotKey = ['morning', 'afternoon', 'evening'][p]
    const cell = getCell(dayOffset, slotKey)
    if (!cell || cell.isMatchDay) continue
    if (cell.mode === 'team') {
      const item = items.find(i => i.id === cell.training_item_id)
      if (item) dailyFatigue += item.fatigue_delta
    } else {
      for (const group of cell.groups || []) {
        const item = items.find(i => i.id === group.training_item_id)
        if (item) dailyFatigue += item.fatigue_delta
      }
    }
  }
  return dailyFatigue > 20
}
