import { NavLink } from 'react-router-dom'

const items = [
  { to: '/admin', label: 'Overview', end: true },
  { to: '/admin/directory', label: 'Directory' },
  { to: '/admin/schedules', label: 'Schedules' },
  { to: '/admin/users', label: 'Users' },
  { to: '/admin/reviews', label: 'Reviews' },
]

export function AdminNav() {
  return (
    <nav aria-label="Administration" className="mb-8 flex flex-wrap gap-2">
      {items.map((i) => (
        <NavLink key={i.to} to={i.to} end={i.end} className={({ isActive }) =>
            `chip no-underline ${isActive ? 'border-berry bg-blush font-semibold text-berry' : 'hover:text-berry'}`
          }>
          {i.label}
        </NavLink>
      ))}
    </nav>
  )
}
