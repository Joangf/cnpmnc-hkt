import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet, useLocation, useMatch, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../lib/theme'
import { IconMenu, IconMoon, IconSun, LogoMark } from './icons'
import { EMERGENCY_NUMBER } from './ui'

const mainLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-9 items-center px-4 py-1.5 rounded-full text-sm font-semibold whitespace-nowrap transition-all duration-fast no-underline ${
    isActive ? 'bg-berry text-white shadow-button' : 'text-ink hover:text-berry hover:bg-blush'
  }`
const accountLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-10 items-center whitespace-nowrap text-xs font-semibold no-underline transition-colors hover:text-berry ${
    isActive ? 'text-berry' : 'text-muted'
  }`
const menuItemClass =
  'flex min-h-14 w-full items-center justify-between border-b border-line px-4 text-left text-control font-medium text-ink no-underline hover:bg-blush hover:text-berry sm:px-6'

/** Dark mode switch: a toggle button whose label stays "Dark mode"; aria-pressed carries the state.
 * The icon pops in again each time the theme changes. */
function ThemeToggle({ variant }: { variant: 'chip' | 'menu' }) {
  const { theme, toggle } = useTheme()
  const dark = theme === 'dark'
  const Icon = dark ? IconSun : IconMoon
  const icon = <Icon key={theme} size={18} className="animate-pop" />
  if (variant === 'menu') {
    return (
      <button type="button" className={menuItemClass} aria-pressed={dark} onClick={toggle}>
        <span className="flex items-center gap-2">
          {icon}
          Dark mode
        </span>
        <span className="text-caption text-muted">{dark ? 'On' : 'Off'}</span>
      </button>
    )
  }
  return (
    <button type="button" className="chip min-h-12 gap-2 px-4" aria-pressed={dark} onClick={toggle}>
      {icon}
      Dark mode
    </button>
  )
}

interface NavItem {
  to: string
  label: ReactNode
  end?: boolean
}

