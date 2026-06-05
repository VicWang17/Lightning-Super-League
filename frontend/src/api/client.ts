import { useAuthStore } from '../stores/auth'
import type { Season, SeasonDetail, TodayFixturesResponse, SeasonCalendarResponse } from '../types/season'
import type { PlayerContract, ContractPreview, ContractOffer, PlayerState, TeamPlayerStates } from '../types/player'
import type {
  MarketPlayer,
  TransferListingItem,
  TransferOfferItem,
  PublicOfferItem,
  TransferRecordItem,
  ValuationResponse,
  ListPlayerRequest,
  ListPlayerResponse,
  CreateOfferRequest,
  CounterOfferRequest,
  FinalOfferRequest,
  OfferResponse,
  ReleasePreviewResponse,
  ReleaseResponse,
  AcceptOfferResponse,
} from '../types/transfer'

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

  // PUT helper
  async put<T>(endpoint: string, body: unknown, options: RequestInit = {}) {
    return this.requestWithAuth<T>(endpoint, {
      ...options,
      method: 'PUT',
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

  // ==================== 自由市场 API ====================
  async getFreeMarketList(params?: {
    position?: string
    min_ovr?: number
    max_ovr?: number
    min_age?: number
    max_age?: number
    origin?: string
    page?: number
    page_size?: number
  }) {
    const query = new URLSearchParams()
    if (params?.position) query.append('position', params.position)
    if (params?.min_ovr !== undefined) query.append('min_ovr', String(params.min_ovr))
    if (params?.max_ovr !== undefined) query.append('max_ovr', String(params.max_ovr))
    if (params?.min_age !== undefined) query.append('min_age', String(params.min_age))
    if (params?.max_age !== undefined) query.append('max_age', String(params.max_age))
    if (params?.origin) query.append('origin', params.origin)
    if (params?.page) query.append('page', String(params.page))
    if (params?.page_size) query.append('page_size', String(params.page_size))
    return this.requestWithAuth<{
      items: import('../types/free_market').FreeMarketPlayer[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/free-market?${query.toString()}`, { method: 'GET' })
  }

  async getFreeMarketDetail(listingId: string) {
    return this.requestWithAuth<import('../types/free_market').FreeMarketDetail>(`/free-market/${listingId}`, { method: 'GET' })
  }

  async previewFreeMarketSign(listingId: string, data: import('../types/free_market').FreeMarketSignRequest) {
    return this.post<import('../types/free_market').FreeMarketPreview>(`/free-market/${listingId}/preview`, data)
  }

  async signFreeMarketPlayer(listingId: string, data: import('../types/free_market').FreeMarketSignRequest) {
    return this.post<import('../types/free_market').FreeMarketSignResult>(`/free-market/${listingId}/sign`, data)
  }

  // ==================== 青训 API ====================
  async getYouthAcademy(teamId: string, seasonId?: string) {
    const query = seasonId ? `?season_id=${seasonId}` : ''
    return this.requestWithAuth<{
      team_id: string
      season_id: string
      players: Array<{
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
      }>
      capacity: number
      count: number
    }>(`/teams/${teamId}/youth/academy${query}`, { method: 'GET' })
  }

  async previewYouthSigning(academyPlayerId: string, data: {
    team_id: string
    years: number
    wage: number
    squad_role?: string
  }) {
    return this.post<import('../types/player').ContractPreview>(`/youth/academy/${academyPlayerId}/preview-signing`, data)
  }

  async signYouthPlayer(academyPlayerId: string, data: {
    team_id: string
    years: number
    wage: number
    squad_role?: string
  }) {
    return this.post<{ contract_id: string; player_id: string; team_id: string; signing_fee: number }>(`/youth/academy/${academyPlayerId}/sign`, data)
  }

  async releaseYouthPlayer(academyPlayerId: string) {
    return this.post<{ academy_player_id: string; status: string }>(`/youth/academy/${academyPlayerId}/release`, {})
  }

  async getYouthGrowthCurve(academyPlayerId: string) {
    return this.requestWithAuth<Array<{
      season_day: number
      ovr: number
      extra_data: Record<string, unknown> | null
      created_at: string
    }>>(`/youth/academy/${academyPlayerId}/growth`, { method: 'GET' })
  }

  // ==================== 选秀 API ====================
  // 选秀系统已移除（简化闭环设计）
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

  // ==================== 转会市场 API ====================

  async getTransferMarket(params?: {
    position?: string
    min_ovr?: number
    max_ovr?: number
    min_age?: number
    max_age?: number
    is_listed?: boolean
    page?: number
    page_size?: number
  }) {
    const query = new URLSearchParams()
    if (params?.position) query.append('position', params.position)
    if (params?.min_ovr !== undefined) query.append('min_ovr', String(params.min_ovr))
    if (params?.max_ovr !== undefined) query.append('max_ovr', String(params.max_ovr))
    if (params?.min_age !== undefined) query.append('min_age', String(params.min_age))
    if (params?.max_age !== undefined) query.append('max_age', String(params.max_age))
    if (params?.is_listed !== undefined) query.append('is_listed', String(params.is_listed))
    if (params?.page) query.append('page', String(params.page))
    if (params?.page_size) query.append('page_size', String(params.page_size))
    return this.requestWithAuth<{
      items: MarketPlayer[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/transfers/market?${query.toString()}`, { method: 'GET' })
  }

  async getTransferListings(params?: {
    seller_team_id?: string
    page?: number
    page_size?: number
  }) {
    const query = new URLSearchParams()
    if (params?.seller_team_id) query.append('seller_team_id', params.seller_team_id)
    if (params?.page) query.append('page', String(params.page))
    if (params?.page_size) query.append('page_size', String(params.page_size))
    return this.requestWithAuth<{
      items: TransferListingItem[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/transfers/listings?${query.toString()}`, { method: 'GET' })
  }

  async getPublicOffers(params?: { page?: number; page_size?: number }) {
    const query = new URLSearchParams()
    if (params?.page) query.append('page', String(params.page))
    if (params?.page_size) query.append('page_size', String(params.page_size))
    return this.requestWithAuth<{
      items: PublicOfferItem[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/transfers/offers/public?${query.toString()}`, { method: 'GET' })
  }

  async getReceivedOffers(params: {
    team_id: string
    status?: string
    page?: number
    page_size?: number
  }) {
    const query = new URLSearchParams()
    query.append('team_id', params.team_id)
    if (params.status) query.append('status', params.status)
    if (params.page) query.append('page', String(params.page))
    if (params.page_size) query.append('page_size', String(params.page_size))
    return this.requestWithAuth<{
      items: TransferOfferItem[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/transfers/offers/received?${query.toString()}`, { method: 'GET' })
  }

  async getSentOffers(params: {
    team_id: string
    status?: string
    page?: number
    page_size?: number
  }) {
    const query = new URLSearchParams()
    query.append('team_id', params.team_id)
    if (params.status) query.append('status', params.status)
    if (params.page) query.append('page', String(params.page))
    if (params.page_size) query.append('page_size', String(params.page_size))
    return this.requestWithAuth<{
      items: TransferOfferItem[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/transfers/offers/sent?${query.toString()}`, { method: 'GET' })
  }

  async getTransferHistory(params?: {
    team_id?: string
    player_id?: string
    page?: number
    page_size?: number
  }) {
    const query = new URLSearchParams()
    if (params?.team_id) query.append('team_id', params.team_id)
    if (params?.player_id) query.append('player_id', params.player_id)
    if (params?.page) query.append('page', String(params.page))
    if (params?.page_size) query.append('page_size', String(params.page_size))
    return this.requestWithAuth<{
      items: TransferRecordItem[]
      total: number
      page: number
      page_size: number
      total_pages: number
    }>(`/transfers/history?${query.toString()}`, { method: 'GET' })
  }

  async getPlayerValuation(playerId: string, teamId?: string) {
    const query = teamId ? `?team_id=${teamId}` : ''
    return this.requestWithAuth<ValuationResponse>(`/transfers/players/${playerId}/valuation${query}`, { method: 'POST' })
  }

  async listPlayer(playerId: string, data: ListPlayerRequest) {
    return this.post<ListPlayerResponse>(`/transfers/players/${playerId}/list`, data)
  }

  async cancelListing(listingId: string, teamId: string) {
    return this.post<{ listing_id: string; status: string }>(`/transfers/listings/${listingId}/cancel?team_id=${teamId}`, {})
  }

  async createTransferOffer(data: CreateOfferRequest) {
    return this.post<OfferResponse>('/transfers/offers', data)
  }

  async acceptTransferOffer(offerId: string, actorTeamId: string) {
    return this.post<AcceptOfferResponse>(`/transfers/offers/${offerId}/accept?actor_team_id=${actorTeamId}`, {})
  }

  async rejectTransferOffer(offerId: string, actorTeamId: string) {
    return this.post<{ offer_id: string; status: string }>(`/transfers/offers/${offerId}/reject?actor_team_id=${actorTeamId}`, {})
  }

  async counterTransferOffer(offerId: string, data: CounterOfferRequest) {
    return this.post<OfferResponse>(`/transfers/offers/${offerId}/counter`, data)
  }

  async createFinalOffer(negotiationId: string, data: FinalOfferRequest) {
    return this.post<OfferResponse>(`/transfers/negotiations/${negotiationId}/final-offer`, data)
  }

  async previewRelease(playerId: string, teamId: string) {
    return this.requestWithAuth<ReleasePreviewResponse>(`/transfers/players/${playerId}/release/preview?team_id=${teamId}`, { method: 'POST' })
  }

  async transferReleasePlayer(playerId: string, teamId: string) {
    return this.post<ReleaseResponse>(`/transfers/players/${playerId}/release?team_id=${teamId}`, {})
  }

  async triggerAITransferScan() {
    return this.post<{ scanned: number; responded: number; listed: number; offered: number }>('/transfers/admin/ai-scan', {})
  }

  // ==================== 训练系统 API ====================

  async getTrainingItems(category?: string) {
    const query = category ? `?category=${category}` : ''
    return this.requestWithAuth<{
      items: import('../types/training').TrainingItem[]
    }>(`/training/items${query}`, { method: 'GET' })
  }

  async getTrainingTemplates() {
    return this.requestWithAuth<{
      items: import('../types/training').TrainingTemplate[]
    }>('/training/templates', { method: 'GET' })
  }

  async getTeamTrainingPlan(teamId: string, seasonId: string, startDay: number, days = 7) {
    return this.requestWithAuth<{
      items: import('../types/training').TrainingPlanSlot[]
    }>(`/training/teams/${teamId}/plan?season_id=${seasonId}&start_day=${startDay}&days=${days}`, { method: 'GET' })
  }

  async saveTeamTrainingPlan(teamId: string, seasonId: string, items: Array<{
    season_day: number
    slot: string
    mode: string
    training_item_id?: string
    groups?: import('../types/training').TrainingGroup[]
  }>) {
    return this.requestWithAuth<{
      items: import('../types/training').TrainingPlanSlot[]
    }>(`/training/teams/${teamId}/plan`, {
      method: 'PUT',
      body: JSON.stringify({ season_id: seasonId, items }),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async applyTrainingTemplate(teamId: string, templateId: string, seasonId: string, startDay: number) {
    return this.requestWithAuth<{
      items: import('../types/training').TrainingPlanSlot[]
    }>(`/training/teams/${teamId}/templates/${templateId}/apply`, {
      method: 'POST',
      body: JSON.stringify({ season_id: seasonId, start_day: startDay }),
      headers: { 'Content-Type': 'application/json' },
    })
  }

  async autoGroupPlayers(teamId: string, mode = 'groups_3') {
    return this.requestWithAuth<import('../types/training').AutoGroupResponse>(
      `/training/teams/${teamId}/auto-group?mode=${mode}`,
      { method: 'POST' }
    )
  }

  async completeTrainingSlot(teamId: string, seasonId: string, seasonDay: number, slot: string) {
    return this.requestWithAuth<import('../types/training').TrainingDailySummary>(
      `/training/teams/${teamId}/plan/complete?season_id=${seasonId}&season_day=${seasonDay}&slot=${slot}`,
      { method: 'POST' }
    )
  }

  async getTrainingResults(teamId: string, seasonId: string, params?: {
    player_id?: string
    start_day?: number
    days?: number
    limit?: number
  }) {
    const query = new URLSearchParams()
    query.append('season_id', seasonId)
    if (params?.player_id) query.append('player_id', params.player_id)
    if (params?.start_day !== undefined) query.append('start_day', String(params.start_day))
    if (params?.days !== undefined) query.append('days', String(params.days))
    if (params?.limit !== undefined) query.append('limit', String(params.limit))
    return this.requestWithAuth<{
      items: import('../types/training').TrainingResultItem[]
    }>(`/training/teams/${teamId}/results?${query.toString()}`, { method: 'GET' })
  }

  async getPlayerFatigue(playerId: string) {
    return this.requestWithAuth<import('../types/training').PlayerFatigueItem>(
      `/training/players/${playerId}/fatigue`,
      { method: 'GET' }
    )
  }

  async getTeamFatigue(teamId: string) {
    return this.requestWithAuth<import('../types/training').TeamFatigueResponse>(
      `/training/teams/${teamId}/fatigue`,
      { method: 'GET' }
    )
  }

  async getPlayerTrainingProgress(playerId: string, seasonId: string, days = 7) {
    return this.requestWithAuth<import('../types/training').PlayerTrainingProgress>(
      `/training/players/${playerId}/training/progress?season_id=${seasonId}&days=${days}`,
      { method: 'GET' }
    )
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
