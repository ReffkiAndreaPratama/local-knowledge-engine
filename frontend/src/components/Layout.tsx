import { useState, type ReactNode } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  BookOpen,
  Bot,
  FileText,
  FolderKanban,
  Gauge,
  ListChecks,
  Menu,
  Moon,
  Search,
  Settings as SettingsIcon,
  Sun,
  X,
} from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui'
import { statsApi, settingsApi } from '@/lib/api'
import { cn } from '@/lib/utils'
import { useTheme } from '@/hooks/useTheme'

interface LayoutProps {
  children: ReactNode
}

const navItems = [
  { path: '/overview', icon: Gauge, label: 'Overview' },
  { path: '/search', icon: Search, label: 'Search' },
  { path: '/documents', icon: FileText, label: 'Documents' },
  { path: '/collections', icon: FolderKanban, label: 'Collections' },
  { path: '/assistant', icon: Bot, label: 'AI Assistant' },
  { path: '/jobs', icon: ListChecks, label: 'Indexing Jobs' },
  { path: '/settings', icon: SettingsIcon, label: 'Settings' },
]

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const { theme, toggle } = useTheme()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [query, setQuery] = useState('')

  const { data: stats } = useQuery({
    queryKey: ['stats'],
    queryFn: statsApi.get,
    refetchInterval: 15_000,
  })

  const { data: settings } = useQuery({
    queryKey: ['settings'],
    queryFn: settingsApi.get,
    staleTime: 60_000,
  })

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = query.trim()
    if (!trimmed) return
    navigate(`/search?q=${encodeURIComponent(trimmed)}`)
    setMobileOpen(false)
  }

  const indexingActive = (stats?.pending_documents ?? 0) > 0

  return (
    <div className="flex h-screen bg-background text-foreground">
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-40 flex w-64 flex-col border-r border-border bg-surface transition-transform md:static md:translate-x-0',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex items-center justify-between px-5 py-5">
          <Link to="/overview" className="flex items-center gap-2.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
              <BookOpen className="h-4 w-4" />
            </span>
            <span className="text-sm font-semibold leading-tight">
              Local Knowledge
              <span className="block text-[11px] font-normal text-muted">Engine</span>
            </span>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="flex-1 space-y-0.5 px-3" aria-label="Main navigation">
          {navItems.map((item) => {
            const Icon = item.icon
            const isActive = location.pathname === item.path
            return (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setMobileOpen(false)}
                aria-current={isActive ? 'page' : undefined}
                className={cn(
                  'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                  isActive
                    ? 'bg-primary-soft font-medium text-primary'
                    : 'text-muted hover:bg-elevated hover:text-foreground',
                )}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="space-y-2 border-t border-border px-4 py-4 text-[11px] text-muted">
          <div className="flex items-center justify-between">
            <span>Documents</span>
            <span className="font-medium text-foreground">{stats?.document_count ?? '—'}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Chunks</span>
            <span className="font-medium text-foreground">{stats?.chunk_count ?? '—'}</span>
          </div>
          <div className="flex items-center justify-between">
            <span>Index status</span>
            <span
              className={cn(
                'font-medium',
                indexingActive ? 'text-warning' : 'text-success',
              )}
            >
              {indexingActive ? 'Indexing…' : 'Idle'}
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span>Embeddings</span>
            <span className="font-medium text-foreground">
              {settings?.enable_semantic_search
                ? `${stats?.embedding_coverage_percent?.toFixed(0) ?? 0}%`
                : 'Off'}
            </span>
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-border bg-surface/80 px-4 py-3 backdrop-blur md:px-6">
          <Button
            variant="ghost"
            size="icon"
            className="md:hidden"
            onClick={() => setMobileOpen(true)}
            aria-label="Open navigation"
          >
            <Menu className="h-4 w-4" />
          </Button>

          <form onSubmit={submitSearch} className="relative flex-1 max-w-2xl" role="search">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search your documents…"
              aria-label="Global search"
              className="h-9 w-full rounded-lg border border-border bg-background pl-9 pr-16 text-sm text-foreground placeholder:text-muted"
            />
            <kbd className="pointer-events-none absolute right-2 top-1/2 hidden -translate-y-1/2 rounded border border-border bg-elevated px-1.5 py-0.5 text-[10px] text-muted sm:block">
              Enter
            </kbd>
          </form>

          <div className="ml-auto flex items-center gap-2">
            <span
              className="hidden items-center gap-1.5 rounded-full border border-border px-2.5 py-1 text-[11px] text-muted sm:inline-flex"
              title={settings?.embedding_model}
            >
              <span
                className={cn(
                  'h-1.5 w-1.5 rounded-full',
                  settings?.enable_semantic_search ? 'bg-success' : 'bg-muted',
                )}
              />
              {settings?.enable_semantic_search ? 'Semantic on' : 'Semantic off'}
            </span>
            <Button
              variant="ghost"
              size="icon"
              onClick={toggle}
              aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
            >
              {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
            </Button>
          </div>
        </header>

        <main className="min-w-0 flex-1 overflow-auto">
          <div className="mx-auto w-full max-w-6xl px-4 py-6 md:px-6 md:py-8">{children}</div>
        </main>
      </div>
    </div>
  )
}
