import { ButtonHTMLAttributes, forwardRef } from 'react'
import { clsx } from 'clsx'

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  isLoading?: boolean
  fullWidth?: boolean
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      isLoading = false,
      fullWidth = false,
      disabled,
      className,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      'inline-flex items-center justify-center font-medium rounded-lg transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#0A0A0F] disabled:opacity-50 disabled:cursor-not-allowed'

    const variants = {
      primary:
        'bg-[#0D7377] hover:bg-[#0A5A5D] text-white focus:ring-[#0D7377] shadow-[0_4px_12px_rgba(13,115,119,0.3)] hover:shadow-[0_4px_16px_rgba(13,115,119,0.4)]',
      secondary:
        'bg-[#1E1E2D] hover:bg-[#2D2D44] text-[#E2E2F0] focus:ring-[#2D2D44] border border-[#2D2D44]',
      outline:
        'bg-transparent hover:bg-[#1E1E2D] text-[#E2E2F0] border border-[#2D2D44] hover:border-[#0D7377]/50 focus:ring-[#0D7377]',
      ghost:
        'bg-transparent hover:bg-[#1E1E2D] text-[#8B8BA7] hover:text-[#E2E2F0] focus:ring-[#2D2D44]',
      danger:
        'bg-[#DC2626] hover:bg-[#B91C1C] text-white focus:ring-[#DC2626] shadow-[0_4px_12px_rgba(220,38,38,0.3)]',
    }

    const sizes = {
      sm: 'px-3 py-1.5 text-sm',
      md: 'px-5 py-2.5 text-sm',
      lg: 'px-6 py-3 text-base',
    }

    return (
      <button
        ref={ref}
        className={clsx(
          baseStyles,
          variants[variant],
          sizes[size],
          fullWidth && 'w-full',
          className
        )}
        disabled={disabled || isLoading}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    )
  }
)

Button.displayName = 'Button'

export default Button