export function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const { pathname, hash } = useLocation()
  const isHome = useMatch({ path: '/', end: true }) !== null
  const [open, setOpen] = useState(false)
  const isPatient = user?.role === 'PATIENT'
  const isAdmin = user?.role === 'ADMIN'

  const notifications = useQuery({
    queryKey: ['notifications'],
    queryFn: api.notifications.list,
    enabled: isPatient,
    refetchInterval: 30_000,
  })
  const unread = notifications.data?.unread_count ?? 0

  // New page: start at the top and close the menu (BrowserRouter does neither by itself).
  useEffect(() => {
    setOpen(false)
    if (!hash) window.scrollTo(0, 0)
  }, [pathname, hash])

  const signOut = async () => {
    setOpen(false)
    await logout()
    navigate('/')
  }

  const mainLinks: NavItem[] = [
    { to: '/doctors', label: 'Find a doctor' },
    { to: '/symptoms', label: 'Symptom checker' },
  ]
  const accountLinks: NavItem[] = isPatient
    ? [
        { to: '/appointments', label: 'My appointments' },
        {
          to: '/notifications',
          label: (
            <>
              Notifications
              {unread > 0 && (
                <span
                  key={unread}
                  className="ml-2 inline-flex min-w-6 animate-pop items-center justify-center rounded-full bg-berry px-1.5 text-xs font-semibold text-on-accent"
                >
                  {unread}
                  <span className="sr-only"> unread</span>
                </span>
              )}
            </>
          ),
        },
        { to: '/profile', label: 'Profile' },
      ]
    : isAdmin
      ? [{ to: '/admin', label: 'Admin' }]
      : [
          { to: '/login', label: 'Sign in' },
          { to: '/register', label: 'Register' },
        ]

  return (
    <div className="flex min-h-screen flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-canvas focus:px-4 focus:py-3 focus:font-semibold focus:shadow-card"
      >
        Skip to content
      </a>

      <header className="sticky top-0 z-40 bg-canvas/95 backdrop-blur-md shadow-sm transition-all">
        {/* The emergency number is always visible (booking flow step 1). */}
        <div className="bg-surface/80 border-b border-line/60">
          <div className="mx-auto flex max-w-page flex-wrap items-center justify-between gap-x-6 px-4 text-xs font-medium text-muted sm:px-6">
            <p className="hidden py-2 sm:block">HKT Hospital - Online booking 24/7 · Instant confirmation</p>
            <div className="flex items-center gap-6">
              <nav aria-label="Account" className="hidden items-center gap-5 xl:flex">
                {accountLinks.map((l) => (
                  <NavLink key={l.to} to={l.to} className={accountLinkClass}>
                    {l.label}
                  </NavLink>
                ))}
                {user && (
                  <button className={accountLinkClass({ isActive: false })} onClick={signOut}>
                    Sign out
                  </button>
                )}
              </nav>
              <p className="flex min-h-9 items-center gap-2 whitespace-nowrap">
                <span className="relative flex h-2.5 w-2.5">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-alert opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-alert"></span>
                </span>
                <span className="text-muted">Emergency 24/7:</span>
                <a href={`tel:${EMERGENCY_NUMBER}`} className="font-bold text-alert hover:underline">
                  {EMERGENCY_NUMBER}
                </a>
              </p>
            </div>
          </div>
        </div>

        <div className="border-b border-line">
          <div className="mx-auto flex max-w-page items-center gap-x-8 px-4 py-3 sm:px-6 sm:py-3.5">
            <Link to="/" className="flex items-center gap-3 text-ink no-underline hover:text-ink group">
              <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-berry text-on-accent shadow-button group-hover:scale-105 transition-transform duration-fast">
                <LogoMark size={22} />
              </span>
              <div className="flex flex-col">
                <span className="text-xl font-extrabold tracking-tight text-ink leading-tight">HKT Hospital</span>
                <span className="text-[11px] font-semibold uppercase tracking-wider text-muted">Healthcare Center</span>
              </div>
            </Link>
            <nav aria-label="Main" className="hidden flex-1 items-center gap-2 xl:flex">
              {mainLinks.map((l) => (
                <NavLink key={l.to} to={l.to} className={mainLinkClass}>
                  {l.label}
                </NavLink>
              ))}
            </nav>
            <div className="ml-auto hidden items-center gap-3 xl:flex">
              <ThemeToggle variant="chip" />
              {!isAdmin && (
                <Link to="/doctors" className="btn-primary min-h-12 px-[22px] text-base">
                  Book appointment
                </Link>
              )}
            </div>
            <button
              className="btn-secondary btn-sm ml-auto xl:hidden"
              aria-expanded={open}
              aria-controls="mobile-menu"
              onClick={() => setOpen((o) => !o)}
            >
              <IconMenu size={20} />
              Menu
            </button>
          </div>
        </div>

        {open && (
          <nav id="mobile-menu" aria-label="Menu" className="animate-drop border-b border-line shadow-card xl:hidden">
            {[...mainLinks, ...accountLinks].map((l) => (
              <NavLink key={l.to} to={l.to} className={menuItemClass} onClick={() => setOpen(false)}>
                <span>{l.label}</span>
                <span aria-hidden="true">→</span>
              </NavLink>
            ))}
            {user && (
              <button className={menuItemClass} onClick={signOut}>
                Sign out
              </button>
            )}
            <ThemeToggle variant="menu" />
            {!isAdmin && (
              <div className="p-4 sm:px-6">
                <Link to="/doctors" className="btn-primary w-full">
                  Book appointment
                </Link>
              </div>
            )}
          </nav>
        )}
      </header>

      <main id="main" className={`flex-1 ${isHome ? '' : 'page'}`}>
        {/* Each new page rises in gently; query-string changes (filters, paging) don't replay it. */}
        <div key={pathname} className="reveal">
          <Outlet />
        </div>
      </main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto flex max-w-page flex-col gap-2 px-4 py-8 sm:flex-row sm:items-center sm:justify-between sm:gap-8 sm:px-6">
          <p className="font-bold">HKT Hospital</p>
          <p className="caption">
            HKT Hospital is a booking platform and does not provide medical advice. In an emergency call{' '}
            <a className="link text-alert hover:text-alert-dark" href={`tel:${EMERGENCY_NUMBER}`}>
              {EMERGENCY_NUMBER}
            </a>
            .
          </p>
        </div>
      </footer>
    </div>
  )
}
