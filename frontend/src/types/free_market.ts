// Free Market types - CONTRACT-YOUTH-CLOSED-LOOP-TECH-DESIGN.md

export type FreeAgentOrigin = 'CONTRACT_EXPIRED' | 'RELEASED' | 'ACADEMY_RELEASED' | 'AUTO_GENERATED'

export interface FreeMarketPlayer {
  listing_id: string
  player_id: string
  name: string
  race: string
  avatar_url?: string
  position: string
  age: number
  ovr: number
  potential_letter: string
  origin: FreeAgentOrigin
  signing_fee: number
  recommended_wage: number
  listed_at_day: number
  growth_speed?: string
  is_rookie_protected?: boolean
}

export interface FreeMarketDetail {
  listing_id: string
  player: {
    id: string
    name: string
    race: string
    avatar_url?: string
    position: string
    age: number
    ovr: number
    potential_letter: string
    abilities: Record<string, number>
    skills: unknown[]
  }
  origin: FreeAgentOrigin
  signing_fee: number
  recommended_wage: number
  listed_at_day: number
  growth_speed?: string
  is_rookie_protected?: boolean
}

export interface FreeMarketPreview {
  recommended_wage: number
  offered_wage: number
  wage_ratio: number
  visible_reaction: string
  hidden_wage_satisfaction: number
  wage_cap_after_pct: number
  can_submit: boolean
  warnings: string[]
  signing_fee: number
  balance_after_fee: number
  can_pay_signing_fee: boolean
}

export interface FreeMarketSignRequest {
  team_id: string
  years: number
  wage: number
  squad_role: string
}

export interface FreeMarketSignResult {
  contract_id: string
  player_id: string
  team_id: string
  signing_fee: number
}

// Origin display names
export const ORIGIN_NAMES: Record<FreeAgentOrigin, string> = {
  CONTRACT_EXPIRED: '合同到期',
  RELEASED: '解约球员',
  ACADEMY_RELEASED: '青训新人',
  AUTO_GENERATED: '系统兜底',
}

export const ORIGIN_COLORS: Record<FreeAgentOrigin, string> = {
  CONTRACT_EXPIRED: 'text-blue-400',
  RELEASED: 'text-red-400',
  ACADEMY_RELEASED: 'text-emerald-400',
  AUTO_GENERATED: 'text-[#8B8BA7]',
}
