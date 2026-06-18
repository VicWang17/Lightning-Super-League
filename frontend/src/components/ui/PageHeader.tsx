import { clsx } from 'clsx'
import type { ReactNode, ComponentType } from 'react'

export interface PageHeaderProps {
  icon?: ComponentType<{ className?: string }>
  title: string
  subtitle?: string
  action?: ReactNode
  className?: string
}

export function PageHeader({
  icon: Icon,
  title,
  subtitle,
  action,
  className,
}: PageHeaderProps) {
  return (
    <div className={clsx('flex items-start justify-between gap-4 mb-6', className)}>
      <div className="flex items-center gap-3">
        {Icon && <Icon className="w-7 h-7 text-accent" />}
        <div>
          <h1 className="text-2xl font-bold text-text-primary">{title}</h1>
          {subtitle && (
            <p className="text-sm text-text-secondary mt-1">{subtitle}</p>
          )}
        </div>
      </div>
      {action && <div>{action}</div>}
    </div>
  )
}
