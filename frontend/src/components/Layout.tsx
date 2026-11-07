import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet, useLocation, useMatch, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { useTheme } from '../lib/theme'
import { IconMenu, IconMoon, IconPhone, IconSun, LogoMark } from './icons'
import { EMERGENCY_NUMBER } from './ui'

const mainLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-12 items-center whitespace-nowrap text-control font-medium no-underline hover:text-berry ${
    isActive ? 'text-berry underline decoration-2 underline-offset-[10px]' : 'text-ink'
  }`
const accountLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-11 items-center whitespace-nowrap no-underline hover:text-berry ${isActive ? 'font-semibold text-berry' : 'text-muted'}`
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
    { to: '/departments', label: 'Departments' },
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

      <header className="bg-canvas">
        {/* The emergency number is always visible (booking flow step 1). */}
        <div className="bg-surface">
          <div className="mx-auto flex max-w-page flex-wrap items-center justify-between gap-x-6 px-4 text-caption text-muted sm:px-6">
            <p className="hidden py-2.5 sm:block">Book online any time · Hospitals confirm during clinic hours</p>
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
              <p className="flex min-h-11 items-center gap-1.5 whitespace-nowrap">
                <IconPhone size={16} className="text-alert" />
                Emergency 24/7:{' '}
                <a href={`tel:${EMERGENCY_NUMBER}`} className="font-semibold text-alert underline underline-offset-2 hover:text-alert-dark">
                  {EMERGENCY_NUMBER}
                </a>
              </p>
            </div>
          </div>
        </div>

        <div className="border-b border-line">
          <div className="mx-auto flex max-w-page items-center gap-x-10 px-4 py-4 sm:px-6 sm:py-5">
            <Link to="/" className="flex items-center gap-3 text-ink no-underline hover:text-ink">
              <span className="flex h-10 w-10 items-center justify-center rounded-md bg-berry text-on-accent shadow-button">
                <LogoMark />
              </span>
              <span className="text-xl font-bold">HKT Hospital</span>
            </Link>
            <nav aria-label="Main" className="hidden flex-1 items-center gap-8 xl:flex">
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
