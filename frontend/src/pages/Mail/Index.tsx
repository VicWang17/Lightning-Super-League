import { useEffect, useState, useCallback } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Mail as MailIcon,
  Check,
  ChevronRight,
  SquareAlert,
  ArrowBigUp,
  Cancel,
} from '../../components/ui/pixel-icons'
import { api } from '../../api/client'
import {
  type MailItem,
  type MailDetail,
  type MailListResponse,
  MailCategory,
  MAIL_CATEGORY_LABELS,
  MAIL_CATEGORY_COLORS,
} from '../../types/mail'

const CATEGORY_CONFIG: {
  key: MailCategory | 'all'
  label: string
}[] = [
  { key: 'all', label: '全部邮件' },
  { key: MailCategory.MATCH_PREVIEW, label: MAIL_CATEGORY_LABELS[MailCategory.MATCH_PREVIEW] },
  { key: MailCategory.MATCH_RESULT, label: MAIL_CATEGORY_LABELS[MailCategory.MATCH_RESULT] },
  { key: MailCategory.SPONSOR, label: MAIL_CATEGORY_LABELS[MailCategory.SPONSOR] },
  { key: MailCategory.TRANSFER, label: MAIL_CATEGORY_LABELS[MailCategory.TRANSFER] },
  { key: MailCategory.FINANCE, label: MAIL_CATEGORY_LABELS[MailCategory.FINANCE] },
  { key: MailCategory.SYSTEM, label: MAIL_CATEGORY_LABELS[MailCategory.SYSTEM] },
]

function CategoryBadge({ category }: { category: MailCategory }) {
  return (
    <span
      className="inline-flex items-center px-1.5 py-0.5 text-[10px] font-bold border"
      style={{
        color: MAIL_CATEGORY_COLORS[category],
        borderColor: `${MAIL_CATEGORY_COLORS[category]}40`,
        backgroundColor: `${MAIL_CATEGORY_COLORS[category]}15`,
      }}
    >
      {MAIL_CATEGORY_LABELS[category]}
    </span>
  )
}

function formatTime(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const days = Math.floor(diff / (1000 * 60 * 60 * 24))

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60))
    if (hours === 0) {
      const mins = Math.floor(diff / (1000 * 60))
      return mins <= 1 ? '刚刚' : `${mins}分钟前`
    }
    return `${hours}小时前`
  }
  if (days === 1) return '昨天'
  if (days < 7) return `${days}天前`
  if (days < 30) return `${Math.floor(days / 7)}周前`
  return `${date.getMonth() + 1}月${date.getDate()}日`
}

