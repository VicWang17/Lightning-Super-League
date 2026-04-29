import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'primary' | 'success' | 'warning' | 'danger' | 'info'
  size?: 'sm' | 'md'
}

const Badge = forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      children,
      variant = 'default',
      size = 'md',
      className,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center font-medium rounded-none'

    const variants = {
      default: 'bg-[#2D2D44] text-[#8B8BA7] border-2 border-[#2D2D44]',
      primary: 'bg-[#0D7377]/20 text-[#0D7377] border-2 border-[#0A5A5D]/30',
      success: 'bg-[#166534]/20 text-[#4ADE80] border-2 border-[#166534]/30',
      warning: 'bg-[#FCD34D]/10 text-[#FCD34D] border-2 border-[#FCD34D]/30',
      danger: 'bg-[#EF4444]/10 text-[#EF4444] border-2 border-[#EF4444]/30',
      info: 'bg-[#3B82F6]/10 text-[#3B82F6] border-2 border-[#3B82F6]/30',
    }

    const sizes = {
      sm: 'px-2 py-0.5 text-xs',
      md: 'px-2.5 py-1 text-xs',
    }

    return (
      <span
        ref={ref}
        className={clsx(baseStyles, variants[variant], sizes[size], className)}
        {...props}
      >
        {children}
      </span>
    )
  }
)

Badge.displayName = 'Badge'

export default Badge
