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
          DEFAULT: '#ECFFD8',
          secondary: '#F7FFE2',
          tertiary: '#F8FFD2',
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
          red: '#FF6F59',
          yellow: '#FFC247',
        },
        brand: {
          green: '#1F5F43',
          'green-dark': '#173126',
          'green-light': '#B9EF3F',
          blue: '#59C7EE',
          'blue-dark': '#1F5F43',
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
        'pixel': '4px 4px 0px rgba(31, 95, 67, 0.35)',
        'pixel-sm': '2px 2px 0px rgba(31, 95, 67, 0.35)',
        'pixel-lg': '6px 6px 0px rgba(31, 95, 67, 0.35)',
        'pixel-green': '4px 4px 0px #1F5F43',
        'pixel-green-glow': '4px 4px 0 rgba(31, 95, 67, 0.35), 0 0 16px rgba(185, 239, 63, 0.4)',
        'glow-green': '0 0 20px rgba(185, 239, 63, 0.4)',
        'glow-green-lg': '0 0 40px rgba(185, 239, 63, 0.5)',
        'glow': '0 0 16px var(--ui-accent-glow)',
        'card': '4px 4px 0px rgba(31, 95, 67, 0.25)',
        'card-hover': '6px 6px 0px rgba(31, 95, 67, 0.30)',
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
