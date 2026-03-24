import { NavLink, Outlet } from 'react-router-dom'
import { getUserDisplayName, logout } from '../lib/keycloak'

const navItems = [
  { to: '/', label: 'Chat', icon: MessageIcon },
  { to: '/documents', label: 'Documents', icon: FileIcon },
  { to: '/search', label: 'Search', icon: SearchIcon },
] as const

export default function Layout() {
  const username = getUserDisplayName()

  return (
    <div className="flex h-screen flex-col bg-surface">
      {/* Top navigation bar */}
      <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface-raised px-5">
        <div className="flex items-center gap-6">
          <h1 className="text-base font-semibold tracking-tight text-ink">
            <span className="text-accent">K</span>nowledge
          </h1>
          <nav className="flex items-center gap-1">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-accent/15 text-accent'
                      : 'text-ink-muted hover:bg-surface-overlay hover:text-ink'
                  }`
                }
              >
                <Icon />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          <span className="text-xs text-ink-muted">{username}</span>
          <button
            onClick={logout}
            className="rounded-md px-3 py-1 text-xs text-ink-muted transition-colors hover:bg-surface-overlay hover:text-ink"
          >
            Sign out
          </button>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1 overflow-hidden">
        <Outlet />
      </main>
    </div>
  )
}

function MessageIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 3h12v8H4l-2 2V3z" />
    </svg>
  )
}

function FileIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 1H4a1 1 0 0 0-1 1v12a1 1 0 0 0 1 1h8a1 1 0 0 0 1-1V5L9 1z" />
      <path d="M9 1v4h4" />
    </svg>
  )
}

function SearchIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="7" cy="7" r="4" />
      <path d="M14 14l-3-3" />
    </svg>
  )
}
