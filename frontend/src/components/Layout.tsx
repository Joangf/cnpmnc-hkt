import { useQuery } from '@tanstack/react-query'
import { useEffect, useState, type ReactNode } from 'react'
import { Link, NavLink, Outlet, useLocation, useMatch, useNavigate } from 'react-router-dom'
import { api } from '../api/endpoints'
import { useAuth } from '../auth/AuthContext'
import { IconMenu, IconPhone, LogoMark } from './icons'
import { EMERGENCY_NUMBER } from './ui'

const mainLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-12 items-center text-base font-extrabold uppercase tracking-nav hover:text-cobalt ${
    isActive ? 'underline decoration-[3px] underline-offset-[6px]' : ''
  }`
const accountLinkClass = ({ isActive }: { isActive: boolean }) =>
  `flex min-h-12 items-center text-caption font-extrabold uppercase tracking-label hover:text-cobalt ${
    isActive ? 'underline decoration-2 underline-offset-4' : ''
  }`
const menuItemClass =
  'flex min-h-14 w-full items-center justify-between border-b-2 border-ink px-4 text-left text-base font-extrabold uppercase tracking-nav hover:bg-sun sm:px-6'

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
    { to: '/hospitals', label: 'Hospitals & clinics' },
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
                <span className="ml-2 inline-flex min-w-6 items-center justify-center bg-ink px-1.5 text-xs font-extrabold text-white">
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
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:bg-sun focus:px-4 focus:py-3 focus:font-extrabold"
      >
        Skip to content
      </a>

      <header className="border-b-3 border-ink bg-white">
        {/* The emergency number is always visible (booking flow step 1). */}
        <div className="flex items-center justify-between gap-4 border-b-3 border-ink px-4 sm:px-6">
          <a
            href={`tel:${EMERGENCY_NUMBER}`}
            className="flex min-h-12 items-center gap-2 text-caption font-extrabold uppercase tracking-label text-alert hover:text-ink"
          >
            <IconPhone size={20} />
            Emergency {EMERGENCY_NUMBER}
          </a>
          <nav aria-label="Account" className="hidden items-center gap-7 xl:flex">
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
        </div>

        <div className="flex items-stretch">
          <Link to="/" className="flex items-center gap-3 border-r-3 border-ink px-4 py-4 hover:text-ink sm:px-7 sm:py-5">
            <span className="flex h-10 w-10 items-center justify-center border-3 border-ink bg-sky">
              <LogoMark />
            </span>
            <span className="text-[1.375rem] font-extrabold leading-none">CareBook</span>
          </Link>
          <nav aria-label="Main" className="hidden flex-1 items-center justify-end gap-9 px-8 xl:flex">
            {mainLinks.map((l) => (
              <NavLink key={l.to} to={l.to} className={mainLinkClass}>
                {l.label}
              </NavLink>
            ))}
          </nav>
          {!isAdmin && (
            <div className="hidden items-center border-l-3 border-ink px-7 xl:flex">
              <Link to="/doctors" className="btn-primary min-h-[52px] px-6">
                Book now
              </Link>
            </div>
          )}
          <div className="ml-auto flex items-center px-4 sm:px-6 xl:hidden">
            <button
              className="btn-secondary btn-sm"
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
          <nav id="mobile-menu" aria-label="Menu" className="border-t-3 border-ink xl:hidden">
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
            {!isAdmin && (
              <div className="p-4 sm:px-6">
                <Link to="/doctors" className="btn-primary w-full">
                  Book now
                </Link>
              </div>
            )}
          </nav>
        )}
      </header>

      <main id="main" className={`flex-1 ${isHome ? '' : 'page'}`}>
        <Outlet />
      </main>

      <footer className="border-t-3 border-ink">
        <div className="mx-auto flex max-w-page flex-col gap-2 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:gap-8 sm:px-6">
          <p className="font-extrabold">CareBook</p>
          <p className="caption">
            CareBook is a booking platform and does not provide medical advice. In an emergency call{' '}
            <a className="link text-ink" href={`tel:${EMERGENCY_NUMBER}`}>
              {EMERGENCY_NUMBER}
            </a>
            .
          </p>
        </div>
      </footer>
    </div>
  )
}
