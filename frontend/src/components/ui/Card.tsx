import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'default' | 'glass' | 'outlined'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      variant = 'default',
      padding = 'md',
      hover = false,
      className,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'transition-all duration-200'

    const variants = {
      default: 'bg-[#12121A] border-2 border-[#2D2D44]',
      glass:
        'bg-[#12121A]/80 border-2 border-[#2D2D44]/50',
      outlined: 'bg-transparent border-2 border-[#2D2D44]',
    }

    const paddings = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    }

    const hoverStyles = hover
      ? 'hover:border-[#0D7377]/40 hover:-translate-y-0.5 hover:shadow-pixel'
      : ''

    return (
      <div
        ref={ref}
        className={clsx(
          baseStyles,
          variants[variant],
          paddings[padding],
          hoverStyles,
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

Card.displayName = 'Card'

// Card Header 组件
export interface CardHeaderProps extends HTMLAttributes<HTMLDivElement> {
  title?: string
  subtitle?: string
  action?: React.ReactNode
}

const CardHeader = forwardRef<HTMLDivElement, CardHeaderProps>(
  ({ title, subtitle, action, children, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={clsx(
          'flex items-start justify-between mb-4',
          className
        )}
        {...props}
      >
        <div className="flex-1">
          {title && (
            <h3 className="text-lg font-semibold text-[#E2E2F0]">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-sm text-[#8B8BA7] mt-1">{subtitle}</p>
          )}
          {children}
        </div>
        {action && <div className="ml-4">{action}</div>}
      </div>
    )
  }
)

CardHeader.displayName = 'CardHeader'

// Card Content 组件
export interface CardContentProps extends HTMLAttributes<HTMLDivElement> {}

const CardContent = forwardRef<HTMLDivElement, CardContentProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <div ref={ref} className={clsx('', className)} {...props}>
        {children}
      </div>
    )
  }
)

CardContent.displayName = 'CardContent'

// Card Footer 组件
export interface CardFooterProps extends HTMLAttributes<HTMLDivElement> {
  align?: 'left' | 'center' | 'right' | 'between'
}

const CardFooter = forwardRef<HTMLDivElement, CardFooterProps>(
  ({ children, align = 'left', className, ...props }, ref) => {
    const alignStyles = {
      left: 'justify-start',
      center: 'justify-center',
      right: 'justify-end',
      between: 'justify-between',
    }

    return (
      <div
        ref={ref}
        className={clsx(
          'flex items-center mt-4 pt-4 border-t-2 border-[#2D2D44]',
          alignStyles[align],
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)

CardFooter.displayName = 'CardFooter'

export { Card, CardHeader, CardContent, CardFooter }
export default Card
