import { useAuthStore } from '../stores/auth'
import type { Season, SeasonDetail, TodayFixturesResponse, SeasonCalendarResponse } from '../types/season'
import type { PlayerContract, ContractPreview, ContractOffer, PlayerState, TeamPlayerStates } from '../types/player'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'

interface ApiResponse<T = unknown> {
  success: boolean
  message: string
  data: T
}

interface LoginCredentials {
  username: string
  password: string
}

class ApiClient {
  private baseUrl: string
  private isRefreshing = false
  private refreshPromise: Promise<boolean> | null = null

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl
  }

  private async requestWithAuth<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    
    // 获取当前 token
    const token = useAuthStore.getState().token
    
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      ...((options.method === 'POST' || options.method === 'PUT') && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/x-www-form-urlencoded' }
        : {}),
      ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
      ...((options.headers as Record<string, string>) || {}),
    }

    const config: RequestInit = {
      ...options,
      headers,
    }

    const response = await fetch(url, config)
    const data = await response.json()

    // 处理 401 错误 - token 过期
    if (response.status === 401) {
      console.log(`[API] 401 Unauthorized for ${endpoint}, attempting token refresh...`)
      
      // 尝试刷新 token
      const refreshed = await this.tryRefreshToken()
      
      if (refreshed) {
        // 刷新成功，使用新 token 重试原请求
        console.log(`[API] Token refreshed, retrying ${endpoint}...`)
        return this.retryRequest<T>(endpoint, options)
      } else {
        // 刷新失败，跳转到登录页
        console.log('[API] Token refresh failed, redirecting to login...')
        this.redirectToLogin()
        throw new Error('登录已过期，请重新登录')
      }
    }

    if (!response.ok) {
      throw new Error(data.detail || data.message || '请求失败')
    }

    return data
  }

  // 使用新 token 重试请求
  private async retryRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<ApiResponse<T>> {
    const url = `${this.baseUrl}${endpoint}`
    const newToken = useAuthStore.getState().token
    
    const headers: Record<string, string> = {
      'Accept': 'application/json',
      ...((options.method === 'POST' || options.method === 'PUT') && !(options.body instanceof FormData)
        ? { 'Content-Type': 'application/x-www-form-urlencoded' }
        : {}),
      ...(newToken ? { 'Authorization': `Bearer ${newToken}` } : {}),
      ...((options.headers as Record<string, string>) || {}),
    }

    const response = await fetch(url, {
      ...options,
      headers,
    })
    
    const data = await response.json()
    
    if (!response.ok) {
      throw new Error(data.detail || data.message || '请求失败')
    }

    return data
  }

  // 尝试刷新 token（带锁，防止并发刷新）
  private async tryRefreshToken(): Promise<boolean> {
    // 如果正在刷新，等待当前刷新完成
    if (this.isRefreshing && this.refreshPromise) {
      console.log('[API] Waiting for existing token refresh...')
      return this.refreshPromise
    }

    // 开始新的刷新流程
    this.isRefreshing = true
    this.refreshPromise = this.doRefreshToken()

    try {
      const result = await this.refreshPromise
      return result
    } finally {
      this.isRefreshing = false
      this.refreshPromise = null
    }
  }

  // 执行实际的 token 刷新
  private async doRefreshToken(): Promise<boolean> {
    const refreshToken = useAuthStore.getState().refreshToken
    
    if (!refreshToken) {
      console.log('[API] No refresh token available')
      return false
    }

    try {
      console.log('[API] Refreshing token...')
      
      const response = await fetch(`${this.baseUrl}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })

      if (!response.ok) {
        console.log('[API] Token refresh failed:', response.status)
        return false
      }

      const data = await response.json()
      
      if (!data.success || !data.data) {
        console.log('[API] Token refresh failed:', data.message)
        return false
      }

      // 更新 store 中的 token
      const tokenData = data.data
      useAuthStore.getState().setToken(tokenData)
      
      console.log('[API] Token refreshed successfully')
      return true
      
    } catch (error) {
      console.error('[API] Token refresh error:', error)
      return false
    }
  }

  // 跳转到登录页
  private redirectToLogin() {
    // 清除登录状态
    useAuthStore.getState().logout()
    
    // 跳转到登录页（保留当前路径，登录后可以返回）
    const currentPath = window.location.pathname
    if (currentPath !== '/login') {
      window.location.href = `/login?redirect=${encodeURIComponent(currentPath)}`
    }
  }

  // Auth API
  async login(credentials: LoginCredentials) {
    const formData = new URLSearchParams()
    formData.append('username', credentials.username)
    formData.append('password', credentials.password)

    const url = `${this.baseUrl}/auth/login`
    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.detail || data.message || '登录失败')
    }

    return data
  }

  async logout() {
    return this.requestWithAuth<void>('/auth/logout', {
      method: 'POST',
    })
  }

  async getCurrentUser() {
    return this.requestWithAuth<User>('/auth/me', {
      method: 'GET',
    })
  }

  async refreshToken(refreshToken: string) {
    return this.requestWithAuth<TokenData>('/auth/refresh', {
      method: 'POST',
      body: JSON.stringify({ refresh_token: refreshToken }),
      headers: {
        'Content-Type': 'application/json',
      },
    })
  }

  // GET helper
  async get<T>(endpoint: string, options: RequestInit = {}) {
    return this.requestWithAuth<T>(endpoint, { ...options, method: 'GET' })
  }

  // POST helper
  async post<T>(endpoint: string, body: unknown, options: RequestInit = {}) {
    return this.requestWithAuth<T>(endpoint, {
      ...options,
      method: 'POST',
      body: JSON.stringify(body),
      headers: {
        'Content-Type': 'application/json',
        ...((options.headers as Record<string, string>) || {}),
      },
    })
  }

  // ==================== 赛季 API ====================
  
  async getSeasons() {
    return this.requestWithAuth<Season[]>('/seasons', { method: 'GET' })
  }

  async getCurrentSeason() {
    return this.requestWithAuth<SeasonDetail>('/seasons/current', { method: 'GET' })
  }

  async getSeasonByNumber(seasonNumber: number) {
    return this.requestWithAuth<SeasonDetail>(`/seasons/${seasonNumber}`, { method: 'GET' })
  }

  async createSeason(startDate?: string) {
    return this.requestWithAuth<Season>('/seasons', {
      method: 'POST',
      body: startDate ? JSON.stringify({ start_date: startDate }) : undefined,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async startSeason(seasonNumber: number) {
    return this.requestWithAuth<Season>(`/seasons/${seasonNumber}/start`, { method: 'POST' })
  }

  async processNextDay(seasonNumber: number) {
    return this.requestWithAuth<{
      season_number: number
      current_day: number
      status: string
      fixtures_processed: number
      results: unknown[]
    }>(`/seasons/${seasonNumber}/next-day`, { method: 'POST' })
  }

  async getTodayFixtures(seasonNumber: number) {
    return this.requestWithAuth<TodayFixturesResponse>(`/seasons/${seasonNumber}/today`, { method: 'GET' })
  }

  async getSeasonCalendar(seasonNumber: number, teamId?: string) {
    const query = teamId ? `?team_id=${teamId}` : ''
    return this.requestWithAuth<SeasonCalendarResponse>(`/seasons/${seasonNumber}/calendar${query}`, { method: 'GET' })
  }

  async getTeamFixtures(seasonNumber: number, teamId: string, fixtureType?: string) {
    const query = fixtureType ? `?fixture_type=${fixtureType}` : ''
    return this.requestWithAuth<{ season_number: number; team_id: string; fixtures: unknown[] }>(
      `/seasons/${seasonNumber}/teams/${teamId}/fixtures${query}`,
      { method: 'GET' }
    )
  }

  // ==================== 邮件 API ====================
  async getMails(params?: { category?: string; is_read?: boolean; limit?: number; offset?: number }) {
    const query = new URLSearchParams()
    if (params?.category) query.append('category', params.category)
    if (params?.is_read !== undefined) query.append('is_read', String(params.is_read))
    if (params?.limit) query.append('limit', String(params.limit))
    if (params?.offset !== undefined) query.append('offset', String(params.offset))
    return this.requestWithAuth<{
      items: import('../types/mail').MailItem[]
      total: number
      unread_count: number
      category_counts: Record<string, number>
    }>(`/mail?${query.toString()}`, { method: 'GET' })
  }

  async getMailDetail(mailId: string) {
    return this.requestWithAuth<import('../types/mail').MailDetail>(`/mail/${mailId}`, { method: 'GET' })
  }

  async getUnreadCount() {
    return this.requestWithAuth<{ total: number; by_category: Record<string, number> }>('/mail/unread-count', { method: 'GET' })
  }

  async markMailsRead(mailIds: string[]) {
    return this.post<void>('/mail/read', { mail_ids: mailIds })
  }

  async markAllMailsRead(category?: string) {
    const query = category ? `?category=${category}` : ''
    return this.requestWithAuth<void>(`/mail/read-all${query}`, { method: 'POST' })
  }

  // ==================== 财务 API ====================
  async getFinanceOverview(teamId: string, seasonId?: string) {
    const query = seasonId ? `?season_id=${seasonId}` : ''
    return this.requestWithAuth<{
      team_id: string
      season_id: string
      current_balance: number
      opening_balance: number
      projected_income: number
      projected_expense: number
      locked_budget_total: number
      transfer_budget: number
      youth_budget: number
      wage_budget: number
      reserve_budget: number
      total_income: number
      total_expense: number
      income_breakdown: {
        broadcast: number
        sponsor: number
        match_bonus: number
        cup_prize: number
        league_prize: number
        other: number
      }
      expense_breakdown: {
        wage: number
        youth: number
        transfer: number
        penalty: number
        other: number
      }
      wage_cap_info: {
        wage_cap: number
        wage_bill: number
        wage_pressure_pct: number
        status: string
      }
      financial_health: string
      overspend_level: string
      budget_locked: boolean
      budget_locked_at: string | null
      budget_plan: {
        team_id: string
        target_season_id: string
        policy: string
        transfer_pct: number
        youth_pct: number
        wage_pct: number
        reserve_pct: number
        is_player_confirmed: boolean
        locked_at: string | null
      } | null
      sponsor_contract: {
        team_id: string
        season_id: string
        policy: string
        base_amount: number
        win_bonus: number
        draw_bonus: number
        max_bonus: number
        health_modifier_pct: number
        status: string
      } | null
    }>(`/teams/${teamId}/finance/overview${query}`, { method: 'GET' })
  }

  async getFinanceTransactions(teamId: string, params?: {
    season_id?: string
    source_type?: string
    direction?: string
    page?: number
    page_size?: number
  }) {
    const query = new URLSearchParams()
    if (params?.season_id) query.append('season_id', params.season_id)
    if (params?.source_type) query.append('source_type', params.source_type)
    if (params?.direction) query.append('direction', params.direction)
    if (params?.page) query.append('page', String(params.page))
    if (params?.page_size) query.append('page_size', String(params.page_size))
    return this.requestWithAuth<{
      items: Array<{
        id: string
        team_id: string
        season_id: string
        source_type: string
        direction: string
        amount: number
        balance_after: number
        description: string
        extra_data: Record<string, unknown> | null
        created_at: string
      }>
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/teams/${teamId}/finance/transactions?${query.toString()}`, { method: 'GET' })
  }

  // ==================== 预算与赞助商 API ====================
  async getBudgetPlan(teamId: string, targetSeasonId: string) {
    return this.requestWithAuth<{
      team_id: string
      target_season_id: string
      policy: string
      transfer_pct: number
      youth_pct: number
      wage_pct: number
      reserve_pct: number
      is_player_confirmed: boolean
      locked_at: string | null
    }>(`/teams/${teamId}/finance/budget-plan?target_season_id=${targetSeasonId}`, { method: 'GET' })
  }

  async confirmBudgetPlan(
    teamId: string,
    targetSeasonId: string,
    policy: string,
    transferPct: number,
    youthPct: number,
    wagePct: number,
    reservePct: number
  ) {
    return this.requestWithAuth<{
      team_id: string
      target_season_id: string
      policy: string
      transfer_pct: number
      youth_pct: number
      wage_pct: number
      reserve_pct: number
      is_player_confirmed: boolean
      locked_at: string | null
    }>(`/teams/${teamId}/finance/budget-plan?target_season_id=${targetSeasonId}&policy=${policy}&transfer_pct=${transferPct}&youth_pct=${youthPct}&wage_pct=${wagePct}&reserve_pct=${reservePct}`, { method: 'POST' })
  }

  async getSponsorOptions(teamId: string, seasonId: string) {
    return this.requestWithAuth<Array<{
      policy: string
      label: string
      base_amount: number
      win_bonus: number
      draw_bonus: number
      max_bonus: number
      description: string
    }>>(`/teams/${teamId}/finance/sponsor-options?season_id=${seasonId}`, { method: 'GET' })
  }

  async signSponsorContract(teamId: string, seasonId: string, policy: string) {
    return this.requestWithAuth<{
      team_id: string
      season_id: string
      policy: string
      base_amount: number
      win_bonus: number
      draw_bonus: number
      max_bonus: number
      health_modifier_pct: number
      status: string
    }>(`/teams/${teamId}/finance/sponsor-contract?season_id=${seasonId}&policy=${policy}`, { method: 'POST' })
  }

  async getSponsorContract(teamId: string, seasonId: string) {
    return this.requestWithAuth<{
      team_id: string
      season_id: string
      policy: string
      base_amount: number
      win_bonus: number
      draw_bonus: number
      max_bonus: number
      health_modifier_pct: number
      status: string
    }>(`/teams/${teamId}/finance/sponsor-contract?season_id=${seasonId}`, { method: 'GET' })
  }

  // ==================== 球员合同与状态 API ====================
  async getPlayerContract(playerId: string) {
    return this.get<PlayerContract>(`/players/${playerId}/contract`)
  }

  async previewContract(playerId: string, data: ContractOffer) {
    return this.post<ContractPreview>(`/players/${playerId}/contract/preview`, data)
  }

  async signContract(playerId: string, data: ContractOffer) {
    return this.post<PlayerContract>(`/players/${playerId}/contract/sign`, data)
  }

  async renewContract(playerId: string, data: ContractOffer) {
    return this.post<PlayerContract>(`/players/${playerId}/contract/renew`, data)
  }

  async releasePlayer(playerId: string, teamId: string) {
    return this.post<{ released: boolean }>(`/players/${playerId}/contract/release?team_id=${teamId}`, {})
  }

  async getPlayerState(playerId: string) {
    return this.get<PlayerState>(`/players/${playerId}/state`)
  }

  async getTeamPlayerStates(teamId: string) {
    return this.get<TeamPlayerStates>(`/teams/${teamId}/player-states`)
  }

  // ==================== 时钟 API ====================
  async getClock() {
    // 时钟接口不需要认证
    const url = `${this.baseUrl}/clock`
    const response = await fetch(url, {
      method: 'GET',
      headers: { 'Accept': 'application/json' },
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || data.message || '获取时钟失败')
    }
    return data as {
      success: boolean
      data: {
        mode: string
        virtual_now: string
        speed: number
      }
    }
  }
}

// Types needed for the API client
interface User {
  id: string
  username: string
  email: string
  nickname: string | null
  avatar_url: string | null
  level: number
  experience: number
  is_active: boolean
  is_verified: boolean
  created_at: string
  last_login: string | null
}

interface TokenData {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const api = new ApiClient(API_BASE_URL)
export default api
