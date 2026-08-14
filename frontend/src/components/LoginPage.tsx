'use client'

import { useState } from 'react'
import { login } from '@/lib/api'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'

export default function LoginPage({ onLoginSuccess }: { onLoginSuccess: (session: any) => void }) {
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await login(email)
      const session = {
        token: data.token,
        player_id: data.player_id,
        email: data.email,
        username: data.username,
        full_name: data.full_name,
        name: data.name,
        role: data.role,
      }
      localStorage.setItem('user_session', JSON.stringify(session))
      onLoginSuccess(session)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login gagal')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="mx-auto max-w-md animate-fade-in">
      <div className="rounded-2xl border border-white/10 bg-surface-900/80 p-8 backdrop-blur-xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-600 shadow-brand">
            <span className="text-2xl">⚔️</span>
          </div>
          <h1 className="text-2xl font-bold text-white">Masuk</h1>
          <p className="mt-2 text-sm text-gray-400">Masukkan email untuk mengakses sistem</p>
        </div>

        {error && (
          <div className="mb-6">
            <ErrorMessage message={error} />
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label className="mb-1.5 block text-sm font-medium text-gray-300">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="nama@example.com"
              required
              className="w-full rounded-xl border border-white/10 bg-surface-950/60 px-4 py-2.5 text-sm text-white placeholder-gray-500 outline-none transition focus:border-brand-500 focus:ring-2 focus:ring-brand-500/20"
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="brand-gradient w-full rounded-xl py-3 text-sm font-semibold text-white shadow-brand transition hover:opacity-90 disabled:opacity-50"
          >
            {loading ? <LoadingSpinner text="Memverifikasi..." /> : 'Masuk'}
          </button>
        </form>
      </div>
    </div>
  )
}
