import { useCallback, useEffect, useMemo, useState, type ElementType } from 'react'
import {
  Archive,
  Check,
  Clock,
  Goal,
  MoreHorizontal,
  Reload,
  User,
  Users,
  WarningDiamond,
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import type { PlayerFatigueItem, TrainingItem, TrainingMode } from '../../types/training'
import { getTemplateItemId, TRAINING_TEMPLATES, type TrainingTemplateDetail } from '../../types/training'

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

interface PlanGroup {
  group_id: string
  name: string
  player_ids: string[]
  training_item_id: string | null
}

interface PlanSlotData {
  mode: TrainingMode
  training_item_id: string | null
  groups: PlanGroup[] | null
  isAutoSuggested: boolean
  isUserModified: boolean
  isMatchDay: boolean
}

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
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null)
  const [groupConfig, setGroupConfig] = useState<PlanGroup[] | null>(null)
  const [activeCategory, setActiveCategory] = useState('all')

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
            setSelectedGroupId(backendGroups[0]?.group_id || null)
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
  const selectedDay = selectedCell ? startDay + selectedCell.dayOffset : null
  const selectedCellData = selectedCell && selectedSlot ? getCell(selectedCell.dayOffset, selectedSlot.key) : undefined
  const activeGroup = selectedCellData?.groups?.find(group => group.group_id === selectedGroupId) || selectedCellData?.groups?.[0] || null
  const focusedTrainingItem = selectedCellData?.mode === 'team'
    ? getItemById(selectedCellData.training_item_id)
    : getItemById(activeGroup?.training_item_id || null)

  const categories = useMemo(() => {
    const seen = new Set(items.map(item => item.category))
    return ['all', ...Array.from(seen)]
  }, [items])

  const visibleItems = useMemo(() => {
    const filtered = activeCategory === 'all' ? items : items.filter(item => item.category === activeCategory)
    return filtered.sort((a, b) => {
      if (a.is_recovery !== b.is_recovery) return a.is_recovery ? 1 : -1
      return a.load_points - b.load_points
    })
  }, [activeCategory, items])

  const selectedTrainingItems = useMemo(() => {
    if (!selectedCellData || selectedCellData.isMatchDay) return []
    if (selectedCellData.mode === 'team') {
      const item = getItemById(selectedCellData.training_item_id)
      return item ? [item] : []
    }
    return (selectedCellData.groups || [])
      .map(group => getItemById(group.training_item_id))
      .filter((item): item is TrainingItem => Boolean(item))
  }, [getItemById, selectedCellData])

  const selectedLoad = selectedTrainingItems.reduce((sum, item) => sum + item.load_points, 0)
  const selectedFatigueDelta = selectedTrainingItems.reduce((sum, item) => sum + item.fatigue_delta, 0)
  const avgFitness = fatigue.length ? Math.round(fatigue.reduce((sum, player) => sum + player.fitness, 0) / fatigue.length) : 0

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

  const switchMode = useCallback(async (newMode: TrainingMode) => {
    if (newMode === globalMode || !teamId) return
    if (hasUserChanges && !confirm('切换分组方式会重新整理当前训练计划，未保存的手动微调可能失效。确定继续吗？')) return

    setGlobalMode(newMode)
    setSelectedGroupId(null)
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
    setSelectedGroupId(backendGroups[0]?.group_id || null)
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

  const applyTrainingItem = useCallback((trainingId: string) => {
    if (!selectedCell || !selectedSlot) return
    const key = getCellKey(selectedCell.dayOffset, selectedSlot.key)
    const cell = localPlan.get(key)
    if (!cell || cell.isMatchDay) return

    const next = new Map(localPlan)
    if (cell.mode === 'team') {
      next.set(key, { ...cell, training_item_id: trainingId, isAutoSuggested: false, isUserModified: true })
    } else {
      const targetGroupId = selectedGroupId || cell.groups?.[0]?.group_id
      if (!targetGroupId || !cell.groups) return
      next.set(key, {
        ...cell,
        groups: cell.groups.map(group => group.group_id === targetGroupId ? { ...group, training_item_id: trainingId } : group),
        isAutoSuggested: false,
        isUserModified: true,
      })
      setSelectedGroupId(targetGroupId)
    }
    setLocalPlan(next)
    setHasUserChanges(true)
  }, [getCellKey, localPlan, selectedCell, selectedGroupId, selectedSlot])

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
      <section className="training-hero">
        <div className="training-hero-copy">
          <div className="training-chip">
            <span />
            第 {startDay} - {startDay + 6} 天训练指令
          </div>
          <h1>训练场指挥台</h1>
        </div>
        <div className="training-command-strip">
          <div className="training-hud-note">
            <span>计划 {stats.planned}/21</span>
            <span>微调 {stats.modified}</span>
            <span>比赛锁定 {stats.matchSlots}</span>
            <span>体能 {avgFitness || '-'}%</span>
          </div>
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
      </section>

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

      <main className="training-workbench">
        <section className="training-board">
          <div className="training-board-header">
            <div>
              <h2>本周计划板</h2>
              <p>点击任意可训练时段，再从右侧选择训练内容。</p>
            </div>
            <select
              value={activeTemplate.id}
              onChange={event => {
                const template = TRAINING_TEMPLATES.find(item => item.id === event.target.value)
                if (template) applyTemplate(template)
              }}
            >
              {TRAINING_TEMPLATES.map(template => (
                <option key={template.id} value={template.id}>{template.name}</option>
              ))}
            </select>
          </div>

          <div className="training-week-grid">
            {Array.from({ length: 7 }).map((_, dayOffset) => {
              const seasonDay = startDay + dayOffset
              const matchInfo = matchDays.get(seasonDay)
              return (
                <article key={seasonDay} className={`training-day-column ${isToday(dayOffset) ? 'is-today' : ''}`}>
                  <header>
                    <strong>{DAYS[(seasonDay - 1) % 7]}</strong>
                    <span>第 {seasonDay} 天</span>
                    {matchInfo && <em>{matchInfo.isHome ? '主场' : '客场'}比赛</em>}
                  </header>
                  <div className="training-slot-stack">
                    {PERIODS.map((period, periodIndex) => {
                      const cell = getCell(dayOffset, period.key)
                      const selected = selectedCell?.dayOffset === dayOffset && selectedCell.periodIndex === periodIndex
                      return (
                        <button
                          key={period.key}
                          disabled={cell?.isMatchDay}
                          onClick={() => {
                            if (cell?.isMatchDay) return
                            setSelectedCell({ dayOffset, periodIndex })
                            const firstGroup = cell?.groups?.[0]?.group_id || null
                            if (firstGroup) setSelectedGroupId(firstGroup)
                          }}
                          className={`training-slot-block ${selected ? 'is-selected' : ''} ${cell?.isMatchDay ? 'is-match' : ''} ${cell?.isUserModified ? 'is-edited' : ''}`}
                        >
                          <span className="slot-time">{period.label}</span>
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
                  </div>
                </article>
              )
            })}
          </div>
        </section>

        <aside className="training-library">
          <section className="training-editor-panel">
            <div className="training-editor-title">
              <div>
                <h2>时段设置</h2>
                <p>{selectedDay && selectedSlot ? `第 ${selectedDay} 天 · ${selectedSlot.label}` : '请选择计划板上的时段'}</p>
              </div>
              {selectedCellData && !selectedCellData.isMatchDay && (
                <button onClick={clearSelectedCell}>清空</button>
              )}
            </div>

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
                        onClick={() => setSelectedGroupId(group.group_id)}
                        className={selectedGroupId === group.group_id ? 'is-active' : ''}
                      >
                        <strong>{group.name}</strong>
                        <span>{group.player_ids.length} 人</span>
                      </button>
                    ))}
                  </div>
                )}

                <div className={`training-focus-card tone-${focusedTrainingItem ? getCategoryTone(focusedTrainingItem.category) : 'neutral'}`}>
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
                    </>
                  ) : (
                    <div className="training-empty-focus">
                      <strong>未安排训练</strong>
                      <span>从下方训练库选择一个项目，写入当前时段。</span>
                    </div>
                  )}
                </div>

                <div className="training-slot-preview">
                  <PreviewMetric label="训练负荷" value={selectedLoad || '-'} />
                  <PreviewMetric label="疲劳变化" value={selectedTrainingItems.length ? `${selectedFatigueDelta > 0 ? '+' : ''}${selectedFatigueDelta}` : '-'} />
                  <PreviewMetric label="模式" value={selectedCellData ? MODE_LABELS[selectedCellData.mode].label : '-'} />
                </div>
              </>
            )}
          </section>

          <section className="training-item-panel">
            <div className="training-category-tabs">
              {categories.map(category => (
                <button
                  key={category}
                  onClick={() => setActiveCategory(category)}
                  className={activeCategory === category ? 'is-active' : ''}
                >
                  {category === 'all' ? '全部' : getCategoryLabel(category)}
                </button>
              ))}
            </div>
            <div className="training-item-list">
              {visibleItems.map(item => (
                <TrainingItemCard
                  key={item.id}
                  item={item}
                  disabled={!selectedCellData || selectedCellData.isMatchDay}
                  selected={selectedTrainingItems.some(selected => selected.id === item.id)}
                  onSelect={() => applyTrainingItem(item.id)}
                />
              ))}
            </div>
          </section>

          <section className="training-fatigue-panel">
            <div className="training-panel-heading">
              <WarningDiamond className="h-4 w-4" />
              <h2>球员负荷</h2>
            </div>
            {fatigue.length === 0 ? (
              <p className="training-muted">暂无疲劳数据。</p>
            ) : (
              <div className="training-fatigue-list">
                {fatigue.slice(0, 8).map(player => (
                  <div key={player.player_id} className="training-fatigue-row">
                    <span>{player.player_name}</span>
                    <div>
                      <i style={{ width: `${clampPercent(player.fatigue)}%` }} />
                    </div>
                    <strong className={player.fatigue > 70 ? 'is-danger' : player.fatigue > 45 ? 'is-warn' : ''}>{player.fatigue}</strong>
                  </div>
                ))}
              </div>
            )}
          </section>
        </aside>
      </main>
    </div>
  )
}

