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
      'inline-flex items-center justify-center font-bold focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-[#F8FFD2] disabled:opacity-50 disabled:cursor-not-allowed'

    const variants = {
      primary:
        'btn-primary fresh-button-primary text-[#173126] focus:ring-[#B9EF3F]',
      secondary:
        'btn-secondary fresh-button-secondary focus:ring-[#59C7EE]',
      outline:
        'fresh-button-outline bg-white/70 hover:bg-white text-[#173126] border-2 border-[#1F5F43]/40 hover:border-[#1F5F43] focus:ring-[#B9EF3F] hover:-translate-y-0.5 transition-all duration-200',
      ghost:
        'fresh-button-ghost bg-transparent hover:bg-white/70 text-[#466353] hover:text-[#173126] focus:ring-[#59C7EE] border-2 border-transparent hover:-translate-y-0.5 transition-all duration-200',
      danger:
        'fresh-button-danger bg-[#FF6F59] hover:bg-[#FF6F59] text-[#173126] focus:ring-[#FF6F59] border-2 border-[#1F5F43] shadow-pixel hover:-translate-y-0.5 transition-all duration-200',
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
