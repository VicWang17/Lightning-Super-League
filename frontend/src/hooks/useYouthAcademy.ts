import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'

export interface AcademyPlayer {
  academy_player_id: string
  player_id: string
  name: string
  race: string
  avatar_url?: string
  position: string
  age: number
  ovr: number
  potential_letter: string
  growth_speed: string
  joined_day: number
  last_trained_day: number | null
}

export interface YouthAcademyData {
  team_id: string
  season_id: string
  players: AcademyPlayer[]
  capacity: number
  count: number
}

export interface BudgetPlan {
  team_id: string
  season_id: string
  policy: string
  transfer_pct: number
  youth_pct: number
  wage_pct: number
  reserve_pct: number
  is_player_confirmed: boolean
  locked_at: string | null
}

const ROSTER_MAX = 18

export function useYouthAcademy() {
  const [data, setData] = useState<YouthAcademyData | null>(null)
  const [budget, setBudget] = useState<BudgetPlan | null>(null)
  const [rosterCount, setRosterCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetch = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const teamRes = await api.get<{ id: string; current_season_id?: string }>('/teams/my-team')
      if (!teamRes.success || !teamRes.data) {
        setError('无法获取球队信息')
        return
      }

      const teamId = teamRes.data.id
      const seasonId = teamRes.data.current_season_id

      const [academyRes, budgetRes, playersRes] = await Promise.all([
        api.getYouthAcademy(teamId),
        seasonId ? api.getBudgetPlan(teamId, seasonId) : Promise.resolve({ success: false, data: null } as any),
        api.get<{ items: unknown[]; total: number }>(`/teams/${teamId}/players?page_size=1`),
      ])

      if (academyRes.success && academyRes.data) {
        setData(academyRes.data)
      }

      if (budgetRes.success && budgetRes.data) {
        setBudget(budgetRes.data)
      }

      if (playersRes.success && playersRes.data) {
        setRosterCount(playersRes.data.total)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取青训数据失败')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetch()
  }, [fetch])

  const rosterFull = rosterCount >= ROSTER_MAX

  return {
    data,
    budget,
    rosterCount,
    rosterFull,
    loading,
    error,
    refetch: fetch,
  }
}
