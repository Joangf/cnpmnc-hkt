import type { ReactNode, SVGProps } from 'react'

// Line icons from the design kit: 24px grid, 2px stroke, round caps.
// Icons support words and never replace them, so they are always hidden from assistive tech.

type IconProps = Omit<SVGProps<SVGSVGElement>, 'children'> & { size?: number }
export type IconComponent = (props: IconProps) => ReactNode

function Icon({ size = 24, children, className = '', ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
      className={`shrink-0 ${className}`}
    >
      {children}
    </svg>
  )
}

export const IconSearch: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-4-4" />
  </Icon>
)

export const IconCheck: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12l3 3 5-6" />
  </Icon>
)

export const IconClock: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 7v5l3 2" />
  </Icon>
)

export const IconAlert: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M12 3l10 18H2z" />
    <path d="M12 10v4M12 17.5v.5" />
  </Icon>
)

export const IconInfo: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 7.5v.5" />
  </Icon>
)

export const IconX: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M9 9l6 6M15 9l-6 6" />
  </Icon>
)

export const IconMinus: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M8 12h8" />
  </Icon>
)

export const IconRefund: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M3 12a9 9 0 103-6.7" />
    <path d="M3 4v5h5" />
  </Icon>
)

export const IconPhone: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M5 4h4l2 5-2.5 1.5a11 11 0 005 5L15 13l5 2v4a2 2 0 01-2 2A16 16 0 013 6a2 2 0 012-2z" />
  </Icon>
)

export const IconMenu: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Icon>
)

export const IconArrowRight: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M5 12h14M13 6l6 6-6 6" />
  </Icon>
)

export const IconArrowLeft: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M19 12H5M11 6l-6 6 6 6" />
  </Icon>
)

export const IconSun: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="12" r="4" />
    <path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" />
  </Icon>
)

export const IconMoon: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" />
  </Icon>
)

// Specialty tiles (homepage example board).
export const IconHeart: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10z" />
  </Icon>
)

export const IconPerson: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="8" r="4" />
    <path d="M5 21c0-4 3-7 7-7s7 3 7 7" />
  </Icon>
)

export const IconFemale: IconComponent = (p) => (
  <Icon {...p}>
    <circle cx="12" cy="9" r="5" />
    <path d="M12 14v7M9 18h6" />
  </Icon>
)

export const IconBone: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M7 4a2 2 0 1 0 0 4l10 8a2 2 0 1 0 0 4M17 4a2 2 0 1 1 0 4L7 16a2 2 0 1 1 0 4" />
  </Icon>
)

export const IconStethoscope: IconComponent = (p) => (
  <Icon {...p}>
    <path d="M6 3v6a5 5 0 0 0 10 0V3M11 14v2a5 5 0 0 0 10 0v-2" />
    <circle cx="21" cy="12" r="2" />
  </Icon>
)

/** Rounded cross used in the logo tile. */
export function LogoMark({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
      <rect x="9" y="3" width="6" height="18" rx="1.5" />
      <rect x="3" y="9" width="18" height="6" rx="1.5" />
    </svg>
  )
}
