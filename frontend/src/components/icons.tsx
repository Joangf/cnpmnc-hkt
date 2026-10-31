import type { ReactNode, SVGProps } from 'react'

// Line icons from the design kit: 24px grid, 2.5 stroke, round caps.
// Icons support words and never replace them, so they are always hidden from assistive tech.

type IconProps = Omit<SVGProps<SVGSVGElement>, 'children'> & { size?: number }
export type IconComponent = (props: IconProps) => ReactNode

function Icon({ size = 24, children, ...props }: IconProps & { children: ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      className="shrink-0"
      {...props}
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

/** Solid cross used in the logo block. */
export function LogoMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true" focusable="false">
      <rect x="9" y="3" width="6" height="18" />
      <rect x="3" y="9" width="18" height="6" />
    </svg>
  )
}
