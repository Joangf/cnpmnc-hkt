import defaultTheme from 'tailwindcss/defaultTheme'

// Tokens from .claude/design/design-guidelines.md ("Warm, simple, and human.").
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      white: '#FFFFFF',
      ink: '#2B1A22',
      muted: '#5E4B53',
      berry: { DEFAULT: '#8C1D4F', dark: '#6E163E' },
      blush: '#FBE9EF',
      mist: '#EAF2F8',
      peach: '#FFF1E6',
      surface: '#FAF6F2',
      line: '#EADFD8',
      field: '#D9CBC2',
      focus: '#E59AB8',
      success: { DEFAULT: '#1E7A4F', soft: '#E8F4EE', line: '#BFDFCD', strong: '#134D33' },
      notice: { DEFAULT: '#A15C07', soft: '#FFF6E8', line: '#F1D9B5', strong: '#6B3D05' },
      info: { DEFAULT: '#25507A', line: '#C9DCEA', strong: '#1E3A57' },
      alert: { DEFAULT: '#B42318', dark: '#912018', soft: '#FEF3F2', line: '#F4C7C3', strong: '#7A271A' },
      disabled: { DEFAULT: '#EEF1F3', text: '#6B7882' },
    },
    // 12 buttons and inputs, 16 cards, 20 panels, full for chips.
    borderRadius: { none: '0', sm: '6px', DEFAULT: '12px', md: '12px', lg: '16px', xl: '20px', full: '9999px' },
    boxShadow: {
      none: 'none',
      card: '0 1px 2px rgba(43,26,34,0.05), 0 8px 24px rgba(43,26,34,0.08)',
      button: '0 2px 8px rgba(140,29,79,0.25)',
      alert: '0 2px 8px rgba(180,35,24,0.25)',
    },
    extend: {
      fontFamily: { sans: ['"Figtree Variable"', 'Figtree', ...defaultTheme.fontFamily.sans] },
      fontSize: {
        hero: ['3.5rem', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        display: ['3rem', { lineHeight: '3.5rem', letterSpacing: '-0.02em' }],
        h1: ['2rem', '2.5rem'],
        h2: ['1.375rem', '1.875rem'],
        body: ['1.125rem', '1.75rem'],
        control: ['1.0625rem', '1.5rem'],
        caption: ['0.9375rem', '1.375rem'],
      },
      letterSpacing: { label: '0.08em' },
      borderWidth: { 1.5: '1.5px' },
      // 1200px content + 24px gutters.
      maxWidth: { page: '78rem' },
    },
  },
  plugins: [],
}
