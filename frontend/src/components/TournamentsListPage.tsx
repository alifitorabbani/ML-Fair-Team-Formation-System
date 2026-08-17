'use client'

import { useState, useEffect } from 'react'
import { userListTournaments } from '@/lib/tournamentApi'
import { useAuthToken } from '@/lib/hooks/useAuth'
import { TournamentResponse } from '@/types'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'

export default function TournamentsListPage({ onNavigateToDetail }: { onNavigateToDetail: (id: string) => void }) {
  const token = useAuthToken()
  const [tournaments, setTournaments] = useState<TournamentResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!token) return
    setLoading(true)
    setError(null)
    userListTournaments(token)
      .then(setTournaments)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false))
  }, [token])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner text="Memuat turnamen..." />
      </div>
    )
  }

  if (error) {
    return <ErrorMessage title="Error" message={error} />
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold text-white">Turnamen</h2>
        <p className="mt-1 text-sm text-gray-400">Daftar turnamen yang tersedia</p>
      </div>
      {tournaments.length === 0 ? (
        <Card>
          <p className="text-center text-sm text-gray-400">Belum ada turnamen yang dibuat.</p>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {tournaments.map((t) => (
            <Card key={t.id} className="transition hover:border-brand-500/40">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-lg font-semibold text-white">{t.name}</h3>
                  <p className="mt-1 line-clamp-2 text-sm text-gray-400">{t.description}</p>
                </div>
                <span className="rounded-full bg-brand-500/10 px-2 py-1 text-xs font-medium text-brand-300">
                  {t.status}
                </span>
              </div>
              <div className="mt-4 flex items-center gap-2 text-xs text-gray-500">
                <span>Dibuat: {new Date(t.created_at).toLocaleDateString('id-ID')}</span>
              </div>
              <button
                onClick={() => onNavigateToDetail(t.id)}
                className="mt-4 rounded-xl bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-500"
              >
                Lihat Detail
              </button>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
