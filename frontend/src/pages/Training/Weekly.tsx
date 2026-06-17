import { useCallback, useEffect, useMemo, useState, type ElementType } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Archive,
  Brush,
  Check,
  Clock,
  Goal,
  MoreHorizontal,
  Reload,
  User,
  Users,
  WarningDiamond,
  ChevronLeft,
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import type { PlayerFatigueItem, TrainingItem, TrainingMode, PlanGroup, PlanSlotData } from '../../types/training'
import { getTemplateItemId, TRAINING_TEMPLATES, type TrainingTemplateDetail } from '../../types/training'
import { checkSlotConflicts } from './components/ConflictEngine'
import type { TrainingConflict } from './components/ConflictEngine'
import TrainingPickerModal from './components/TrainingPickerModal'
import GroupEditorModal from './components/GroupEditorModal'
import { TrainingTabs } from './components/TrainingTabs'
import '../../styles/training-system.css'

const DAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
const PERIODS = [
  { key: 'morning' as const, label: '上午', index: 0 },
  { key: 'afternoon' as const, label: '下午', index: 1 },
  { key: 'evening' as const, label: '晚上', index: 2 },
]
const DEFAULT_TEMPLATE = TRAINING_TEMPLATES[0]

const ATTR_NAMES: Record<string, string> = {
  sho: '射门', pas: '传球', dri: '盘带', spd: '速度', str_: '力量',
  sta: '体能', acc: '加速', hea: '头球', bal: '平衡', defe: '防守',
  tkl: '抢断', vis: '视野', cro: '传中', con: '控球', fin: '终结',
  com: '镇定', sav: '扑救', ref: '反应', pos: '站位', rus: '出击',
  dec: '决策', fk: '任意球', pk: '点球',
}

const POSITION_NAMES: Record<string, string> = {
  FW: '前锋',
  MF: '中场',
  DF: '后卫',
  GK: '门将',
}

const CATEGORY_LABELS: Record<string, string> = {
  finishing: '终结',
  passing: '传控',
  technical: '技术',
  defending: '防守',
  set_piece: '定位球',
  physical: '身体',
  tactical: '战术',
  goalkeeper: '门将',
  match: '比赛',
  recovery: '恢复',
  analysis: '分析',
  战术: '战术',
  技术: '技术',
  恢复: '恢复',
}

const INTENSITY_LABELS: Record<string, string> = {
  light: '低',
  medium: '中',
  hard: '高',
}

// PlanGroup 和 PlanSlotData 已从 ../../types/training 导入

interface MatchDayInfo {
  season_day: number
  hasMatch: boolean
  opponentName?: string
  isHome?: boolean
}

const MODE_LABELS: Record<TrainingMode, { label: string; detail: string; icon: ElementType }> = {
  team: { label: '全队统一', detail: '同一时段所有球员执行同一训练', icon: User },
  groups_2: { label: '双组训练', detail: '分成两组微调课程，切换会重排计划', icon: Users },
  groups_3: { label: '三组专项', detail: '进攻、防守、门将分别安排，切换会重排计划', icon: Users },
}

function getTopAttributes(item: TrainingItem, limit = 4) {
  return Object.entries(item.attribute_weights || {})
    .filter(([, weight]) => weight > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([attr, weight]) => ({ label: ATTR_NAMES[attr] || attr, weight }))
}

function getBestPositions(item: TrainingItem) {
  return Object.entries(item.position_fit || {})
    .filter(([, fit]) => fit >= 1)
    .sort((a, b) => b[1] - a[1])
    .map(([pos]) => POSITION_NAMES[pos] || pos)
}

function getCategoryLabel(category: string) {
  return CATEGORY_LABELS[category] || category
}

function getCategoryTone(category: string) {
  if (['finishing', 'technical', '技术'].includes(category)) return 'red'
  if (['passing', 'tactical', '战术'].includes(category)) return 'blue'
  if (['defending', 'physical'].includes(category)) return 'green'
  if (['set_piece', 'goalkeeper'].includes(category)) return 'gold'
  if (['recovery', 'analysis', '恢复'].includes(category)) return 'cyan'
  return 'neutral'
}

function getTrainingEffectDesc(item: TrainingItem) {
  if (item.is_recovery) return '恢复体能并控制疲劳，适合比赛后或密集赛程。'
  const attrs = getTopAttributes(item, 3).map(attr => attr.label)
  const positions = getBestPositions(item).slice(0, 3)
  return `${attrs.length ? `重点提升 ${attrs.join('、')}` : '综合训练'}${positions.length ? `，适合 ${positions.join('、')}` : ''}。`
}

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, value))
}

