import { HTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface CardProps extends HTMLAttributes<HTMLDivElement> {
  variant?: 'glass' | 'solid' | 'outlined'
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hover?: boolean
}

const Card = forwardRef<HTMLDivElement, CardProps>(
  (
    {
      children,
      variant = 'solid',
      padding = 'md',
      hover = false,
      className,
      ...props
    },
    ref
  ) => {
    const baseStyles = 'fresh-card transition-all duration-200'

    const variants = {
      glass:
        'bg-white/75 backdrop-blur-sm border-2 border-[#1F5F43]/25 shadow-pixel',
      solid:
        'pixel-card-frame border-2 border-[#1F5F43] bg-white/85',
      outlined:
        'bg-white/45 border-2 border-[#1F5F43]/35',
    }

    const paddings = {
      none: '',
      sm: 'p-4',
      md: 'p-6',
      lg: 'p-8',
    }

    const hoverStyles = hover
      ? 'pixel-card-interactive hover:border-[#1F5F43]'
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
            <h3 className="text-lg font-black text-[#173126]">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="text-sm font-semibold text-[#466353] mt-1">{subtitle}</p>
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
          'flex items-center mt-4 pt-4 border-t-2 border-[#1F5F43]/20',
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
