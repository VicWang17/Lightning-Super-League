import { useState, useEffect, useCallback } from 'react'
import { api } from '../api/client'
import type { PlayerAward, PlayerAwardSummary, SeasonAwards, LeagueAwards, CupAwards } from '../types/awards'

// ===== 球员荣誉 =====
export function usePlayerAwards(playerId: string | undefined) {
  const [awards, setAwards] = useState<PlayerAward[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!playerId) return
    setLoading(true)
    api.getPlayerAwards(playerId)
      .then((response) => {
        if (response.success && response.data) {
          setAwards(response.data)
        }
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [playerId])

  return { awards, loading, error }
}

export function usePlayerAwardSummary(playerId: string | undefined) {
  const [summary, setSummary] = useState<PlayerAwardSummary | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!playerId) return
    setLoading(true)
    api.getPlayerAwardSummary(playerId)
      .then((response) => {
        if (response.success && response.data) {
          setSummary(response.data)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [playerId])

  return { summary, loading }
}

// ===== 赛季大奖 =====
export function useSeasonAwards(seasonId: string | undefined) {
  const [awards, setAwards] = useState<SeasonAwards | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchAwards = useCallback(async () => {
    if (!seasonId) return
    setLoading(true)
    try {
      const response = await api.getSeasonAwards(seasonId)
      if (response.success && response.data) {
        setAwards(response.data)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [seasonId])

  useEffect(() => {
    fetchAwards()
  }, [fetchAwards])

  return { awards, loading, refetch: fetchAwards }
}

export function useAllLeagueAwardsForSeason(seasonId: string | undefined) {
  const [leagueAwards, setLeagueAwards] = useState<LeagueAwards[]>([])
  const [loading, setLoading] = useState(false)

  const fetchAwards = useCallback(async () => {
    if (!seasonId) return
    setLoading(true)
    try {
      const response = await api.getAllLeagueAwardsForSeason(seasonId)
      if (response.success && response.data) {
        setLeagueAwards(response.data)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [seasonId])

  useEffect(() => {
    fetchAwards()
  }, [fetchAwards])

  return { leagueAwards, loading, refetch: fetchAwards }
}

export function useLeagueAwards(leagueId: string | undefined, seasonId: string | undefined) {
  const [awards, setAwards] = useState<LeagueAwards | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchAwards = useCallback(async () => {
    if (!leagueId || !seasonId) return
    setLoading(true)
    try {
      const response = await api.getLeagueAwards(leagueId, seasonId)
      if (response.success && response.data) {
        setAwards(response.data)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [leagueId, seasonId])

  useEffect(() => {
    fetchAwards()
  }, [fetchAwards])

  return { awards, loading, refetch: fetchAwards }
}

export function useCupAwards(cupId: string | undefined, seasonId: string | undefined) {
  const [awards, setAwards] = useState<CupAwards | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchAwards = useCallback(async () => {
    if (!cupId || !seasonId) return
    setLoading(true)
    try {
      const response = await api.getCupAwards(cupId, seasonId)
      if (response.success && response.data) {
        setAwards(response.data)
      }
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [cupId, seasonId])

  useEffect(() => {
    fetchAwards()
  }, [fetchAwards])

  return { awards, loading, refetch: fetchAwards }
}
