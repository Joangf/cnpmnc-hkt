import defaultTheme from 'tailwindcss/defaultTheme'

// Tokens from .claude/design/design-guidelines.md ("Warm, simple, and human.").
const v = (name) => `rgb(var(--c-${name}) / <alpha-value>)`

/** @type {import('tailwindcss').Config} */
export default {
  // Hover styles only on devices that can hover, so taps don't leave cards "stuck" lifted.
  future: { hoverOnlyWhenSupported: true },
  // Dark mode is set by <html data-theme="dark"> (see src/lib/theme.ts), not only by the OS.
  darkMode: ['selector', "[data-theme='dark']"],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    // Every colour is a CSS variable (light values on :root, dark on [data-theme='dark'] in
    // src/index.css), so one attribute switches the whole palette.
    colors: {
      transparent: 'transparent',
      current: 'currentColor',
      white: '#FFFFFF',
      canvas: v('canvas'),
      'on-accent': v('on-accent'),
      ink: v('ink'),
      muted: v('muted'),
      berry: { DEFAULT: v('berry'), dark: v('berry-dark') },
      blush: v('blush'),
      mist: v('mist'),
      peach: v('peach'),
      surface: v('surface'),
      line: v('line'),
      field: v('field'),
      focus: v('focus'),
      success: { DEFAULT: v('success'), soft: v('success-soft'), line: v('success-line'), strong: v('success-strong') },
      notice: { DEFAULT: v('notice'), soft: v('notice-soft'), line: v('notice-line'), strong: v('notice-strong') },
      info: { DEFAULT: v('info'), line: v('info-line'), strong: v('info-strong') },
      alert: { DEFAULT: v('alert'), dark: v('alert-dark'), soft: v('alert-soft'), line: v('alert-line'), strong: v('alert-strong') },
      disabled: { DEFAULT: v('disabled'), text: v('disabled-text') },
    },
    // 12 buttons and inputs, 16 cards, 20 panels, full for chips.
    borderRadius: { none: '0', sm: '6px', DEFAULT: '12px', md: '12px', lg: '16px', xl: '20px', full: '9999px' },
    // Shadows are variables too: dark mode needs deeper, neutral shadows to read at all.
    boxShadow: {
      none: 'none',
      card: 'var(--shadow-card)',
      button: 'var(--shadow-button)',
      alert: 'var(--shadow-alert)',
      // Hovered link cards and buttons: same warm shadow, a little deeper.
      'card-hover': 'var(--shadow-card-hover)',
      'button-hover': 'var(--shadow-button-hover)',
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

      // Motion: short, soft and functional (see "Motion" in the design guidelines).
      transitionDuration: { DEFAULT: '200ms', fast: '120ms', base: '200ms', slow: '320ms' },
      transitionTimingFunction: {
        DEFAULT: 'cubic-bezier(0.2, 0, 0, 1)',
        out: 'cubic-bezier(0.2, 0, 0, 1)',
        in: 'cubic-bezier(0.4, 0, 1, 1)',
      },
      keyframes: {
        fade: { from: { opacity: '0' }, to: { opacity: '1' } },
        rise: { from: { opacity: '0', transform: 'translateY(8px)' }, to: { opacity: '1', transform: 'none' } },
        drop: { from: { opacity: '0', transform: 'translateY(-6px)' }, to: { opacity: '1', transform: 'none' } },
        pop: { '0%': { transform: 'scale(0.6)', opacity: '0' }, '60%': { transform: 'scale(1.15)', opacity: '1' }, '100%': { transform: 'scale(1)' } },
      },
      // `backwards` holds the first frame during a stagger delay but leaves nothing behind once done,
      // so hover transforms on the same element still work.
      animation: {
        fade: 'fade 200ms cubic-bezier(0.2, 0, 0, 1) backwards',
        rise: 'rise 320ms cubic-bezier(0.2, 0, 0, 1) backwards',
        drop: 'drop 200ms cubic-bezier(0.2, 0, 0, 1) backwards',
        pop: 'pop 240ms cubic-bezier(0.2, 0, 0, 1) backwards',
      },
    },
  },
  plugins: [],
}
