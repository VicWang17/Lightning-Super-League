import { useState, useEffect, useCallback } from 'react'
import api from '../api/client'
import type { LeagueSystem, League, LeagueDetail, Match, TopScorer, TopAssist, CleanSheet } from '../types/league'

// 获取所有联赛体系
export function useLeagueSystems() {
  const [systems, setSystems] = useState<LeagueSystem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchSystems = async () => {
      try {
        setLoading(true)
        const response = await api.get<LeagueSystem[]>('/leagues/systems')
        if (response.success) {
          setSystems(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取联赛体系失败')
      } finally {
        setLoading(false)
      }
    }

    fetchSystems()
  }, [])

  return { systems, loading, error }
}

// 获取联赛列表
export function useLeagues(systemId?: string) {
  const [leagues, setLeagues] = useState<League[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchLeagues = async () => {
      try {
        setLoading(true)
        const url = systemId ? `/leagues?system_id=${systemId}` : '/leagues'
        const response = await api.get<League[]>(url)
        if (response.success) {
          setLeagues(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取联赛列表失败')
      } finally {
        setLoading(false)
      }
    }

    fetchLeagues()
  }, [systemId])

  return { leagues, loading, error }
}

// 获取联赛详情
export function useLeagueDetail(leagueId: string | undefined) {
  const [league, setLeague] = useState<LeagueDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!leagueId) {
      setLoading(false)
      return
    }

    const fetchLeague = async () => {
      try {
        setLoading(true)
        const response = await api.get<LeagueDetail>(`/leagues/${leagueId}`)
        if (response.success) {
          setLeague(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取联赛详情失败')
      } finally {
        setLoading(false)
      }
    }

    fetchLeague()
  }, [leagueId])

  return { league, loading, error }
}

// 获取积分榜
export function useLeagueTable(leagueId: string | undefined) {
  const [standings, setStandings] = useState<LeagueDetail['standings']>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchStandings = useCallback(async () => {
    if (!leagueId) return

    try {
      setLoading(true)
      const response = await api.get<LeagueDetail['standings']>(`/leagues/${leagueId}/table`)
      if (response.success) {
        setStandings(response.data)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '获取积分榜失败')
    } finally {
      setLoading(false)
    }
  }, [leagueId])

  useEffect(() => {
    fetchStandings()
  }, [fetchStandings])

  return { standings, loading, error, refetch: fetchStandings }
}

// 获取赛程
export function useLeagueSchedule(leagueId: string | undefined, matchday?: number) {
  const [matches, setMatches] = useState<Match[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!leagueId) {
      setLoading(false)
      return
    }

    const fetchSchedule = async () => {
      try {
        setLoading(true)
        let url = `/leagues/${leagueId}/schedule`
        if (matchday) url += `?matchday=${matchday}`
        const response = await api.get<Match[]>(url)
        if (response.success) {
          setMatches(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取赛程失败')
      } finally {
        setLoading(false)
      }
    }

    fetchSchedule()
  }, [leagueId, matchday])

  return { matches, loading, error }
}

// 获取射手榜
export function useTopScorers(leagueId: string | undefined, limit = 20) {
  const [scorers, setScorers] = useState<TopScorer[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!leagueId) {
      setLoading(false)
      return
    }

    const fetchScorers = async () => {
      try {
        setLoading(true)
        const response = await api.get<TopScorer[]>(`/leagues/${leagueId}/top-scorers?limit=${limit}`)
        if (response.success) {
          setScorers(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取射手榜失败')
      } finally {
        setLoading(false)
      }
    }

    fetchScorers()
  }, [leagueId, limit])

  return { scorers, loading, error }
}

// 获取助攻榜
export function useTopAssists(leagueId: string | undefined, limit = 20) {
  const [assists, setAssists] = useState<TopAssist[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!leagueId) {
      setLoading(false)
      return
    }

    const fetchAssists = async () => {
      try {
        setLoading(true)
        const response = await api.get<TopAssist[]>(`/leagues/${leagueId}/top-assists?limit=${limit}`)
        if (response.success) {
          setAssists(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取助攻榜失败')
      } finally {
        setLoading(false)
      }
    }

    fetchAssists()
  }, [leagueId, limit])

  return { assists, loading, error }
}

// 获取零封榜
export function useCleanSheets(leagueId: string | undefined, limit = 20) {
  const [cleanSheets, setCleanSheets] = useState<CleanSheet[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!leagueId) {
      setLoading(false)
      return
    }

    const fetchCleanSheets = async () => {
      try {
        setLoading(true)
        const response = await api.get<CleanSheet[]>(`/leagues/${leagueId}/clean-sheets?limit=${limit}`)
        if (response.success) {
          setCleanSheets(response.data)
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : '获取零封榜失败')
      } finally {
        setLoading(false)
      }
    }

    fetchCleanSheets()
  }, [leagueId, limit])

  return { cleanSheets, loading, error }
}
