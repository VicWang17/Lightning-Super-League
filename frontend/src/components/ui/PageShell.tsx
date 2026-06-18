import { clsx } from 'clsx'
import type { ReactNode } from 'react'

export interface PageShellProps {
  children: ReactNode
  className?: string
  theme?: 'default' | 'tactics' | 'cup'
}

export function PageShell({ children, className, theme = 'default' }: PageShellProps) {
  return (
    <div
      className={clsx('space-y-6 relative', className)}
      data-ui-theme={theme === 'default' ? undefined : theme}
    >
      {children}
    </div>
  )
}