export default function WeeklyTraining() {
  const navigate = useNavigate()
  const [items, setItems] = useState<TrainingItem[]>([])
  const [fatigue, setFatigue] = useState<PlayerFatigueItem[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [selectedCell, setSelectedCell] = useState<{ dayOffset: number; periodIndex: number } | null>(null)
  const [localPlan, setLocalPlan] = useState<Map<string, PlanSlotData>>(new Map())
  const [currentDay, setCurrentDay] = useState(1)
  const [teamId, setTeamId] = useState('')
  const [seasonId, setSeasonId] = useState('')
  const [matchDays, setMatchDays] = useState<Map<number, MatchDayInfo>>(new Map())
  const [activeTemplate, setActiveTemplate] = useState<TrainingTemplateDetail>(DEFAULT_TEMPLATE)
  const [hasUserChanges, setHasUserChanges] = useState(false)
  const [globalMode, setGlobalMode] = useState<TrainingMode>('team')
  const [slotGroupSelection, setSlotGroupSelection] = useState<Map<string, string>>(new Map())
  const [groupConfig, setGroupConfig] = useState<PlanGroup[] | null>(null)
  const [brushItemId, setBrushItemId] = useState<string | null>(null)
  const [isPickerOpen, setIsPickerOpen] = useState(false)
  const [pickerMode, setPickerMode] = useState<'replace' | 'brush'>('replace')
  const [isGroupEditorOpen, setIsGroupEditorOpen] = useState(false)

  const startDay = currentDay

  const getCellKey = useCallback((dayOffset: number, slot: string) => `${startDay + dayOffset}-${slot}`, [startDay])
  const getCell = useCallback((dayOffset: number, slot: string) => localPlan.get(getCellKey(dayOffset, slot)), [getCellKey, localPlan])
  const isToday = useCallback((dayOffset: number) => startDay + dayOffset === currentDay, [currentDay, startDay])

  const getItemById = useCallback((id: string | null) => {
    if (!id) return null
    return items.find(item => item.id === id) || null
  }, [items])

  useEffect(() => {
    let cancelled = false

    async function fetchData() {
      try {
        const [teamRes, seasonRes, itemsRes] = await Promise.all([
          api.get<{ id: string }>('/teams/my-team'),
          api.getCurrentSeason(),
          api.getTrainingItems(),
        ])
        if (!teamRes.success || !teamRes.data?.id) return
        if (!seasonRes.success || !seasonRes.data?.id) return

        const tid = teamRes.data.id
        const sid = seasonRes.data.id
        const seasonNumber = seasonRes.data.season_number || 1
        const cDay = seasonRes.data.current_day || 1

        setTeamId(tid)
        setSeasonId(sid)
        setCurrentDay(cDay)
        if (itemsRes.success && Array.isArray(itemsRes.data)) setItems(itemsRes.data)

        const [planRes, fixtureRes, fatigueRes] = await Promise.all([
          api.getTeamTrainingPlan(tid, sid, cDay, 7),
          api.getTeamFixtures(seasonNumber, tid),
          api.getTeamFatigue(tid),
        ])
        if (cancelled) return

        const matchMap = new Map<number, MatchDayInfo>()
        if (fixtureRes.success && fixtureRes.data?.fixtures) {
          const fixtures = fixtureRes.data.fixtures as Array<{
            day: number
            home_team_id: string
            away_team_id: string
            home_team_name?: string
            away_team_name?: string
          }>
          for (const fixture of fixtures) {
            if (fixture.day < cDay || fixture.day >= cDay + 7) continue
            const isHome = fixture.home_team_id === tid
            matchMap.set(fixture.day, {
              season_day: fixture.day,
              hasMatch: true,
              isHome,
              opponentName: isHome ? fixture.away_team_name || '客队' : fixture.home_team_name || '主队',
            })
          }
        }
        setMatchDays(matchMap)

        if (fatigueRes.success) setFatigue(fatigueRes.data?.players || [])

        const fetchedPlans = planRes.success && Array.isArray(planRes.data) ? planRes.data : []
        const planMap = new Map<string, PlanSlotData>()
        let inferredMode: TrainingMode = 'team'
        for (const plan of fetchedPlans) {
          if (plan.mode && plan.mode !== 'team') {
            inferredMode = plan.mode as TrainingMode
            break
          }
        }
        setGlobalMode(inferredMode)

        for (const plan of fetchedPlans) {
          const groups = plan.groups
            ? plan.groups.map(group => ({
                group_id: group.group_id,
                name: group.name,
                player_ids: group.player_ids,
                training_item_id: group.training_item_id || null,
              }))
            : null

          planMap.set(`${plan.season_day}-${plan.slot}`, {
            mode: (plan.mode as TrainingMode) || 'team',
            training_item_id: plan.training_item_id || null,
            groups,
            isAutoSuggested: false,
            isUserModified: false,
            isMatchDay: false,
          })
        }

        for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
          const seasonDay = cDay + dayOffset
          for (const period of PERIODS) {
            const key = `${seasonDay}-${period.key}`
            if (planMap.has(key)) continue

            if (matchMap.has(seasonDay) && period.key === 'evening') {
              planMap.set(key, {
                mode: inferredMode,
                training_item_id: null,
                groups: null,
                isAutoSuggested: false,
                isUserModified: false,
                isMatchDay: true,
              })
              continue
            }

            planMap.set(key, {
              mode: inferredMode,
              training_item_id: inferredMode === 'team' ? getTemplateItemId(DEFAULT_TEMPLATE, dayOffset, period.index) : null,
              groups: null,
              isAutoSuggested: true,
              isUserModified: false,
              isMatchDay: false,
            })
          }
        }

        setLocalPlan(planMap)
        setSelectedCell({ dayOffset: 0, periodIndex: 0 })

        if (inferredMode !== 'team') {
          const autoGroupRes = await api.autoGroupPlayers(tid, inferredMode)
          if (cancelled) return
          if (autoGroupRes.success && autoGroupRes.data) {
            const backendGroups = autoGroupRes.data.groups.map(group => ({
              group_id: group.group_id,
              name: group.name,
              player_ids: group.player_ids,
              training_item_id: null as string | null,
            }))
            setGroupConfig(backendGroups)
            setLocalPlan(prev => {
              const next = new Map(prev)
              for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
                const seasonDay = cDay + dayOffset
                for (const period of PERIODS) {
                  const key = `${seasonDay}-${period.key}`
                  const cell = next.get(key)
                  if (!cell || cell.isMatchDay || cell.groups) continue
                  const templateItemId = getTemplateItemId(DEFAULT_TEMPLATE, dayOffset, period.index)
                  next.set(key, {
                    ...cell,
                    groups: backendGroups.map(group => ({ ...group, training_item_id: templateItemId })),
                  })
                }
              }
              return next
            })
          }
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    fetchData()
    return () => {
      cancelled = true
    }
  }, [])

  const selectedSlot = selectedCell ? PERIODS[selectedCell.periodIndex] : null
  const selectedCellData = selectedCell && selectedSlot ? getCell(selectedCell.dayOffset, selectedSlot.key) : undefined
  const selectedGroupId = useMemo(() => {
    if (!selectedCell || !selectedCellData?.groups?.length) return null
    const key = `${selectedCell.dayOffset}-${selectedCell.periodIndex}`
    return slotGroupSelection.get(key) || selectedCellData.groups[0]?.group_id || null
  }, [selectedCell, selectedCellData, slotGroupSelection])

  const activeGroup = useMemo(() => {
    if (!selectedCellData?.groups?.length) return null
    return selectedCellData.groups.find(group => group.group_id === selectedGroupId) || selectedCellData.groups[0] || null
  }, [selectedCellData, selectedGroupId])
  const focusedTrainingItem = selectedCellData?.mode === 'team'
    ? getItemById(selectedCellData.training_item_id)
    : getItemById(activeGroup?.training_item_id || null)

  const categories = useMemo(() => {
    const seen = new Set(items.map(item => item.category))
    return ['all', ...Array.from(seen)]
  }, [items])

  // visibleItems 已迁移至 TrainingPickerModal 内部管理

  const stats = useMemo(() => {
    let planned = 0
    let modified = 0
    let matchSlots = 0
    for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
      for (const period of PERIODS) {
        const cell = getCell(dayOffset, period.key)
        if (!cell) continue
        if (cell.isMatchDay) {
          matchSlots += 1
        } else if (cell.mode === 'team' ? cell.training_item_id : cell.groups?.some(group => group.training_item_id)) {
          planned += 1
        }
        if (cell.isUserModified) modified += 1
      }
    }
    return { planned, modified, matchSlots }
  }, [getCell])

  const conflictsMap = useMemo(() => {
    const map = new Map<string, TrainingConflict[]>()
    for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
      for (let periodIndex = 0; periodIndex < PERIODS.length; periodIndex++) {
        const slot = PERIODS[periodIndex]
        const cell = getCell(dayOffset, slot.key)
        const list = checkSlotConflicts(dayOffset, periodIndex, cell, matchDays, fatigue, items, startDay, getCell)
        if (list.length) map.set(`${dayOffset}-${periodIndex}`, list)
      }
    }
    return map
  }, [getCell, matchDays, fatigue, items, startDay])

  // dailyOverloadDays 已移除（UI 中不再显示过载标记）

  const switchMode = useCallback(async (newMode: TrainingMode) => {
    if (newMode === globalMode || !teamId) return
    if (hasUserChanges && !confirm('切换分组方式会重新整理当前训练计划，未保存的手动微调可能失效。确定继续吗？')) return

    setGlobalMode(newMode)
    setSlotGroupSelection(new Map())
    setHasUserChanges(true)

    if (newMode === 'team') {
      setGroupConfig(null)
      setLocalPlan(prev => {
        const next = new Map(prev)
        for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
          for (const period of PERIODS) {
            const key = getCellKey(dayOffset, period.key)
            const cell = next.get(key)
            if (!cell || cell.isMatchDay) continue
            next.set(key, {
              ...cell,
              mode: 'team',
              training_item_id: cell.groups?.find(group => group.training_item_id)?.training_item_id || cell.training_item_id || getTemplateItemId(activeTemplate, dayOffset, period.index),
              groups: null,
              isUserModified: true,
            })
          }
        }
        return next
      })
      return
    }

    const autoGroupRes = await api.autoGroupPlayers(teamId, newMode)
    if (!autoGroupRes.success || !autoGroupRes.data) return
    const backendGroups = autoGroupRes.data.groups.map(group => ({
      group_id: group.group_id,
      name: group.name,
      player_ids: group.player_ids,
      training_item_id: null as string | null,
    }))
    setGroupConfig(backendGroups)
    setLocalPlan(prev => {
      const next = new Map(prev)
      for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
        for (const period of PERIODS) {
          const key = getCellKey(dayOffset, period.key)
          const cell = next.get(key)
          if (!cell || cell.isMatchDay) continue
          const itemId = cell.training_item_id || getTemplateItemId(activeTemplate, dayOffset, period.index)
          next.set(key, {
            ...cell,
            mode: newMode,
            training_item_id: null,
            groups: backendGroups.map(group => ({ ...group, training_item_id: itemId })),
            isUserModified: true,
          })
        }
      }
      return next
    })
  }, [activeTemplate, getCellKey, globalMode, hasUserChanges, teamId])

  const applyTrainingItemToSlot = useCallback((trainingId: string, dayOffset: number, periodKey: string, groupId?: string | null) => {
    const key = getCellKey(dayOffset, periodKey)
    const cell = localPlan.get(key)
    if (!cell || cell.isMatchDay) return false

    const next = new Map(localPlan)
    if (cell.mode === 'team') {
      next.set(key, { ...cell, training_item_id: trainingId, isAutoSuggested: false, isUserModified: true })
    } else {
      const targetGroupId = groupId || cell.groups?.[0]?.group_id
      if (!targetGroupId || !cell.groups) return false
      next.set(key, {
        ...cell,
        groups: cell.groups.map(group => group.group_id === targetGroupId ? { ...group, training_item_id: trainingId } : group),
        isAutoSuggested: false,
        isUserModified: true,
      })
    }
    setLocalPlan(next)
    setHasUserChanges(true)
    return true
  }, [getCellKey, localPlan])

  const applyTrainingItem = useCallback((trainingId: string) => {
    if (!selectedCell || !selectedSlot) return
    applyTrainingItemToSlot(trainingId, selectedCell.dayOffset, selectedSlot.key, selectedGroupId)
  }, [applyTrainingItemToSlot, selectedCell, selectedGroupId, selectedSlot])

  const handleSlotClick = useCallback((dayOffset: number, periodIndex: number) => {
    if (brushItemId) {
      const period = PERIODS[periodIndex]
      const didApply = applyTrainingItemToSlot(brushItemId, dayOffset, period.key)
      if (didApply) return
    }
    setSelectedCell({ dayOffset, periodIndex })
    const cell = getCell(dayOffset, PERIODS[periodIndex].key)
    const firstGroup = cell?.groups?.[0]?.group_id || null
    if (firstGroup) {
      setSlotGroupSelection(prev => {
        const next = new Map(prev)
        next.set(`${dayOffset}-${periodIndex}`, firstGroup)
        return next
      })
    }
  }, [brushItemId, applyTrainingItemToSlot, getCell])

  const clearSelectedCell = useCallback(() => {
    if (!selectedCell || !selectedSlot) return
    const key = getCellKey(selectedCell.dayOffset, selectedSlot.key)
    const cell = localPlan.get(key)
    if (!cell || cell.isMatchDay) return
    const next = new Map(localPlan)
    next.set(key, cell.mode === 'team'
      ? { ...cell, training_item_id: null, isAutoSuggested: false, isUserModified: true }
      : { ...cell, groups: cell.groups?.map(group => ({ ...group, training_item_id: null })) || null, isAutoSuggested: false, isUserModified: true })
    setLocalPlan(next)
    setHasUserChanges(true)
  }, [getCellKey, localPlan, selectedCell, selectedSlot])

  const applyTemplate = useCallback((template: TrainingTemplateDetail, force = false) => {
    setActiveTemplate(template)
    setLocalPlan(prev => {
      const next = new Map(prev)
      for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
        for (const period of PERIODS) {
          const key = getCellKey(dayOffset, period.key)
          const cell = next.get(key)
          if (!cell || cell.isMatchDay || (!force && cell.isUserModified)) continue
          const itemId = getTemplateItemId(template, dayOffset, period.index)
          next.set(key, cell.mode === 'team'
            ? { ...cell, training_item_id: itemId, isAutoSuggested: true, isUserModified: false }
            : { ...cell, groups: (cell.groups || groupConfig || []).map(group => ({ ...group, training_item_id: itemId })), isAutoSuggested: true, isUserModified: false })
        }
      }
      return next
    })
    setHasUserChanges(true)
  }, [getCellKey, groupConfig])

  const savePlan = async () => {
    if (!teamId || !seasonId) return
    setSaving(true)
    setSaveMsg('')
    try {
      const saveItems: Array<{
        season_day: number
        slot: string
        mode: string
        training_item_id?: string
        groups?: Array<{ group_id: string; name: string; player_ids: string[]; training_item_id: string }>
      }> = []

      for (let dayOffset = 0; dayOffset < 7; dayOffset++) {
        for (const period of PERIODS) {
          const cell = getCell(dayOffset, period.key)
          if (!cell || cell.isMatchDay) continue
          const base = { season_day: startDay + dayOffset, slot: period.key, mode: cell.mode }
          if (cell.mode === 'team') {
            saveItems.push(cell.training_item_id ? { ...base, training_item_id: cell.training_item_id } : base)
          } else {
            const groups = (cell.groups || [])
              .filter(group => group.training_item_id)
              .map(group => ({
                group_id: group.group_id,
                name: group.name,
                player_ids: group.player_ids,
                training_item_id: group.training_item_id!,
              }))
            saveItems.push(groups.length ? { ...base, groups } : base)
          }
        }
      }

      const res = await api.saveTeamTrainingPlan(teamId, seasonId, saveItems)
      if (res.success) {
        setSaveMsg('保存成功')
        setHasUserChanges(false)
        setLocalPlan(prev => {
          const next = new Map(prev)
          for (const [key, cell] of next) next.set(key, { ...cell, isAutoSuggested: false, isUserModified: false })
          return next
        })
      } else {
        setSaveMsg(res.message || '保存失败')
      }
    } catch {
      setSaveMsg('保存失败')
    } finally {
      setSaving(false)
      window.setTimeout(() => setSaveMsg(''), 2200)
    }
  }

  if (loading) {
    return (
      <div className="training-console-page">
        <div className="training-loading">训练场数据接入中...</div>
      </div>
    )
  }

  return (
    <div className="training-console-page">
      <button
        onClick={() => navigate(-1)}
        className="inline-flex items-center gap-1 text-sm text-[#8B8BA7] hover:text-white transition-colors mb-4"
      >
        <ChevronLeft className="w-4 h-4" />
        返回上一页
      </button>
      <TrainingTabs />
      <section className="training-mode-panel">
        {(['team', 'groups_2', 'groups_3'] as TrainingMode[]).map(mode => {
          const config = MODE_LABELS[mode]
          const Icon = config.icon
          return (
            <button
              key={mode}
              onClick={() => switchMode(mode)}
              className={`training-mode-card ${globalMode === mode ? 'is-active' : ''}`}
            >
              <Icon className="h-4 w-4" />
              <strong>{config.label}</strong>
              <span>{config.detail}</span>
            </button>
          )
        })}
      </section>

      <div style={{ display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: 8, marginBottom: 10 }}>
        {globalMode !== 'team' && (
          <button onClick={() => setIsGroupEditorOpen(true)} className="training-ghost-btn">
            <Users className="h-4 w-4" />
            调整分组
          </button>
        )}
        <button onClick={() => applyTemplate(activeTemplate, true)} className="training-ghost-btn">
          <Reload className="h-4 w-4" />
          重置模板
        </button>
        <button onClick={savePlan} disabled={saving} className="training-save-btn">
          {saving ? <Clock className="h-4 w-4 animate-spin" /> : <Archive className="h-4 w-4" />}
          {hasUserChanges ? '保存修改' : '保存计划'}
        </button>
        {saveMsg && (
          <span className={`training-save-msg ${saveMsg.includes('成功') ? 'is-ok' : 'is-bad'}`}>
            {saveMsg.includes('成功') && <Check className="h-4 w-4" />}
            {saveMsg}
          </span>
        )}
      </div>

      <main className="training-workbench">
        <section className="training-board">
          <div className="training-week-grid" style={{ gridTemplateColumns: '40px repeat(7, minmax(0, 1fr))', gap: 6 }}>
            {/* 左上角空白 */}
            <div />
            {/* 7 个日期 header */}
            {Array.from({ length: 7 }).map((_, dayOffset) => {
              const seasonDay = startDay + dayOffset
              return (
                <div key={`header-${seasonDay}`} className={`training-day-header ${isToday(dayOffset) ? 'is-today' : ''}`}>
                  <strong>{DAYS[(seasonDay - 1) % 7]}</strong>
                  <span>第 {seasonDay} 天</span>
                </div>
              )
            })}
            {/* 3 个时段 × 8 列 */}
            {PERIODS.map((period, periodIndex) => (
              <>
                <div key={`label-${period.key}`} className="training-period-label">
                  {period.label}
                </div>
                {Array.from({ length: 7 }).map((_, dayOffset) => {
                  const seasonDay = startDay + dayOffset
                  const matchInfo = matchDays.get(seasonDay)
                  const cell = getCell(dayOffset, period.key)
                  const selected = selectedCell?.dayOffset === dayOffset && selectedCell.periodIndex === periodIndex
                  const slotConflicts = conflictsMap.get(`${dayOffset}-${periodIndex}`) || []
                  const topConflict = slotConflicts[0]
                  const isBrushTarget = brushItemId && !cell?.isMatchDay
                  return (
                    <button
                      key={`${seasonDay}-${period.key}`}
                      disabled={cell?.isMatchDay}
                      onClick={() => handleSlotClick(dayOffset, periodIndex)}
                      title={topConflict?.message || undefined}
                      className={`training-slot-block ${selected ? 'is-selected' : ''} ${cell?.isMatchDay ? 'is-match' : ''} ${cell?.isUserModified ? 'is-edited' : ''} ${isBrushTarget ? 'is-brush-preview' : ''}`}
                    >
                      {topConflict && (
                        <div className={`slot-warning ${topConflict.level}`}>
                          {topConflict.level === 'error' ? '!' : '▲'}
                        </div>
                      )}
                      {cell?.isMatchDay ? (
                        <MatchBlock match={matchInfo} />
                      ) : cell?.mode === 'team' ? (
                        <TeamBlock cell={cell} getItemById={getItemById} />
                      ) : cell ? (
                        <GroupBlock cell={cell} getItemById={getItemById} />
                      ) : (
                        <span className="slot-empty">未安排</span>
                      )}
                    </button>
                  )
                })}
              </>
            ))}
          </div>
        </section>

        <aside className="training-library">
          <section className="training-editor-panel">
            {selectedCellData?.isMatchDay ? (
              <div className="training-match-lock">
                <Goal className="h-5 w-5" />
                <strong>比赛日程已锁定</strong>
                <span>比赛时段由赛程决定，不能修改训练内容。</span>
              </div>
            ) : (
              <>
                {selectedCellData?.mode !== 'team' && selectedCellData?.groups && (
                  <div className="training-group-tabs">
                    {selectedCellData.groups.map(group => (
                      <button
                        key={group.group_id}
                        onClick={() => {
                          if (!selectedCell) return
                          const key = `${selectedCell.dayOffset}-${selectedCell.periodIndex}`
                          setSlotGroupSelection(prev => {
                            const next = new Map(prev)
                            next.set(key, group.group_id)
                            return next
                          })
                        }}
                        className={selectedGroupId === group.group_id ? 'is-active' : ''}
                        title={`${group.name} · ${group.player_ids.length}人`}
                      >
                        {group.name}
                      </button>
                    ))}
                  </div>
                )}

                <button
                  onClick={() => {
                    if (!selectedCellData || selectedCellData.isMatchDay) return
                    setPickerMode('replace')
                    setIsPickerOpen(true)
                  }}
                  className={`training-focus-card tone-${focusedTrainingItem ? getCategoryTone(focusedTrainingItem.category) : 'neutral'}`}
                  style={{ width: '100%', cursor: selectedCellData && !selectedCellData.isMatchDay ? 'pointer' : 'default' }}
                  disabled={!selectedCellData || selectedCellData.isMatchDay}
                  title={selectedCellData && !selectedCellData.isMatchDay ? '点击更换训练' : undefined}
                >
                  {focusedTrainingItem ? (
                    <>
                      <div className="training-focus-head">
                        <div>
                          <strong>{focusedTrainingItem.name}</strong>
                          <span>{getCategoryLabel(focusedTrainingItem.category)} · 强度 {INTENSITY_LABELS[focusedTrainingItem.intensity] || focusedTrainingItem.intensity}</span>
                        </div>
                        <em>{selectedCellData?.mode === 'team' ? '全队' : activeGroup?.name || '分组'}</em>
                      </div>
                      <p>{getTrainingEffectDesc(focusedTrainingItem)}</p>
                      <div className="training-focus-bars">
                        {getTopAttributes(focusedTrainingItem, 5).map(attr => (
                          <div key={attr.label}>
                            <span>{attr.label}</span>
                            <i><b style={{ width: `${Math.min(100, attr.weight * 100)}%` }} /></i>
                          </div>
                        ))}
                      </div>
                      <div style={{ marginTop: 8, color: 'var(--tr-accent)', fontSize: 12, fontWeight: 1000 }}>↳ 点击更换训练</div>
                    </>
                  ) : (
                    <div className="training-empty-focus">
                      <strong>未安排训练</strong>
                      <span>点击此处从训练库中选择项目。</span>
                    </div>
                  )}
                </button>

              </>
            )}
          </section>

          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => {
                if (brushItemId) {
                  setBrushItemId(null)
                } else {
                  setPickerMode('brush')
                  setIsPickerOpen(true)
                }
              }}
              className={`training-ghost-btn ${brushItemId ? 'is-active' : ''}`}
              style={brushItemId ? { borderColor: 'var(--tr-accent)', color: 'var(--tr-accent)', flex: 1, padding: '7px 8px', fontSize: 12 } : { flex: 1, padding: '7px 8px', fontSize: 12 }}
              title={brushItemId ? '点击取消画笔' : '选择训练后批量填入格子'}
            >
              <Brush className="h-4 w-4" />
              {brushItemId ? `画笔: ${items.find(i => i.id === brushItemId)?.name?.slice(0, 8) || ''}` : '画笔'}
            </button>
            {selectedCellData && !selectedCellData.isMatchDay && (
              <button onClick={clearSelectedCell} className="training-ghost-btn" style={{ flex: 1, padding: '7px 8px', fontSize: 12 }}>
                清空
              </button>
            )}
          </div>
        </aside>
      </main>

      {/* 球员负荷横向条 */}
      <section className="training-fatigue-strip">
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 10, color: 'var(--tr-accent)' }}>
          <WarningDiamond className="h-4 w-4" />
          <h3 style={{ fontSize: 14, fontWeight: 1000, margin: 0 }}>球员负荷</h3>
        </div>
        {fatigue.length === 0 ? (
          <p style={{ color: 'var(--tr-muted)', fontSize: 12, fontWeight: 800 }}>暂无疲劳数据。</p>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(160px, 1fr))', gap: 8 }}>
            {fatigue.map(player => (
              <div
                key={player.player_id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: 8,
                  padding: '6px 10px',
                  background: 'rgba(5,6,9,0.88)',
                  border: '1px solid var(--tr-border)',
                }}
              >
                <span style={{ color: 'var(--tr-text)', fontSize: 12, fontWeight: 800, width: 60, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {player.player_name}
                </span>
                <div style={{ flex: 1, height: 6, border: '1px solid var(--tr-border)', background: '#050609' }}>
                  <div
                    style={{
                      height: '100%',
                      width: `${clampPercent(player.fatigue)}%`,
                      background: player.fatigue > 70 ? '#D75A4A' : player.fatigue > 45 ? '#D7A94A' : '#9ECF45',
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      <TrainingPickerModal
        isOpen={isPickerOpen}
        onClose={() => setIsPickerOpen(false)}
        items={items}
        categories={categories}
        onSelect={(itemId: string) => {
          if (pickerMode === 'brush') {
            setBrushItemId(itemId)
          } else {
            applyTrainingItem(itemId)
          }
          setIsPickerOpen(false)
        }}
        cellMode={selectedCellData?.mode}
        activeGroupName={activeGroup?.name}
        fatigue={fatigue}
      />

      <GroupEditorModal
        isOpen={isGroupEditorOpen}
        onClose={() => setIsGroupEditorOpen(false)}
        groups={groupConfig}
        fatigue={fatigue}
        mode={globalMode}
        onSave={(newGroups: PlanGroup[]) => {
          setGroupConfig(newGroups)
          setHasUserChanges(true)
          // 同步更新所有已有 plan 中的 groups
          setLocalPlan(prev => {
            const next = new Map(prev)
            for (const [key, cell] of next) {
              if (cell.isMatchDay || cell.mode === 'team') continue
              const templateItemId = cell.groups?.find(g => g.training_item_id)?.training_item_id || cell.training_item_id
              next.set(key, {
                ...cell,
                groups: newGroups.map(g => ({
                  ...g,
                  training_item_id: cell.groups?.find(cg => cg.group_id === g.group_id)?.training_item_id || templateItemId || null,
                })),
                isUserModified: true,
              })
            }
            return next
          })
        }}
      />

      {hasUserChanges && (
        <div className="training-unsaved-bar">
          <span>⚠ 你有未保存的修改（调整了 {stats.modified} 个时段）</span>
          <button className="btn-primary" onClick={savePlan} disabled={saving}>
            {saving ? '保存中…' : '保存修改'}
          </button>
          <button
            className="btn-secondary"
            onClick={() => {
              if (confirm('放弃所有未保存的修改？')) {
                window.location.reload()
              }
            }}
          >
            放弃更改
          </button>
        </div>
      )}
    </div>
  )
}

function MatchBlock({ match }: { match?: MatchDayInfo }) {
  return (
    <div className="training-match-block">
      <Goal className="h-4 w-4" />
      <strong>比赛</strong>
      <span>{match?.opponentName || '赛程已确定'}</span>
    </div>
  )
}

function TeamBlock({ cell, getItemById }: { cell: PlanSlotData; getItemById: (id: string | null) => TrainingItem | null }) {
  const item = getItemById(cell.training_item_id)
  if (!item) return <span className="slot-empty">未安排</span>
  return <TrainingBlock item={item} auto={cell.isAutoSuggested} edited={cell.isUserModified} />
}

function GroupBlock({ cell, getItemById }: { cell: PlanSlotData; getItemById: (id: string | null) => TrainingItem | null }) {
  if (!cell.groups?.length) return <span className="slot-empty">未分组</span>
  return (
    <div className="training-group-block">
      {cell.groups.map(group => {
        const item = getItemById(group.training_item_id)
        return (
          <div key={group.group_id}>
            <strong>{item?.name || '未安排'}</strong>
          </div>
        )
      })}
      <div className="slot-markers">
        {cell.isAutoSuggested && <MoreHorizontal className="h-3 w-3" />}
        {cell.isUserModified && <i />}
      </div>
    </div>
  )
}

function TrainingBlock({ item, auto, edited }: { item: TrainingItem; auto: boolean; edited: boolean }) {
  return (
    <div className={`training-block-content tone-${getCategoryTone(item.category)}`}>
      <strong>{item.name}</strong>
      <div className="slot-markers">
        {auto && <MoreHorizontal className="h-3 w-3" />}
        {edited && <i />}
      </div>
    </div>
  )
}

// TrainingItemCard 已迁移至 TrainingPickerModal 内部渲染
