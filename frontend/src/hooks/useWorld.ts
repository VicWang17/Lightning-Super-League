import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { WorldRanking, TopPlayer } from '../types/world'
import type { RecordsByCategory } from '../types/records'
import type { LeaderboardType, LeaderboardItem } from '../types/leaderboard'

export function useWorldRankings() {
  const [rankings, setRankings] = useState<WorldRanking[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRankings = async () => {
      try {
        setLoading(true)
        const response = await api.get<WorldRanking[]>('/world/rankings')
        if (response.success) {
          setRankings(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取世界排名失败')
      } finally {
        setLoading(false)
      }
    }

    fetchRankings()
  }, [])

  return { rankings, loading, error }
}

export function useTopPlayers(limit = 100, position?: string) {
  const [players, setPlayers] = useState<TopPlayer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchPlayers = async () => {
      try {
        setLoading(true)
        let url = `/world/top-players?limit=${limit}`
        if (position) url += `&position=${position}`
        // 后端 /world/top-players 返回 LeaderboardItem（字段为 value 而非 ovr），
        // 需要在前端映射为 TopPlayer 以兼容现有 PlayerRow 组件。
        const response = await api.get<LeaderboardItem[]>(url)
        if (response.success) {
          const mapped: TopPlayer[] = response.data.map((item) => ({
            rank: item.rank,
            player_id: item.player_id,
            player_name: item.player_name,
            avatar_url: item.avatar_url,
            position: item.position,
            age: item.age ?? 0,
            ovr: item.value,
            team_name: item.team_name,
            team_id: item.team_id,
          }))
          setPlayers(mapped)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取球员排名失败')
      } finally {
        setLoading(false)
      }
    }

    fetchPlayers()
  }, [limit, position])

  return { players, loading, error }
}

export function useWorldRecords() {
  const [records, setRecords] = useState<RecordsByCategory | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchRecords = async () => {
      try {
        setLoading(true)
        const response = await api.get<RecordsByCategory>('/world/records')
        if (response.success) {
          setRecords(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取世界纪录失败')
      } finally {
        setLoading(false)
      }
    }

    fetchRecords()
  }, [])

  return { records, loading, error }
}

export function useWorldLeaderboard(
  type: LeaderboardType,
  limit = 100,
  position?: string
) {
  const [items, setItems] = useState<LeaderboardItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchLeaderboard = async () => {
      try {
        setLoading(true)
        let url = `/world/leaderboard?type=${type}&limit=${limit}`
        if (position) url += `&position=${position}`
        const response = await api.get<LeaderboardItem[]>(url)
        if (response.success) {
          setItems(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取世界排行榜失败')
      } finally {
        setLoading(false)
      }
    }

    fetchLeaderboard()
  }, [type, limit, position])

  return { items, loading, error }
}
