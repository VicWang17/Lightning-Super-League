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
      'inline-flex items-center font-black rounded-none'

    const variants = {
      default: 'bg-white/80 text-[#466353] border-2 border-[#1F5F43]/30',
      primary: 'bg-[#59C7EE]/22 text-[#173126] border-2 border-[#1F5F43]/30',
      success: 'bg-[#B9EF3F]/35 text-[#1F5F43] border-2 border-[#1F5F43]/30',
      warning: 'bg-[#FFC247]/30 text-[#8B5A2B] border-2 border-[#1F5F43]/30',
      danger: 'bg-[#FF6F59]/18 text-[#FF6F59] border-2 border-[#FF6F59]/45',
      info: 'bg-[#59C7EE]/18 text-[#173126] border-2 border-[#59C7EE]/50',
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
