import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export interface User {
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

export interface TokenData {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface UserWithToken extends User {
  token: TokenData
}

interface AuthState {
  // 状态
  user: User | null
  token: string | null
  refreshToken: string | null
  isAuthenticated: boolean
  isLoading: boolean
  
  // Actions
  setUser: (user: UserWithToken) => void
  logout: () => void
  setLoading: (loading: boolean) => void
  getToken: () => string | null
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // 初始状态
      user: null,
      token: null,
      refreshToken: null,
      isAuthenticated: false,
      isLoading: false,
      
      // Actions
      setUser: (userWithToken: UserWithToken) => {
        const { token, ...user } = userWithToken
        set({
          user,
          token: token.access_token,
          refreshToken: token.refresh_token,
          isAuthenticated: true,
        })
      },
      
      logout: () => {
        set({
          user: null,
          token: null,
          refreshToken: null,
          isAuthenticated: false,
        })
      },
      
      setLoading: (loading: boolean) => {
        set({ isLoading: loading })
      },
      
      getToken: () => {
        return get().token
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        token: state.token,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
)

// 导出便捷 hooks
export const useIsAuthenticated = () => useAuthStore((state) => state.isAuthenticated)
export const useCurrentUser = () => useAuthStore((state) => state.user)
export const useAuthToken = () => useAuthStore((state) => state.token)