function PreviewMetric({ label, value }: { label: string; value: string | number }) {
  return (
    <div>
      <span>{label}</span>
      <strong>{value}</strong>
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
            <span>{group.name}</span>
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
      <span>{getCategoryLabel(item.category)} · 强度 {INTENSITY_LABELS[item.intensity] || item.intensity}</span>
      <div className="slot-markers">
        {auto && <MoreHorizontal className="h-3 w-3" />}
        {edited && <i />}
      </div>
    </div>
  )
}

function TrainingItemCard({
  item,
  disabled,
  selected,
  onSelect,
}: {
  item: TrainingItem
  disabled: boolean
  selected: boolean
  onSelect: () => void
}) {
  const attrs = getTopAttributes(item, 4)
  const positions = getBestPositions(item).slice(0, 3)

  return (
    <button
      disabled={disabled}
      onClick={onSelect}
      className={`training-item-card tone-${getCategoryTone(item.category)} ${selected ? 'is-selected' : ''}`}
    >
      <div className="training-item-main">
        <strong>{item.name}</strong>
        <span>{getCategoryLabel(item.category)}</span>
      </div>
      <p>{getTrainingEffectDesc(item)}</p>
      <div className="training-attr-row">
        {attrs.map(attr => (
          <span key={attr.label}>{attr.label}</span>
        ))}
      </div>
      <div className="training-numbers">
        <span>强度 {INTENSITY_LABELS[item.intensity] || item.intensity}</span>
        <span className={item.fitness_delta < 0 ? 'is-bad' : 'is-good'}>体能 {item.fitness_delta > 0 ? '+' : ''}{item.fitness_delta}</span>
        <span className={item.fatigue_delta > 0 ? 'is-bad' : 'is-good'}>疲劳 {item.fatigue_delta > 0 ? '+' : ''}{item.fatigue_delta}</span>
        <span>负荷 {item.load_points}</span>
      </div>
      {positions.length > 0 && <em>推荐：{positions.join('、')}</em>}
    </button>
  )
}
