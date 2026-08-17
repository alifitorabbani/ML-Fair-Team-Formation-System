'use client'

import { useState, useEffect } from 'react'
import { adminListTournaments, adminDeleteTournament, adminCreateTournament } from '@/lib/tournamentApi'
import { useAuthToken } from '@/lib/hooks/useAuth'
import { TournamentResponse } from '@/types'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import { Plus, Trash2, Trophy } from 'lucide-react'

export default function AdminTournamentsPage({ onNavigateToDetail }: { onNavigateToDetail: (id: string) => void }) {
  const token = useAuthToken()
  const [tournaments, setTournaments] = useState<TournamentResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [newName, setNewName] = useState('')
  const [creating, setCreating] = useState(false)

  const load = async () => {
    if (!token) return
    setLoading(true)
    setError(null)
    try {
      const data = await adminListTournaments(token)
      setTournaments(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal memuat turnamen')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [token])

  const handleCreate = async () => {
    if (!token || !newName.trim()) return
    setCreating(true)
    try {
      await adminCreateTournament(token, {
        name: newName.trim(),
        description: '',
        timezone: 'Asia/Jakarta',
        dates: [{ date: new Date().toISOString().split('T')[0], start_time: '18:00:00', end_time: '23:00:00', match_duration_minutes: 45, buffer_minutes: 0, min_rest_minutes: 60 }],
        group_count: 4,
        teams_per_group: 4,
        qualification_count: 2,
      })
      setNewName('')
      setShowCreate(false)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal membuat turnamen')
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!token) return
    if (!confirm('Hapus turnamen ini?')) return
    try {
      await adminDeleteTournament(token, id)
      load()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Gagal menghapus turnamen')
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner text="Memuat turnamen..." />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">Manajemen Turnamen</h2>
          <p className="mt-1 text-sm text-gray-400">Buat dan kelola turnamen</p>
        </div>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-2 rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500"
        >
          <Plus className="h-4 w-4" />
          Buat Turnamen
        </button>
      </div>

      {error && <ErrorMessage title="Error" message={error} />}

      {showCreate && (
        <Card>
          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-300">Nama Turnamen</label>
              <input
                type="text"
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm text-white placeholder-gray-500 focus:border-brand-500 focus:outline-none"
                placeholder="Contoh: Turnamen Mobile Legends 2024"
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleCreate}
                disabled={creating || !newName.trim()}
                className="rounded-xl bg-brand-600 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-500 disabled:opacity-50"
              >
                {creating ? 'Membuat...' : 'Buat'}
              </button>
              <button
                onClick={() => setShowCreate(false)}
                className="rounded-xl border border-white/10 px-4 py-2 text-sm text-gray-400 hover:text-white"
              >
                Batal
              </button>
            </div>
          </div>
        </Card>
      )}

      {tournaments.length === 0 ? (
        <Card>
          <p className="text-center text-sm text-gray-400">Belum ada turnamen.</p>
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
              <div className="mt-4 flex items-center gap-2">
                <button
                  onClick={() => onNavigateToDetail(t.id)}
                  className="flex items-center gap-1 rounded-xl bg-brand-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-brand-500"
                >
                  <Trophy className="h-3 w-3" />
                  Kelola
                </button>
                <button
                  onClick={() => handleDelete(t.id)}
                  className="flex items-center gap-1 rounded-xl border border-red-500/30 px-3 py-1.5 text-xs font-medium text-red-400 hover:bg-red-500/10"
                >
                  <Trash2 className="h-3 w-3" />
                  Hapus
                </button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
