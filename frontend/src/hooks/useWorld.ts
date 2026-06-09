import { useState, useEffect } from 'react'
import { api } from '../api/client'
import type { WorldRanking, TopPlayer } from '../types/world'
import type { RecordsByCategory } from '../types/records'

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
        const response = await api.get<TopPlayer[]>(url)
        if (response.success) {
          setPlayers(response.data)
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
