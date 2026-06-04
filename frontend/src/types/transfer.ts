// Transfer Market types - PRD v5 转会市场

export type TransferListingStatus = 'ACTIVE' | 'SOLD' | 'EXPIRED' | 'CANCELLED'
export type NegotiationStatus = 'ACTIVE' | 'ACCEPTED' | 'REJECTED' | 'EXPIRED'
export type OfferStatus = 'PENDING' | 'ACCEPTED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED'
export type OfferKind = 'INITIAL' | 'COUNTER' | 'FINAL'
export type TransferType = 'TRANSFER' | 'RELEASE' | 'FREE_AGENT'

// =====================================================================
// Market Browse
// =====================================================================

export interface MarketPlayer {
  player_id: string
  name: string
  position: string
  age: number
  ovr: number
  potential_letter: string
  market_value: number
  team_id: string
  team_name: string
  is_listed: boolean
  list_price: number | null
  listing_id: string | null
}

export interface TransferListingItem {
  listing_id: string
  player_id: string
  name: string
  position: string
  ovr: number
  age: number
  list_price: number
  market_value: number
  seller_team_id: string
  deadline: string | null
}

// =====================================================================
// Offers
// =====================================================================

export interface TransferOfferItem {
  offer_id: string
  negotiation_id: string
  player_id: string
  player_name: string
  amount: number
  offer_kind: OfferKind
  status: OfferStatus
  buyer_team_id: string
  seller_team_id: string
  expires_at: string
  can_counter?: boolean
}

export interface PublicOfferItem {
  offer_id: string
  player_id: string
  player_name: string
  position: string
  ovr: number
  buyer_team_id: string
  seller_team_id: string
  amount: number
  market_value: number
  offer_kind: OfferKind
  status: OfferStatus
  created_at: string
  expires_at: string
}

// =====================================================================
// History
// =====================================================================

export interface TransferRecordItem {
  record_id: string
  player_id: string
  player_name: string
  from_team_id: string
  to_team_id: string
  transfer_type: TransferType
  amount: number
  market_value: number
  completed_at: string
}

// =====================================================================
// Valuation & Listing
// =====================================================================

export interface ValuationResponse {
  player_id: string
  market_value: number
  age: number
  ovr: number
  potential_letter: string
}

export interface ListPlayerRequest {
  team_id: string
  list_price: number
}

export interface ListPlayerResponse {
  listing_id: string
  player_id: string
  list_price: number
  deadline: string | null
}

// =====================================================================
// Offer Requests
// =====================================================================

export interface CreateOfferRequest {
  player_id: string
  buyer_team_id: string
  amount: number
  listing_id?: string
}

export interface CounterOfferRequest {
  seller_team_id: string
  amount: number
}

export interface FinalOfferRequest {
  buyer_team_id: string
  amount: number
}

export interface OfferResponse {
  offer_id: string
  negotiation_id: string
  amount: number
  expires_at: string
}

// =====================================================================
// Release
// =====================================================================

export interface ReleasePreviewResponse {
  player_id: string
  player_name: string
  unpaid_wages: number
  base_penalty: number
  min_penalty: number
  final_penalty: number
  balance: number
  can_release: boolean
  reason: string
}

export interface ReleaseResponse {
  record_id: string
  transfer_type: TransferType
  amount: number
}

// =====================================================================
// Accept/Record
// =====================================================================

export interface AcceptOfferResponse {
  record_id: string
  transfer_type: TransferType
  amount: number
}

// =====================================================================
// Status helpers
// =====================================================================

export const OFFER_STATUS_NAMES: Record<OfferStatus, string> = {
  PENDING: '待响应',
  ACCEPTED: '已接受',
  REJECTED: '已拒绝',
  EXPIRED: '已过期',
  CANCELLED: '已取消',
}

export const OFFER_KIND_NAMES: Record<OfferKind, string> = {
  INITIAL: '初始报价',
  COUNTER: '反报价',
  FINAL: '最终报价',
}

export const TRANSFER_TYPE_NAMES: Record<TransferType, string> = {
  TRANSFER: '队间转会',
  RELEASE: '解约',
  FREE_AGENT: '自由签约',
}

export const LISTING_STATUS_NAMES: Record<TransferListingStatus, string> = {
  ACTIVE: '挂牌中',
  SOLD: '已成交',
  EXPIRED: '已过期',
  CANCELLED: '已取消',
}
