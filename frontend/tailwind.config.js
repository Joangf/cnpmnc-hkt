import defaultTheme from 'tailwindcss/defaultTheme'

// Tokens from docs/design-guidelines.md ("Bold blocks. Calm care.").
/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      white: '#FFFFFF',
      ink: '#111111',
      muted: '#3D3D3D',
      sky: '#12B5E5',
      mint: '#5EE07A',
      sun: '#FFC72C',
      blush: '#F6C9BD',
      cobalt: '#1652C8',
      alert: { DEFAULT: '#C8231B', dark: '#A11C15' },
      grey: { 100: '#F2F2F2', 200: '#EDEDED', 400: '#8A8A8A', 600: '#5C5C5C' },
    },
    // Square corners only; circles are reserved for avatars and illustration.
    borderRadius: { none: '0', full: '9999px' },
    // Flat colour fields: no drop shadows.
    boxShadow: { none: 'none' },
    extend: {
      fontFamily: { sans: ['"Figtree Variable"', 'Figtree', ...defaultTheme.fontFamily.sans] },
      fontSize: {
        display: ['3.5rem', { lineHeight: '3.75rem', letterSpacing: '-0.02em' }],
        h1: ['2.25rem', { lineHeight: '2.75rem', letterSpacing: '-0.01em' }],
        h2: ['1.5rem', '2rem'],
        body: ['1.125rem', '1.75rem'],
        caption: ['0.9375rem', '1.375rem'],
      },
      letterSpacing: { label: '0.06em', nav: '0.04em' },
      borderWidth: { 3: '3px' },
      outlineWidth: { 3: '3px' },
      maxWidth: { page: '80rem' },
    },
  },
  plugins: [],
}