export default function MailPage() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [mails, setMails] = useState<MailListResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [selectedMail, setSelectedMail] = useState<MailDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  const activeCategory = (searchParams.get('category') as MailCategory | 'all') || 'all'
  const activeFilter = searchParams.get('filter') || 'all' // all | unread

  const fetchMails = useCallback(async () => {
    setLoading(true)
    try {
      const params: Record<string, string> = {}
      if (activeCategory !== 'all') params.category = activeCategory
      if (activeFilter === 'unread') params.is_read = 'false'
      const res = await api.getMails(params)
      if (res.success) {
        setMails(res.data)
      }
    } catch (err) {
      console.error('Failed to fetch mails:', err)
    } finally {
      setLoading(false)
    }
  }, [activeCategory, activeFilter])

  useEffect(() => {
    fetchMails()
  }, [fetchMails])

  const handleSelectCategory = (key: MailCategory | 'all') => {
    const newParams = new URLSearchParams(searchParams)
    if (key === 'all') {
      newParams.delete('category')
    } else {
      newParams.set('category', key)
    }
    setSearchParams(newParams)
    setSelectedMail(null)
  }

  const handleFilterChange = (filter: 'all' | 'unread') => {
    const newParams = new URLSearchParams(searchParams)
    if (filter === 'all') {
      newParams.delete('filter')
    } else {
      newParams.set('filter', filter)
    }
    setSearchParams(newParams)
  }

  const handleOpenMail = async (mail: MailItem) => {
    setDetailLoading(true)
    try {
      const res = await api.getMailDetail(mail.id)
      if (res.success) {
        setSelectedMail(res.data)
        // 更新本地状态为已读
        setMails((prev) => {
          if (!prev) return prev
          return {
            ...prev,
            items: prev.items.map((m) =>
              m.id === mail.id ? { ...m, is_read: true } : m
            ),
            unread_count: Math.max(0, prev.unread_count - (mail.is_read ? 0 : 1)),
          }
        })
      }
    } catch (err) {
      console.error('Failed to open mail:', err)
    } finally {
      setDetailLoading(false)
    }
  }

  const handleMarkAllRead = async () => {
    try {
      const cat = activeCategory === 'all' ? undefined : activeCategory
      await api.markAllMailsRead(cat)
      fetchMails()
    } catch (err) {
      console.error('Failed to mark all read:', err)
    }
  }

  const handleMarkRead = async (mailId: string) => {
    try {
      await api.markMailsRead([mailId])
      setMails((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          items: prev.items.map((m) =>
            m.id === mailId ? { ...m, is_read: true } : m
          ),
          unread_count: Math.max(
            0,
            prev.unread_count - (prev.items.find((m) => m.id === mailId)?.is_read ? 0 : 1)
          ),
        }
      })
    } catch (err) {
      console.error('Failed to mark read:', err)
    }
  }

  const unreadCountForCategory = (key: MailCategory | 'all') => {
    if (!mails) return 0
    if (key === 'all') return mails.unread_count
    return mails.category_counts[key] || 0
  }

  return (
    <div className="flex h-[calc(100vh-6rem)] gap-4 max-w-[1400px]">
      {/* 左侧分类栏 */}
      <aside className="w-56 shrink-0 flex flex-col gap-3">
        {/* 标题 */}
        <div className="flex items-center gap-3 px-1">
          <h1 className="text-xl font-bold pixel-title">邮件中心</h1>
          {mails && mails.unread_count > 0 && (
            <span className="px-2 py-0.5 text-xs font-bold bg-[#B9EF3F] text-[#173126] border-2 border-[#1F5F43]">
              {mails.unread_count}
            </span>
          )}
        </div>

        {/* 写邮件按钮占位 - 游戏风格 */}
        <button
          onClick={handleMarkAllRead}
          className="w-full px-4 py-2.5 bg-[#B9EF3F] text-[#173126] font-bold text-sm border-2 border-[#1F5F43] shadow-pixel hover:brightness-110 transition-all flex items-center justify-center gap-2"
        >
          全部已读
        </button>

        {/* 筛选标签 */}
        <div className="flex gap-1">
          <button
            onClick={() => handleFilterChange('all')}
            className={clsx(
              'flex-1 py-1.5 text-xs font-medium border-2 transition-all',
              activeFilter === 'all'
                ? 'bg-[#1F5F43] text-[#F8FFD2] border-[#1F5F43]'
                : 'bg-[#FFF8DC]/80 text-[#466353] border-[#1F5F43]/20 hover:text-[#173126]'
            )}
          >
            全部
          </button>
          <button
            onClick={() => handleFilterChange('unread')}
            className={clsx(
              'flex-1 py-1.5 text-xs font-medium border-2 transition-all',
              activeFilter === 'unread'
                ? 'bg-[#1F5F43] text-[#F8FFD2] border-[#1F5F43]'
                : 'bg-[#FFF8DC]/80 text-[#466353] border-[#1F5F43]/20 hover:text-[#173126]'
            )}
          >
            未读
          </button>
        </div>

        {/* 分类列表 */}
        <nav className="flex-1 overflow-y-auto space-y-0.5">
          {CATEGORY_CONFIG.map((cat) => {
            const count = mails?.category_counts?.[cat.key] || 0
            const unread = unreadCountForCategory(cat.key)
            const isActive = activeCategory === cat.key
            return (
              <button
                key={cat.key}
                onClick={() => handleSelectCategory(cat.key)}
                className={clsx(
                  'w-full flex items-center gap-3 px-3 py-2 text-sm transition-all border-2',
                  isActive
                    ? 'bg-[#FFF8DC]/80 text-[#1F5F43] border-[#1F5F43]/20'
                    : 'text-[#466353] border-transparent hover:bg-[#FFF8DC]/80 hover:text-[#173126]'
                )}
              >
                <span className="flex-1 text-left font-medium">{cat.label}</span>
                {unread > 0 && (
                  <span className="px-1.5 py-0.5 text-[10px] font-bold bg-[#B9EF3F] text-[#173126] min-w-[1.25rem] text-center">
                    {unread}
                  </span>
                )}
                {unread === 0 && count > 0 && (
                  <span className="text-xs text-[#8B5A2B]/40">{count}</span>
                )}
              </button>
            )
          })}
        </nav>
      </aside>

      {/* 中间邮件列表 */}
      <div className="flex-1 min-w-0 flex flex-col bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20">
        {/* 列表头部 */}
        <div className="h-12 px-4 flex items-center justify-between border-b-2 border-[#1F5F43]/20 shrink-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-[#173126]">
              {CATEGORY_CONFIG.find((c) => c.key === activeCategory)?.label}
            </span>
            {mails && (
              <span className="text-xs text-[#8B5A2B]/40">
                共 {mails.total} 封
              </span>
            )}
          </div>
          {mails && mails.unread_count > 0 && (
            <button
              onClick={handleMarkAllRead}
              className="text-xs text-[#1F5F43] hover:text-[#1F5F43] transition-colors flex items-center gap-1"
            >
              标记全部已读
            </button>
          )}
        </div>

        {/* 邮件列表 */}
        <div className="flex-1 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center h-40 text-[#466353]">
              <span className="animate-pulse">加载邮件中...</span>
            </div>
          ) : !mails || mails.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-[#466353]">
              <p className="text-sm">暂无邮件</p>
              <p className="text-xs text-[#8B5A2B]/40 mt-1">比赛、转会、财务等通知将在这里显示</p>
            </div>
          ) : (
            <div className="divide-y divide-[#1F5F43]/20">
              {mails.items.map((mail) => (
                <div
                  key={mail.id}
                  onClick={() => handleOpenMail(mail)}
                  className={clsx(
                    'group flex items-start gap-3 px-4 py-3 cursor-pointer transition-all hover:bg-[#FFF8DC]/80',
                    mail.is_read ? 'bg-transparent' : 'bg-[#B9EF3F]/10'
                  )}
                >
                  {/* 发件人头像/图标 */}
                  <div className="shrink-0 mt-0.5">
                    {mail.sender_avatar_url ? (
                      <div className="w-9 h-9 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 overflow-hidden">
                        <img
                          src={`/${mail.sender_avatar_url}`}
                          alt={mail.sender_name}
                          className="w-full h-full object-cover"
                        />
                      </div>
                    ) : (
                      <div
                        className="w-9 h-9 border-2 flex items-center justify-center"
                        style={{
                          borderColor: `${MAIL_CATEGORY_COLORS[mail.category]}40`,
                          backgroundColor: `${MAIL_CATEGORY_COLORS[mail.category]}15`,
                        }}
                      >
                        <MailIcon
                          className="w-4 h-4"
                          style={{ color: MAIL_CATEGORY_COLORS[mail.category] }}
                        />
                      </div>
                    )}
                  </div>

                  {/* 内容区 */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                      <span
                        className={clsx(
                          'text-sm truncate',
                          mail.is_read ? 'text-[#466353] font-medium' : 'text-[#173126] font-bold'
                        )}
                      >
                        {mail.sender_name}
                      </span>
                      <CategoryBadge category={mail.category} />
                      {mail.priority === 'urgent' && (
                        <SquareAlert className="w-3 h-3 text-[#FF6F59] shrink-0" />
                      )}
                      {mail.priority === 'high' && (
                        <ArrowBigUp className="w-3 h-3 text-[#FFC247] shrink-0" />
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span
                        className={clsx(
                          'text-sm truncate flex-1',
                          mail.is_read ? 'text-[#466353]' : 'text-[#173126] font-bold'
                        )}
                      >
                        {mail.subject}
                      </span>
                    </div>
                    {mail.summary && (
                      <p className="text-xs text-[#8B5A2B]/40 truncate mt-0.5">
                        {mail.summary}
                      </p>
                    )}
                  </div>

                  {/* 右侧时间和操作 */}
                  <div className="shrink-0 flex flex-col items-end gap-1.5">
                    <span className="text-xs text-[#8B5A2B]/40 whitespace-nowrap">
                      {formatTime(mail.created_at)}
                    </span>
                    {!mail.is_read && (
                      <span className="w-2 h-2 bg-[#B9EF3F]" />
                    )}
                    {mail.is_read && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          handleMarkRead(mail.id)
                        }}
                        className="opacity-0 group-hover:opacity-100 text-[#8B5A2B]/40 hover:text-[#1F5F43] transition-all"
                        title="标记为已读"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* 右侧邮件详情 */}
      <AnimatePresence>
      {selectedMail && (
        <motion.div
          initial={{ x: 60, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 60, opacity: 0 }}
          transition={{ duration: 0.2, ease: 'easeOut' }}
          className="w-[420px] shrink-0 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 flex flex-col"
        >
          {/* 详情头部 */}
          <div className="h-12 px-4 flex items-center justify-between border-b-2 border-[#1F5F43]/20 shrink-0">
            <div className="flex items-center gap-2">
              <CategoryBadge category={selectedMail.category} />
              {selectedMail.priority === 'urgent' && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 bg-[#FF6F59]/20 text-[#FF6F59] border border-[#FF6F59]/40">
                  紧急
                </span>
              )}
            </div>
            <button
              onClick={() => setSelectedMail(null)}
              className="p-1 text-[#8B5A2B]/40 hover:text-[#173126] transition-colors"
            >
              <Cancel className="w-4 h-4" />
            </button>
          </div>

          {/* 详情内容 */}
          <div className="flex-1 overflow-y-auto p-5">
            {detailLoading ? (
              <div className="flex items-center justify-center h-40 text-[#466353]">
                加载中...
              </div>
            ) : (
              <>
                {/* 发件人信息 */}
                <div className="flex items-start gap-3 mb-5">
                  {selectedMail.sender_avatar_url ? (
                    <div className="w-11 h-11 bg-[#FFF8DC]/80 border-2 border-[#1F5F43]/20 overflow-hidden shrink-0">
                      <img
                        src={`/${selectedMail.sender_avatar_url}`}
                        alt={selectedMail.sender_name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                  ) : (
                    <div
                      className="w-11 h-11 border-2 flex items-center justify-center shrink-0"
                      style={{
                        borderColor: `${MAIL_CATEGORY_COLORS[selectedMail.category]}40`,
                        backgroundColor: `${MAIL_CATEGORY_COLORS[selectedMail.category]}15`,
                      }}
                    >
                      <MailIcon
                        className="w-5 h-5"
                        style={{ color: MAIL_CATEGORY_COLORS[selectedMail.category] }}
                      />
                    </div>
                  )}
                  <div className="min-w-0">
                    <p className="text-sm font-bold text-[#173126]">{selectedMail.sender_name}</p>
                    <p className="text-xs text-[#8B5A2B]/40 mt-0.5">
                      {new Date(selectedMail.created_at).toLocaleString('zh-CN')}
                    </p>
                  </div>
                </div>

                {/* 主题 */}
                <h2 className="text-lg font-bold text-[#173126] mb-4 leading-snug">
                  {selectedMail.subject}
                </h2>

                {/* 正文 */}
                <div className="text-sm text-[#466353] leading-relaxed whitespace-pre-wrap">
                  {selectedMail.body}
                </div>

                {/* 关联操作 */}
                {selectedMail.related_url && (
                  <div className="mt-6 pt-4 border-t-2 border-[#1F5F43]/20">
                    <button
                      onClick={() => {
                        if (selectedMail.related_url) {
                          navigate(selectedMail.related_url)
                        }
                      }}
                      className="inline-flex items-center gap-2 px-4 py-2 bg-[#1F5F43] text-[#F8FFD2] text-sm font-bold border-2 border-[#1F5F43] hover:bg-[#173126] transition-all"
                    >
                      {selectedMail.action_label || '查看详情'}
                      <ChevronRight className="w-4 h-4" />
                    </button>
                  </div>
                )}

                {/* 底部元信息 */}
                <div className="mt-6 pt-4 border-t-2 border-[#1F5F43]/20 text-xs text-[#8B5A2B]/40 space-y-1">
                  {selectedMail.is_read && selectedMail.read_at && (
                    <p>已读于 {new Date(selectedMail.read_at).toLocaleString('zh-CN')}</p>
                  )}
                  {selectedMail.expires_at && (
                    <p>过期时间 {new Date(selectedMail.expires_at).toLocaleString('zh-CN')}</p>
                  )}
                </div>
              </>
            )}
          </div>
        </motion.div>
      )}
      </AnimatePresence>
    </div>
  )
}
