export enum MailCategory {
  MATCH_PREVIEW = 'match_preview',
  MATCH_RESULT = 'match_result',
  SPONSOR = 'sponsor',
  TRANSFER = 'transfer',
  FINANCE = 'finance',
  SYSTEM = 'system',
}

export enum MailPriority {
  LOW = 'low',
  NORMAL = 'normal',
  HIGH = 'high',
  URGENT = 'urgent',
}

export interface MailItem {
  id: string
  category: MailCategory
  priority: MailPriority
  sender_name: string
  sender_avatar_url?: string
  subject: string
  summary?: string
  is_read: boolean
  read_at?: string
  related_id?: string
  related_type?: string
  related_url?: string
  has_action: boolean
  action_taken: boolean
  action_label?: string
  expires_at?: string
  created_at: string
}

export interface MailDetail extends MailItem {
  body: string
}

export interface MailListResponse {
  items: MailItem[]
  total: number
  unread_count: number
  category_counts: Record<string, number>
}

export interface UnreadCountResponse {
  total: number
  by_category: Record<string, number>
}

export const MAIL_CATEGORY_LABELS: Record<MailCategory, string> = {
  [MailCategory.MATCH_PREVIEW]: '比赛预告',
  [MailCategory.MATCH_RESULT]: '比赛结果',
  [MailCategory.SPONSOR]: '赞助商',
  [MailCategory.TRANSFER]: '转会市场',
  [MailCategory.FINANCE]: '财务中心',
  [MailCategory.SYSTEM]: '系统通知',
}

export const MAIL_CATEGORY_COLORS: Record<MailCategory, string> = {
  [MailCategory.MATCH_PREVIEW]: '#0D7377',
  [MailCategory.MATCH_RESULT]: '#C6F135',
  [MailCategory.SPONSOR]: '#F59E0B',
  [MailCategory.TRANSFER]: '#3B82F6',
  [MailCategory.FINANCE]: '#10B981',
  [MailCategory.SYSTEM]: '#8B8BA7',
}

export const MAIL_CATEGORY_ICONS: Record<MailCategory, string> = {
  [MailCategory.MATCH_PREVIEW]: 'calendar',
  [MailCategory.MATCH_RESULT]: 'trophy',
  [MailCategory.SPONSOR]: 'building',
  [MailCategory.TRANSFER]: 'transfer',
  [MailCategory.FINANCE]: 'wallet',
  [MailCategory.SYSTEM]: 'server',
}
