'use client'

import { useState, useEffect } from 'react'
import RankingsPage from '@/components/RankingsPage'
import ResultsPage from '@/components/ResultsPage'
import LoginPage from '@/components/LoginPage'
import ProfilePage from '@/components/ProfilePage'
import { adminProcessParticipants, getSystemState } from '@/lib/api'
import AdminDashboard from '@/components/AdminDashboard'
import PaymentPage from '@/components/PaymentPage'
import TournamentsListPage from '@/components/TournamentsListPage'
import TournamentDetailPage from '@/components/TournamentDetailPage'
import AdminTournamentsPage from '@/components/AdminTournamentsPage'
import AdminTournamentDetailPage from '@/components/AdminTournamentDetailPage'
import ErrorMessage from '@/components/shared/ErrorMessage'
import { SystemStateBadge } from '@/components/shared/StatusBadge'

type Page = 'rankings' | 'teams' | 'profile' | 'admin' | 'payment' | 'tournaments' | 'tournament-detail' | 'admin-tournaments' | 'admin-tournament-detail'

interface UserSession {
  token: string
  player_id: string
  email: string
  username?: string
  full_name?: string
  name?: string
  role: 'admin' | 'user'
}

export default function Home() {
  const [currentPage, setCurrentPage] = useState<Page>('rankings')
  const [processing, setProcessing] = useState(false)
  const [processError, setProcessError] = useState<string | null>(null)
  const [processSuccess, setProcessSuccess] = useState<string | null>(null)
  const [user, setUser] = useState<UserSession | null>(null)
  const [systemState, setSystemState] = useState<string>('DRAFT')
  const [rankingAvailable, setRankingAvailable] = useState(false)
  const [teamAvailable, setTeamAvailable] = useState(false)
  const [initializing, setInitializing] = useState(true)
  const [selectedTournamentId, setSelectedTournamentId] = useState<string | null>(null)
  const [selectedAdminTournamentId, setSelectedAdminTournamentId] = useState<string | null>(null)

  useEffect(() => {
    const init = async () => {
      try {
        const stored = localStorage.getItem('user_session')
        if (stored) {
          try {
            const parsed = JSON.parse(stored) as UserSession
            setUser(parsed)
            setCurrentPage(parsed.role === 'admin' ? 'admin' : 'rankings')
          } catch {
            localStorage.removeItem('user_session')
          }
        }

        const stateRes = await getSystemState().catch(() => ({ state: 'DRAFT' } as any))
        if (stateRes) {
          const state = stateRes as any
          setSystemState(state.state || 'DRAFT')
          setRankingAvailable((state.state || 'DRAFT') !== 'DRAFT')
          setTeamAvailable(['TEAM_GENERATED', 'PAYMENT_OPEN', 'COMPETITION_READY'].includes(state.state || 'DRAFT'))
        }
      } catch {
        setSystemState('DRAFT')
        setRankingAvailable(false)
        setTeamAvailable(false)
      } finally {
        setInitializing(false)
      }
    }

    init()
  }, [])

  const handleLoginSuccess = (session: UserSession) => {
    setUser(session)
    localStorage.setItem('user_session', JSON.stringify(session))
    setCurrentPage(session.role === 'admin' ? 'admin' : 'rankings')
  }

  const handleLogout = () => {
    setUser(null)
    localStorage.removeItem('user_session')
    setCurrentPage('rankings')
  }

  const handleProcessParticipants = async () => {
    if (!user || user.role !== 'admin') return
    setProcessing(true)
    setProcessError(null)
    setProcessSuccess(null)
    try {
      const data = await adminProcessParticipants(user.token)
      setProcessSuccess(`Berhasil memproses ${data.count} peserta`)
    } catch (err) {
      setProcessError(err instanceof Error ? err.message : 'Gagal memproses peserta')
    } finally {
      setProcessing(false)
    }
  }

  if (initializing) {
    return (
      <main className="page-shell">
        <div className="flex min-h-screen items-center justify-center">
          <div className="text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 shadow-brand-lg">
              <span className="text-3xl">⚔️</span>
            </div>
            <p className="text-sm text-gray-400">Memuat sistem...</p>
          </div>
        </div>
      </main>
    )
  }

  if (!user) {
    return (
      <main className="page-shell">
        <div className="container mx-auto px-4 py-8">
          <header className="mb-10 text-center">
            <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-brand-600 shadow-brand-lg">
              <span className="text-3xl">⚔️</span>
            </div>
            <h1 className="text-3xl font-bold text-white">ML Fair Team Formation</h1>
            <p className="mt-2 text-sm text-gray-400">Sistem Pembentukan Tim Mobile Legends yang Adil</p>
          </header>
          <LoginPage onLoginSuccess={handleLoginSuccess} />
        </div>
      </main>
    )
  }

  const isAdmin = user.role === 'admin'

  return (
    <main className="page-shell">
      <div className="mx-auto max-w-7xl px-4 py-6">
        <header className="mb-8">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-brand-600 shadow-brand">
                <span className="text-xl">⚔️</span>
              </div>
              <div>
                <h1 className="text-xl font-bold text-white">ML Fair Team Formation</h1>
                <p className="text-xs text-gray-400">Sistem Pembentukan Tim Mobile Legends yang Adil</p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              <div className="hidden items-center gap-2 rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-xs text-gray-300 md:flex">
                <span className="font-medium">{user.full_name || user.name}</span>
                <span className="text-gray-600">|</span>
                <span>{user.email}</span>
              </div>
              <SystemStateBadge state={systemState} />
              <button
                onClick={() => setCurrentPage('profile')}
                className="rounded-xl border border-white/10 bg-surface-900/60 px-3 py-1.5 text-xs font-medium text-gray-300 transition hover:border-brand-500/40 hover:text-white"
              >
                Profil
              </button>
              {isAdmin && (
                <button
                  onClick={() => setCurrentPage('admin')}
                  className={`rounded-xl px-3 py-1.5 text-xs font-semibold transition ${
                    currentPage === 'admin'
                      ? 'brand-gradient text-white shadow-brand'
                      : 'border border-white/10 bg-surface-900/60 text-gray-300 hover:border-brand-500/40 hover:text-white'
                  }`}
                >
                  Dashboard
                </button>
              )}
              <button
                onClick={handleLogout}
                className="rounded-xl border border-brand-500/30 bg-brand-500/10 px-3 py-1.5 text-xs font-medium text-brand-300 transition hover:bg-brand-500/20"
              >
                Logout
              </button>
            </div>
          </div>

          {processError && (
            <div className="mt-4">
              <ErrorMessage title="Error" message={processError} />
            </div>
          )}
          {processSuccess && (
            <div className="mt-4">
              <ErrorMessage title="Berhasil" message={processSuccess} variant="success" />
            </div>
          )}
        </header>

        <nav className="mb-8">
          <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-white/10 bg-surface-900/60 p-1.5 backdrop-blur-xl">
            <NavButton active={currentPage === 'rankings'} onClick={() => setCurrentPage('rankings')}>
              {isAdmin ? 'Perankingan' : '1. Perankingan'}
            </NavButton>
            {isAdmin && (
              <>
                <NavButton active={currentPage === 'admin'} onClick={() => setCurrentPage('admin')}>
                  Dashboard Admin
                </NavButton>
                <NavButton active={currentPage === 'admin-tournaments'} onClick={() => { setSelectedAdminTournamentId(null); setCurrentPage('admin-tournaments'); }}>
                  Turnamen
                </NavButton>
              </>
            )}
            {!isAdmin && rankingAvailable && (
              <NavButton active={currentPage === 'payment'} onClick={() => setCurrentPage('payment')}>
                2. Pembayaran
              </NavButton>
            )}
            <NavButton
              active={currentPage === 'teams'}
              onClick={() => setCurrentPage('teams')}
              disabled={!isAdmin && !teamAvailable}
            >
              {isAdmin ? 'Tim' : '3. Tim'}
            </NavButton>
            <NavButton
              active={currentPage === 'tournaments'}
              onClick={() => setCurrentPage('tournaments')}
            >
              Turnamen
            </NavButton>
          </div>
        </nav>

        <div className="animate-fade-in">
          {isAdmin && currentPage === 'admin' && (
            <AdminDashboard
              onNavigateToRankings={() => setCurrentPage('rankings')}
              onNavigateToTeams={() => setCurrentPage('teams')}
              onProcessParticipants={handleProcessParticipants}
              processing={processing}
              processError={processError}
              processSuccess={processSuccess}
            />
          )}
          {isAdmin && currentPage === 'admin-tournaments' && (
            <AdminTournamentsPage onNavigateToDetail={(id) => { setSelectedAdminTournamentId(id); setCurrentPage('admin-tournament-detail'); }} />
          )}
          {isAdmin && currentPage === 'admin-tournament-detail' && selectedAdminTournamentId && (
            <AdminTournamentDetailPage tournamentId={selectedAdminTournamentId} onBack={() => setCurrentPage('admin-tournaments')} />
          )}
          {currentPage === 'rankings' && <RankingsPage />}
          {currentPage === 'teams' && (
            <ResultsPage onBack={() => setCurrentPage('rankings')} isAdmin={isAdmin} />
          )}
          {currentPage === 'profile' && user && <ProfilePage token={user.token} />}
          {currentPage === 'payment' && user && <PaymentPage token={user.token} />}
          {currentPage === 'tournaments' && <TournamentsListPage onNavigateToDetail={(id) => { setSelectedTournamentId(id); setCurrentPage('tournament-detail'); }} />}
          {currentPage === 'tournament-detail' && selectedTournamentId && (
            <TournamentDetailPage tournamentId={selectedTournamentId} onBack={() => setCurrentPage('tournaments')} />
          )}
        </div>
      </div>
    </main>
  )
}

function NavButton({
  active,
  onClick,
  disabled,
  children,
}: {
  active: boolean
  onClick: () => void
  disabled?: boolean
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`rounded-xl px-5 py-2 text-sm font-semibold transition-all duration-200 ${
        active
          ? 'brand-gradient text-white shadow-brand'
          : disabled
          ? 'cursor-not-allowed text-gray-600'
          : 'text-gray-400 hover:text-white hover:bg-white/5'
      }`}
    >
      {children}
    </button>
  )
}
