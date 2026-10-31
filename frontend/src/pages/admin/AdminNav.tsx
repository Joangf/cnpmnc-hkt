import { NavLink } from 'react-router-dom'

const items = [
  { to: '/admin', label: 'Overview', end: true },
  { to: '/admin/directory', label: 'Directory' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/reviews', label: 'Reviews' },
]

export function AdminNav() {
  return (
    <nav aria-label="Administration" className="mb-8 flex flex-wrap border-l-3 border-t-3 border-ink">
      {items.map((i) => (
        <NavLink key={i.to} to={i.to} end={i.end} className={({ isActive }) =>
            `flex min-h-12 items-center border-b-3 border-r-3 border-ink px-5 font-extrabold uppercase tracking-label ${isActive ? 'bg-ink text-white hover:text-white' : 'bg-white hover:bg-sun hover:text-ink'}`
          }>
          {i.label}
        </NavLink>
      ))}
    </nav>
  )
}
