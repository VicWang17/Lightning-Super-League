/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        background: {
          DEFAULT: '#0A0A0F',
          secondary: '#12121A',
          tertiary: '#1E1E2D',
        },
        surface: {
          DEFAULT: 'var(--ui-surface-solid)',
          hover: 'var(--ui-surface-hover)',
          glass: 'var(--ui-surface-glass)',
          'glass-weak': 'var(--ui-surface-glass-weak)',
          'glass-hover': 'var(--ui-surface-glass-hover)',
        },
        glass: {
          border: 'var(--ui-glass-border)',
          'border-strong': 'var(--ui-glass-border-strong)',
        },
        border: {
          DEFAULT: 'var(--ui-border-subtle)',
          strong: 'var(--ui-border-strong)',
        },
        text: {
          primary: 'var(--ui-text-primary)',
          secondary: 'var(--ui-text-secondary)',
          muted: 'var(--ui-text-muted)',
        },
        accent: {
          DEFAULT: 'var(--ui-accent)',
          secondary: 'var(--ui-accent-secondary)',
          glow: 'var(--ui-accent-glow)',
          10: 'var(--ui-accent-10)',
          red: '#EF4444',
          yellow: '#FCD34D',
        },
        brand: {
          green: '#166534',
          'green-dark': '#14532D',
          'green-light': '#4ADE80',
          blue: '#3B82F6',
          'blue-dark': '#2563EB',
        },
      },
      fontFamily: {
        pixel: ['"Press Start 2P"', 'cursive'],
        sans: ['Inter', 'Noto Sans SC', 'system-ui', 'sans-serif'],
        mono: ['Roboto Mono', 'JetBrains Mono', 'monospace'],
      },
      maxWidth: {
        'container': '1440px',
      },
      boxShadow: {
        'pixel': '4px 4px 0px rgba(0, 0, 0, 0.5)',
        'pixel-sm': '2px 2px 0px rgba(0, 0, 0, 0.5)',
        'pixel-lg': '6px 6px 0px rgba(0, 0, 0, 0.5)',
        'pixel-green': '4px 4px 0px #14532D',
        'pixel-green-glow': '4px 4px 0 rgba(0, 0, 0, 0.5), 0 0 16px rgba(198, 241, 53, 0.4)',
        'glow-green': '0 0 20px rgba(198, 241, 53, 0.4)',
        'glow-green-lg': '0 0 40px rgba(198, 241, 53, 0.5)',
        'glow': '0 0 16px var(--ui-accent-glow)',
        'card': '4px 4px 0px rgba(0, 0, 0, 0.3)',
        'card-hover': '6px 6px 0px rgba(0, 0, 0, 0.4)',
      },
      borderRadius: {
        'none': '0px',
        'sm': '0px',
        'md': '0px',
        'lg': '0px',
        'xl': '0px',
      },
      transitionDuration: {
        'fast': '100ms',
        'normal': '150ms',
        'slow': '200ms',
      },
    },
  },
  plugins: [],
}
