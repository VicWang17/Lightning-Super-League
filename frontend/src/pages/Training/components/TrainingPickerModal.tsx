import { useMemo, useState } from 'react'
import { Search, Cancel as X } from '../../../components/ui/pixel-icons'
import { Modal } from '../../../components/ui/Modal'
import type { TrainingItem, PlayerFatigueItem, TrainingMode } from '../../../types/training'
import '../../../styles/training-system.css'

const INTENSITY_LABELS: Record<string, string> = {
  light: '低',
  medium: '中',
  hard: '高',
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

const ATTR_NAMES: Record<string, string> = {
  sho: '射门', pas: '传球', dri: '盘带', spd: '速度', str_: '力量',
  sta: '体能', acc: '加速', hea: '头球', bal: '平衡', defe: '防守',
  tkl: '抢断', vis: '视野', cro: '传中', con: '控球', fin: '终结',
  com: '镇定', sav: '扑救', ref: '反应', pos: '站位', rus: '出击',
  dec: '决策', fk: '任意球', pk: '点球',
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

function getTopAttributes(item: TrainingItem, limit = 5) {
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
    .map(([pos]) => pos)
}

function getTrainingEffectDesc(item: TrainingItem) {
  if (item.is_recovery) return '恢复体能并控制疲劳，适合比赛后或密集赛程。'
  const attrs = getTopAttributes(item, 3).map(attr => attr.label)
  const positions = getBestPositions(item).slice(0, 3)
  return `${attrs.length ? `重点提升 ${attrs.join('、')}` : '综合训练'}${positions.length ? `，适合 ${positions.join('、')}` : ''}。`
}

interface Props {
  isOpen: boolean
  onClose: () => void
  items: TrainingItem[]
  categories: string[]
  onSelect: (itemId: string) => void
  cellMode?: TrainingMode
  activeGroupName?: string | null
  fatigue: PlayerFatigueItem[]
}

export default function TrainingPickerModal({
  isOpen,
  onClose,
  items,
  categories,
  onSelect,
  cellMode,
  activeGroupName,
  fatigue,
}: Props) {
  const [query, setQuery] = useState('')
  const [activeCategory, setActiveCategory] = useState('all')
  const [hoverItem, setHoverItem] = useState<TrainingItem | null>(null)

  const filtered = useMemo(() => {
    let list = activeCategory === 'all' ? items : items.filter(item => item.category === activeCategory)
    if (query.trim()) {
      const q = query.trim().toLowerCase()
      list = list.filter(item => item.name.toLowerCase().includes(q) || getCategoryLabel(item.category).includes(q))
    }
    return list.sort((a, b) => {
      if (a.is_recovery !== b.is_recovery) return a.is_recovery ? 1 : -1
      return a.load_points - b.load_points
    })
  }, [items, activeCategory, query])

  const previewItem = hoverItem || filtered[0] || null

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title="选择训练项目"
      description={cellMode === 'team' ? '为全队选择训练内容' : `为 ${activeGroupName || '当前分组'} 选择训练内容`}
      size="xl"
      showCloseButton
    >
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 340px', gap: 16, minHeight: 420 }}>
        {/* 左侧：搜索 + 筛选 + 列表 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }}>
          {/* 搜索框 */}
          <div style={{ position: 'relative' }}>
            <Search className="h-4 w-4" style={{ position: 'absolute', left: 10, top: '50%', transform: 'translateY(-50%)', color: 'var(--tr-muted)' }} />
            <input
              value={query}
              onChange={e => setQuery(e.target.value)}
              placeholder="搜索训练名称…"
              style={{
                width: '100%',
                border: '2px solid var(--tr-border)',
                background: 'rgba(5,6,9,0.86)',
                padding: '9px 10px 9px 32px',
                color: 'var(--tr-text)',
                fontSize: 13,
                fontWeight: 900,
                outline: 'none',
              }}
            />
            {query && (
              <button
                onClick={() => setQuery('')}
                style={{ position: 'absolute', right: 8, top: '50%', transform: 'translateY(-50%)', color: 'var(--tr-muted)' }}
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>

          {/* 分类筛选 */}
          <div className="training-category-tabs" style={{ marginBottom: 0 }}>
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

          {/* 训练列表 */}
          <div style={{ flex: 1, overflowY: 'auto', display: 'grid', gap: 6, paddingRight: 4 }}>
            {filtered.length === 0 && (
              <div style={{ color: 'var(--tr-muted)', textAlign: 'center', padding: 24, fontSize: 13, fontWeight: 800 }}>
                未找到匹配的训练项目
              </div>
            )}
            {filtered.map(item => {
              const hasConflict = item.fatigue_delta > 5 && fatigue.some(p => p.fatigue > 70)
              return (
                <button
                  key={item.id}
                  onMouseEnter={() => setHoverItem(item)}
                  onClick={() => onSelect(item.id)}
                  className={`training-item-card tone-${getCategoryTone(item.category)}`}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: '1fr auto auto',
                    gap: 8,
                    alignItems: 'center',
                    padding: '8px 10px',
                    textAlign: 'left',
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <strong style={{ fontSize: 14, color: 'var(--tr-text)', fontWeight: 1000 }}>{item.name}</strong>
                      {hasConflict && (
                        <span style={{ color: '#D75A4A', fontSize: 11, fontWeight: 1000 }}>⚠ 高疲劳冲突</span>
                      )}
                    </div>
                    <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                      <span style={{ fontSize: 11, color: 'var(--tr-muted)', fontWeight: 800 }}>
                        {getCategoryLabel(item.category)}
                      </span>
                      <span style={{ fontSize: 11, color: 'var(--tr-muted)', fontWeight: 800 }}>
                        强度 {INTENSITY_LABELS[item.intensity] || item.intensity}
                      </span>
                    </div>
                  </div>
                  <span style={{ fontSize: 11, color: item.fatigue_delta > 0 ? '#D75A4A' : '#9ECF45', fontWeight: 900, whiteSpace: 'nowrap' }}>
                    疲劳 {item.fatigue_delta > 0 ? '+' : ''}{item.fatigue_delta}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--tr-muted)', fontWeight: 900, whiteSpace: 'nowrap', fontFamily: 'Roboto Mono, monospace' }}>
                    负荷 {item.load_points}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* 右侧：悬浮预览 */}
        <div style={{ border: '2px solid var(--tr-border)', background: 'rgba(5,6,9,0.9)', padding: 14, display: 'flex', flexDirection: 'column', gap: 10 }}>
          {previewItem ? (
            <>
              <div className={`training-focus-card tone-${getCategoryTone(previewItem.category)}`} style={{ marginBottom: 0 }}>
                <div className="training-focus-head">
                  <div>
                    <strong>{previewItem.name}</strong>
                    <span>{getCategoryLabel(previewItem.category)} · 强度 {INTENSITY_LABELS[previewItem.intensity] || previewItem.intensity}</span>
                  </div>
                </div>
                <p>{getTrainingEffectDesc(previewItem)}</p>
                <div className="training-focus-bars">
                  {getTopAttributes(previewItem, 5).map(attr => (
                    <div key={attr.label}>
                      <span>{attr.label}</span>
                      <i><b style={{ width: `${Math.min(100, attr.weight * 100)}%` }} /></i>
                    </div>
                  ))}
                </div>
              </div>

              <div className="training-slot-preview">
                <div>
                  <span>训练负荷</span>
                  <strong>{previewItem.load_points}</strong>
                </div>
                <div>
                  <span>疲劳变化</span>
                  <strong style={{ color: previewItem.fatigue_delta > 0 ? '#D75A4A' : '#9ECF45' }}>
                    {previewItem.fatigue_delta > 0 ? '+' : ''}{previewItem.fatigue_delta}
                  </strong>
                </div>
                <div>
                  <span>体能变化</span>
                  <strong style={{ color: previewItem.fitness_delta < 0 ? '#D75A4A' : '#9ECF45' }}>
                    {previewItem.fitness_delta > 0 ? '+' : ''}{previewItem.fitness_delta}
                  </strong>
                </div>
              </div>

              <div style={{ marginTop: 'auto', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
                <button
                  onClick={() => onSelect(previewItem.id)}
                  className="training-save-btn"
                  style={{ justifyContent: 'center' }}
                >
                  选择此项
                </button>
                <button
                  onClick={onClose}
                  className="training-ghost-btn"
                  style={{ justifyContent: 'center' }}
                >
                  取消
                </button>
              </div>
            </>
          ) : (
            <div style={{ color: 'var(--tr-muted)', textAlign: 'center', marginTop: 'auto', marginBottom: 'auto', fontSize: 13, fontWeight: 800 }}>
              将鼠标悬浮在左侧训练项上查看详情
            </div>
          )}
        </div>
      </div>
    </Modal>
  )
}
