import { clsx } from 'clsx'
import type { ReactNode } from 'react'

export interface PageHeaderProps {
  title: string
  subtitle?: string
  action?: ReactNode
  className?: string
}

export function PageHeader({
  title,
  subtitle,
  action,
  className,
}: PageHeaderProps) {
  return (
    <div className={clsx('fresh-page-header flex items-start justify-between gap-4 mb-6', className)}>
      <div>
        <h1 className="text-2xl font-black text-[#173126]">{title}</h1>
        {subtitle && (
          <p className="text-sm font-bold text-[#466353] mt-1">{subtitle}</p>
        )}
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
