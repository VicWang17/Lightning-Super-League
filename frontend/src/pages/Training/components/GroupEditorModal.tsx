import { useState, useMemo, useEffect } from 'react'
import { Dialog } from '@headlessui/react'
import { Cancel as X } from '../../../components/ui/pixel-icons'
import { FatigueStatus } from '../../../components/ui/FatigueStatus'
import type { PlanGroup, PlayerFatigueItem, TrainingMode } from '../../../types/training'

interface Props {
  isOpen: boolean
  onClose: () => void
  groups: PlanGroup[] | null
  fatigue: PlayerFatigueItem[]
  mode: TrainingMode
  onSave: (groups: PlanGroup[]) => void
}

export default function GroupEditorModal({ isOpen, onClose, groups, fatigue, mode, onSave }: Props) {
  const [localGroups, setLocalGroups] = useState<PlanGroup[]>([])

  useEffect(() => {
    if (isOpen && groups && groups.length > 0) {
      setLocalGroups(groups.map(g => ({ ...g, player_ids: [...g.player_ids] })))
    } else if (isOpen) {
      setLocalGroups([])
    }
  }, [isOpen, groups])

  const playerMap = useMemo(() => {
    const map = new Map<string, PlayerFatigueItem>()
    for (const p of fatigue) map.set(p.player_id, p)
    return map
  }, [fatigue])

  const allPlayerIds = useMemo(() => {
    const set = new Set<string>()
    for (const g of localGroups) {
      for (const pid of g.player_ids) set.add(pid)
    }
    return Array.from(set)
  }, [localGroups])

  const findPlayerGroup = (playerId: string) => {
    return localGroups.find(g => g.player_ids.includes(playerId)) || null
  }

  const movePlayer = (playerId: string, fromGroupId: string | null, toGroupId: string) => {
    setLocalGroups(prev => {
      const next = prev.map(g => ({ ...g, player_ids: [...g.player_ids] }))
      if (fromGroupId) {
        const fromGroup = next.find(g => g.group_id === fromGroupId)
        if (fromGroup) {
          fromGroup.player_ids = fromGroup.player_ids.filter(pid => pid !== playerId)
        }
      }
      const toGroup = next.find(g => g.group_id === toGroupId)
      if (toGroup && !toGroup.player_ids.includes(playerId)) {
        toGroup.player_ids.push(playerId)
      }
      return next
    })
  }

  const removePlayer = (playerId: string, groupId: string) => {
    setLocalGroups(prev =>
      prev.map(g =>
        g.group_id === groupId
          ? { ...g, player_ids: g.player_ids.filter(pid => pid !== playerId) }
          : { ...g, player_ids: [...g.player_ids] }
      )
    )
  }

  const getAvailablePlayersForGroup = (groupId: string) => {
    const targetGroup = localGroups.find(g => g.group_id === groupId)
    const targetIds = new Set(targetGroup?.player_ids || [])
    return fatigue.filter(p => !targetIds.has(p.player_id))
  }

  const modeLabel = mode === 'groups_2' ? '双组训练' : mode === 'groups_3' ? '三组专项' : '全队统一'

  function fatigueLabel(fatigue: number) {
    if (fatigue <= 35) return '精神'
    if (fatigue <= 70) return '正常'
    return '疲劳'
  }

  if (!isOpen) return null

  return (
    <Dialog as="div" className="relative z-50" open={isOpen} onClose={onClose}>
      <div className="fixed inset-0 bg-[#1F5F43]/35" style={{ zIndex: 50 }} />
      <div className="fixed inset-0 overflow-y-auto" style={{ zIndex: 50 }}>
        <div className="flex min-h-full items-center justify-center p-4">
          <Dialog.Panel
            style={{
              width: '100%',
              maxWidth: 720,
              background: '#FFFFFF',
              border: '2px solid #1F5F43',
              padding: 24,
              textAlign: 'left',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 16 }}>
              <div>
                <Dialog.Title style={{ color: '#173126', fontSize: 18, fontWeight: 700, margin: 0 }}>
                  调整分组 · {modeLabel}
                </Dialog.Title>
                <Dialog.Description style={{ color: '#466353', fontSize: 13, marginTop: 4 }}>
                  将球员分配到不同训练组，保存后立即生效
                </Dialog.Description>
              </div>
              <button
                onClick={onClose}
                style={{ background: 'none', border: 'none', color: '#466353', cursor: 'pointer', padding: 4 }}
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {localGroups.length === 0 ? (
              <div style={{ color: '#466353', textAlign: 'center', padding: 40, fontSize: 14 }}>
                暂无分组数据，请先切换分组模式
              </div>
            ) : (
              <>
                <div style={{ display: 'grid', gridTemplateColumns: `repeat(${localGroups.length}, minmax(0, 1fr))`, gap: 12 }}>
                  {localGroups.map(group => {
                    const available = getAvailablePlayersForGroup(group.group_id)
                    return (
                      <div
                        key={group.group_id}
                        style={{
                          border: '2px solid rgba(31,95,67,0.25)',
                          background: 'var(--tr-panel)',
                          padding: 12,
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 8,
                          minHeight: 240,
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <strong style={{ color: '#173126', fontSize: 15, fontWeight: 1000 }}>
                            {group.name}
                          </strong>
                          <span style={{ color: '#466353', fontSize: 11, fontWeight: 900 }}>
                            {group.player_ids.length} 人
                          </span>
                        </div>

                        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
                          {group.player_ids.map(pid => {
                            const p = playerMap.get(pid)
                            return (
                              <div
                                key={pid}
                                style={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'space-between',
                                  gap: 8,
                                  padding: '6px 8px',
                                  background: 'rgba(255,255,255,0.6)',
                                  border: '1px solid rgba(31,95,67,0.15)',
                                }}
                              >
                                <div style={{ minWidth: 0, flex: 1 }}>
                                  <div style={{ color: '#173126', fontSize: 13, fontWeight: 800, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                                    {p?.player_name || pid.slice(0, 6)}
                                  </div>
                                  {p && (
                                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}>
                                      <FatigueStatus fatigue={p.fatigue} size={14} />
                                      {!p.can_high_intensity && (
                                        <span style={{ color: '#FF6F59', fontSize: 10, fontWeight: 900 }}>
                                          不宜高强度
                                        </span>
                                      )}
                                    </div>
                                  )}
                                </div>
                                <button
                                  onClick={() => removePlayer(pid, group.group_id)}
                                  style={{ background: 'none', border: 'none', color: '#466353', cursor: 'pointer', padding: 2, flexShrink: 0 }}
                                  title="移出该组"
                                >
                                  <X className="h-3 w-3" />
                                </button>
                              </div>
                            )
                          })}

                          {group.player_ids.length === 0 && (
                            <div style={{ color: '#466353', fontSize: 12, fontWeight: 800, textAlign: 'center', padding: 16 }}>
                              暂无球员
                            </div>
                          )}
                        </div>

                        <div style={{ position: 'relative' }}>
                          <select
                            value=""
                            onChange={e => {
                              if (!e.target.value) return
                              const fromGroup = findPlayerGroup(e.target.value)
                              movePlayer(e.target.value, fromGroup?.group_id || null, group.group_id)
                              e.target.value = ''
                            }}
                            style={{
                              width: '100%',
                              border: '2px solid rgba(31,95,67,0.25)',
                              background: 'var(--tr-panel)',
                              padding: '8px 10px',
                              color: '#173126',
                              fontSize: 12,
                              fontWeight: 1000,
                              cursor: 'pointer',
                              outline: 'none',
                            }}
                          >
                            <option value="">＋ 添加球员到该组</option>
                            {available.map(p => (
                              <option key={p.player_id} value={p.player_id}>
                                {p.player_name}（{fatigueLabel(p.fatigue)}）
                              </option>
                            ))}
                          </select>
                        </div>
                      </div>
                    )
                  })}
                </div>

                {allPlayerIds.length > 0 && (
                  <div style={{ marginTop: 12, padding: 10, background: 'rgba(89,199,238,0.08)', border: '1px solid rgba(89,199,238,0.3)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: '#1F5F43', fontSize: 12, fontWeight: 1000 }}>
                      全队共 {allPlayerIds.length} 名球员已分配
                    </div>
                  </div>
                )}
              </>
            )}

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10, marginTop: 20, borderTop: '2px solid #1F5F43', paddingTop: 16 }}>
              <button
                onClick={onClose}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  border: '2px solid rgba(31,95,67,0.25)',
                  background: '#FFF8DC',
                  padding: '9px 14px',
                  color: '#173126',
                  fontSize: 13,
                  fontWeight: 1000,
                  cursor: 'pointer',
                }}
              >
                取消
              </button>
              <button
                onClick={() => {
                  onSave(localGroups.filter(g => g.player_ids.length > 0))
                  onClose()
                }}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  border: '2px solid rgba(185,239,63,0.45)',
                  background: '#B9EF3F',
                  padding: '9px 14px',
                  color: '#173126',
                  fontSize: 13,
                  fontWeight: 1000,
                  cursor: 'pointer',
                }}
              >
                保存分组
              </button>
            </div>
          </Dialog.Panel>
        </div>
      </div>
    </Dialog>
  )
}
