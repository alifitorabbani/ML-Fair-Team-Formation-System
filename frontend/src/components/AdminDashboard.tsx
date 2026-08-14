'use client'

import { useState, useEffect } from 'react'
import { isAdminError, clearSession } from '@/lib/api'
import {
  adminGetDashboard,
  adminGenerateRanking,
  adminRankingPreview,
  adminConfirmRanking,
  adminGenerateTeam,
  adminVerifyPayment,
  adminDeletePayment,
  adminGetPayments,
  adminGetAuditLog,
  adminGetRankingVersions,
  adminGetTeamVersions,
} from '@/lib/api'
import { AdminDashboardStats, PaymentResponse, AuditLogResponse, RankingVersionResponse, TeamVersionResponse } from '@/types'
import { Trophy, Users, Mail, DollarSign, Shield, Activity, RefreshCw, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react'
import Card from '@/components/shared/Card'
import ErrorMessage from '@/components/shared/ErrorMessage'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import { SystemStateBadge } from '@/components/shared/StatusBadge'
import { useAuthToken } from '@/lib/hooks/useAuth'

type Tab = 'overview' | 'rankings' | 'teams' | 'payments' | 'audit'

export default function AdminDashboard({
  onNavigateToRankings,
  onNavigateToTeams,
  onProcessParticipants,
  processing,
  processError,
  processSuccess,
}: {
  onNavigateToRankings: () => void
  onNavigateToTeams: () => void
  onProcessParticipants: () => void
  processing: boolean
  processError: string | null
  processSuccess: string | null
}) {
  const token = useAuthToken()
  const [stats, setStats] = useState<AdminDashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [generatingRanking, setGeneratingRanking] = useState(false)
  const [generatingTeam, setGeneratingTeam] = useState(false)
  const [rankingPreview, setRankingPreview] = useState<any>(null)
  const [payments, setPayments] = useState<PaymentResponse[]>([])
  const [auditLogs, setAuditLogs] = useState<AuditLogResponse[]>([])
  const [rankingVersions, setRankingVersions] = useState<RankingVersionResponse[]>([])
  const [teamVersions, setTeamVersions] = useState<TeamVersionResponse[]>([])
  const [activeTab, setActiveTab] = useState<Tab>('overview')
  const [verifyPlayerId, setVerifyPlayerId] = useState('')
  const [verifyStatus, setVerifyStatus] = useState('PAID')
  const [verifyNotes, setVerifyNotes] = useState('')
  const [verifyTransactionId, setVerifyTransactionId] = useState('')
  const [verifyError, setVerifyError] = useState<string | null>(null)
  const [verifySuccess, setVerifySuccess] = useState<string | null>(null)
  const unpaidCount = payments.filter((p) => p.status !== 'PAID').length

  const loadDashboard = async () => {
    setLoading(true)
    try {
      const [dashboardRes, paymentsRes, auditRes, rankingVersionsRes, teamVersionsRes] = await Promise.all([
        adminGetDashboard(token || ''),
        adminGetPayments(token || ''),
        adminGetAuditLog(token || ''),
        adminGetRankingVersions(token || ''),
        adminGetTeamVersions(token || ''),
      ])
      setStats(dashboardRes)
      setPayments(paymentsRes.payments || [])
      setAuditLogs(auditRes.logs || [])
      setRankingVersions(rankingVersionsRes.versions || [])
      setTeamVersions(teamVersionsRes.versions || [])
    } catch (err) {
      console.error('Failed to load dashboard:', err)
      if (isAdminError(err)) {
        clearSession()
        window.location.reload()
      }
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (token) {
      loadDashboard()
    }
  }, [token])

  const handleAdminError = (err: unknown) => {
    if (isAdminError(err)) {
      clearSession()
      window.location.reload()
      return true
    }
    return false
  }

  const handlePreviewRanking = async () => {
    setGeneratingRanking(true)
    try {
      const preview = await adminRankingPreview(token || '')
      setRankingPreview(preview)
    } catch (err) {
      if (!handleAdminError(err)) {
        alert(err instanceof Error ? err.message : 'Gagal membuat preview ranking')
      }
    } finally {
      setGeneratingRanking(false)
    }
  }

  const handleConfirmRanking = async () => {
    if (!rankingPreview) return
    try {
      const rankingVersionId = (rankingPreview as any).ranking_version_id || ''
      if (!rankingVersionId) {
        alert('Ranking version ID tidak ditemukan. Silakan generate ranking ulang.')
        return
      }
      await adminConfirmRanking(token || '', rankingVersionId)
      alert('Ranking berhasil dikonfirmasi')
      setRankingPreview(null)
      loadDashboard()
      onNavigateToTeams()
    } catch (err) {
      if (!handleAdminError(err)) {
        alert(err instanceof Error ? err.message : 'Gagal mengkonfirmasi ranking')
      }
    }
  }

  const handleGenerateTeam = async () => {
    setGeneratingTeam(true)
    try {
      await adminGenerateTeam(token || '')
      alert('Tim berhasil digenerate')
      loadDashboard()
    } catch (err) {
      if (!handleAdminError(err)) {
        alert(err instanceof Error ? err.message : 'Gagal membuat tim')
      }
    } finally {
      setGeneratingTeam(false)
    }
  }

  const handleVerifyPayment = async () => {
    setVerifyError(null)
    setVerifySuccess(null)
    try {
      await adminVerifyPayment(token || '', verifyPlayerId, verifyStatus, verifyTransactionId, verifyNotes)
      setVerifySuccess('Pembayaran berhasil diverifikasi')
      setVerifyPlayerId('')
      setVerifyNotes('')
      setVerifyTransactionId('')
      loadDashboard()
    } catch (err) {
      if (!handleAdminError(err)) {
        setVerifyError(err instanceof Error ? err.message : 'Gagal memverifikasi pembayaran')
      }
    }
  }

  const handleVerifyPaymentFromTable = async (playerId: string) => {
    setVerifyError(null)
    setVerifySuccess(null)
    setVerifyPlayerId(playerId)
    setVerifyStatus('PAID')
    try {
      await adminVerifyPayment(token || '', playerId, 'PAID', '', 'Diverifikasi dari daftar pembayaran')
      setVerifySuccess(`Pembayaran ${playerId} berhasil diverifikasi`)
      setVerifyPlayerId('')
      setVerifyNotes('')
      setVerifyTransactionId('')
      loadDashboard()
    } catch (err) {
      if (!handleAdminError(err)) {
        setVerifyError(err instanceof Error ? err.message : 'Gagal memverifikasi pembayaran')
      }
    }
  }

  const handleDeletePayment = async (paymentId: string, playerId: string) => {
    if (!window.confirm(`Hapus pembayaran untuk ${playerId}? User tidak akan bisa mengakses tim.`)) return
    try {
      await adminDeletePayment(token || '', paymentId)
      loadDashboard()
    } catch (err) {
      if (!handleAdminError(err)) {
        alert(err instanceof Error ? err.message : 'Gagal menghapus pembayaran')
      }
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <LoadingSpinner text="Memuat dashboard..." />
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="flex items-center justify-center py-20">
        <ErrorMessage title="Error" message="Gagal memuat data dashboard" />
      </div>
    )
  }

  const tabs: { key: Tab; label: string; icon: React.ReactNode }[] = [
    { key: 'overview', label: 'Ringkasan', icon: <Activity className="h-4 w-4" /> },
    { key: 'rankings', label: 'Perankingan', icon: <Trophy className="h-4 w-4" /> },
    { key: 'teams', label: 'Tim', icon: <Users className="h-4 w-4" /> },
    { key: 'payments', label: 'Pembayaran', icon: <DollarSign className="h-4 w-4" /> },
    { key: 'audit', label: 'Audit', icon: <Shield className="h-4 w-4" /> },
  ]

  return (
    <div className="animate-fade-in space-y-6">
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard title="Total Peserta" value={stats.total_participants} sub={`${stats.processed_participants} diproses`} icon={<Users className="h-5 w-5" />} />
        <StatCard title="Lolos" value={stats.qualified_count} sub={`${stats.eliminated_count} gugur`} icon={<Trophy className="h-5 w-5" />} color="green" />
        <StatCard title="Tim Dibentuk" value={stats.total_teams || '-'} sub={stats.team_generated ? 'Aktif' : 'Belum'} icon={<Shield className="h-5 w-5" />} color="brand" />
        <StatCard title="Pembayaran" value={stats.payment_pending_count} sub={`${stats.payment_verified_count} terverifikasi`} icon={<DollarSign className="h-5 w-5" />} color="amber" />
      </div>

      {processError && <ErrorMessage title="Error" message={processError} />}
      {processSuccess && <ErrorMessage title="Berhasil" message={processSuccess} variant="success" />}

      <div className="flex flex-wrap items-center gap-2 rounded-2xl border border-white/10 bg-surface-900/60 p-1.5">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium transition ${
              activeTab === tab.key ? 'brand-gradient text-white shadow-brand' : 'text-gray-400 hover:text-white hover:bg-white/5'
            }`}
          >
            {tab.icon}
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === 'overview' && (
        <Card>
          <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-bold text-white">Status Sistem</h2>
              <p className="text-xs text-gray-400">Workflow dan aksi yang tersedia saat ini</p>
            </div>
            <SystemStateBadge state={stats.system_state} />
          </div>

          <div className="mb-6 grid grid-cols-1 gap-3 md:grid-cols-3">
            <ActionCard
              title="Proses Peserta"
              description="Muat dan proses database peserta dari CSV"
              onClick={onProcessParticipants}
              loading={processing}
              icon={<RefreshCw className="h-5 w-5" />}
            />
            <ActionCard
              title="Generate Ranking"
              description="Buat preview perankingan peserta"
              onClick={handlePreviewRanking}
              loading={generatingRanking}
              icon={<Trophy className="h-5 w-5" />}
            />
            <ActionCard
              title="Generate Tim"
              description="Bentuk tim berdasarkan ranking yang dikonfirmasi"
              onClick={handleGenerateTeam}
              loading={generatingTeam}
              icon={<Users className="h-5 w-5" />}
              disabled={!stats.ranking_generated}
              badge={
                unpaidCount > 0 ? (
                  <span className="inline-flex items-center gap-1 rounded-lg border border-amber-500/30 bg-amber-500/10 px-2 py-1 text-xs text-amber-300">
                    <AlertTriangle className="h-3 w-3" />
                    {unpaidCount} peserta belum bayar
                  </span>
                ) : null
              }
            />
          </div>

          {rankingPreview && (
            <div className="animate-slide-up rounded-xl border border-brand-500/20 bg-brand-950/30 p-5">
              <div className="mb-4 flex items-center justify-between">
                <h3 className="font-semibold text-brand-200">Preview Ranking</h3>
                <span className="text-xs text-gray-400">{(rankingPreview as any).preview_generated_at}</span>
              </div>
              <div className="mb-4 grid grid-cols-3 gap-3 text-center">
                <div className="rounded-lg border border-white/5 bg-surface-950/60 p-3">
                  <p className="text-xs text-gray-400">Total</p>
                  <p className="text-lg font-bold text-white">{(rankingPreview as any).total}</p>
                </div>
                <div className="rounded-lg border border-white/5 bg-surface-950/60 p-3">
                  <p className="text-xs text-gray-400">Lolos</p>
                  <p className="text-lg font-bold text-green-400">{(rankingPreview as any).qualified_count}</p>
                </div>
                <div className="rounded-lg border border-white/5 bg-surface-950/60 p-3">
                  <p className="text-xs text-gray-400">Gugur</p>
                  <p className="text-lg font-bold text-brand-400">{(rankingPreview as any).eliminated_count}</p>
                </div>
              </div>
              <div className="flex gap-3">
                <button
                  onClick={handleConfirmRanking}
                  className="brand-gradient flex-1 rounded-xl py-2.5 text-sm font-semibold text-white shadow-brand"
                >
                  Konfirmasi Ranking
                </button>
                <button
                  onClick={() => setRankingPreview(null)}
                  className="flex-1 rounded-xl border border-white/10 bg-surface-900/60 py-2.5 text-sm font-semibold text-gray-300 transition hover:bg-white/5"
                >
                  Batal
                </button>
              </div>
            </div>
          )}
        </Card>
      )}

      {activeTab === 'rankings' && (
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Versi Ranking</h2>
            <button onClick={loadDashboard} className="text-xs text-gray-400 transition hover:text-white">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase text-gray-400">
                  <th className="pb-3 pt-1 font-medium">ID</th>
                  <th className="pb-3 pt-1 font-medium">Status</th>
                  <th className="pb-3 pt-1 font-medium">Peserta</th>
                  <th className="pb-3 pt-1 font-medium">Lolos</th>
                  <th className="pb-3 pt-1 font-medium">Dibuat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {rankingVersions.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-sm text-gray-500">
                      Belum ada versi ranking
                    </td>
                  </tr>
                )}
                {rankingVersions.map((v) => (
                  <tr key={v.id} className="transition hover:bg-white/5">
                    <td className="py-3 pr-4 font-mono text-xs text-gray-300">{v.id.slice(0, 8)}...</td>
                    <td className="py-3 pr-4">
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${v.status === 'CONFIRMED' ? 'border-green-500/30 bg-green-500/10 text-green-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300'}`}>
                        {v.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-gray-300">{v.total_participants}</td>
                    <td className="py-3 pr-4 text-gray-300">{v.qualified_count}</td>
                    <td className="py-3 text-xs text-gray-400">{new Date(v.generated_at).toLocaleString('id-ID')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeTab === 'teams' && (
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Versi Tim</h2>
            <button onClick={loadDashboard} className="text-xs text-gray-400 transition hover:text-white">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase text-gray-400">
                  <th className="pb-3 pt-1 font-medium">ID</th>
                  <th className="pb-3 pt-1 font-medium">Status</th>
                  <th className="pb-3 pt-1 font-medium">Tim</th>
                  <th className="pb-3 pt-1 font-medium">Peserta</th>
                  <th className="pb-3 pt-1 font-medium">Keberadilan</th>
                  <th className="pb-3 pt-1 font-medium">Dibuat</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {teamVersions.length === 0 && (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-sm text-gray-500">
                      Belum ada versi tim
                    </td>
                  </tr>
                )}
                {teamVersions.map((v) => (
                  <tr key={v.id} className="transition hover:bg-white/5">
                    <td className="py-3 pr-4 font-mono text-xs text-gray-300">{v.id.slice(0, 8)}...</td>
                    <td className="py-3 pr-4">
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${v.status === 'CONFIRMED' ? 'border-green-500/30 bg-green-500/10 text-green-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300'}`}>
                        {v.status}
                      </span>
                    </td>
                    <td className="py-3 pr-4 text-gray-300">{v.total_teams}</td>
                    <td className="py-3 pr-4 text-gray-300">{v.total_participants}</td>
                    <td className="py-3 pr-4 text-gray-300">{v.overall_fairness?.toFixed(1) ?? '-'}</td>
                    <td className="py-3 text-xs text-gray-400">{new Date(v.generated_at).toLocaleString('id-ID')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {activeTab === 'payments' && (
        <Card>
          <h2 className="mb-4 text-lg font-bold text-white">Verifikasi Pembayaran</h2>
          <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-300">Player ID</label>
              <input
                value={verifyPlayerId}
                onChange={(e) => setVerifyPlayerId(e.target.value)}
                placeholder="P001"
                className="w-full rounded-xl border border-white/10 bg-surface-950/60 px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-brand-500"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-300">Status</label>
              <select
                value={verifyStatus}
                onChange={(e) => setVerifyStatus(e.target.value)}
                className="w-full rounded-xl border border-white/10 bg-surface-950/60 px-3 py-2 text-sm text-white outline-none focus:border-brand-500"
              >
                <option value="PAID">PAID</option>
                <option value="FAILED">FAILED</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-300">Transaction ID</label>
              <input
                value={verifyTransactionId}
                onChange={(e) => setVerifyTransactionId(e.target.value)}
                placeholder="Opsional"
                className="w-full rounded-xl border border-white/10 bg-surface-950/60 px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-brand-500"
              />
            </div>
          </div>
          <div className="mb-4">
            <label className="mb-1 block text-xs font-medium text-gray-300">Catatan</label>
            <textarea
              value={verifyNotes}
              onChange={(e) => setVerifyNotes(e.target.value)}
              placeholder="Catatan verifikasi..."
              className="w-full rounded-xl border border-white/10 bg-surface-950/60 px-3 py-2 text-sm text-white placeholder-gray-500 outline-none focus:border-brand-500"
            />
          </div>
          {verifyError && <div className="mb-4"><ErrorMessage title="Error" message={verifyError} /></div>}
          {verifySuccess && <div className="mb-4"><ErrorMessage title="Berhasil" message={verifySuccess} variant="success" /></div>}
          <button
            onClick={handleVerifyPayment}
            className="brand-gradient rounded-xl px-5 py-2.5 text-sm font-semibold text-white shadow-brand transition hover:opacity-90"
          >
            Verifikasi Pembayaran
          </button>

          <div className="mt-8">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-gray-300">Daftar Pembayaran</h3>
              <button onClick={loadDashboard} className="text-xs text-gray-400 transition hover:text-white">
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-xs uppercase text-gray-400">
                    <th className="pb-3 pt-1 font-medium">Pemain</th>
                    <th className="pb-3 pt-1 font-medium">Username</th>
                    <th className="pb-3 pt-1 font-medium">Rank</th>
                    <th className="pb-3 pt-1 font-medium">Status</th>
                    <th className="pb-3 pt-1 font-medium">Jumlah</th>
                    <th className="pb-3 pt-1 font-medium">Metode</th>
                    <th className="pb-3 pt-1 font-medium">Dibayar</th>
                    <th className="pb-3 pt-1 font-medium">Diverifikasi</th>
                    <th className="pb-3 pt-1 font-medium">Aksi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {payments.length === 0 && (
                    <tr>
                      <td colSpan={9} className="py-8 text-center text-sm text-gray-500">
                        Belum ada data pembayaran
                      </td>
                    </tr>
                  )}
                  {payments.map((p) => (
                    <tr key={p.id} className="transition hover:bg-white/5">
                      <td className="py-3 pr-4">
                        <div>
                          <p className="font-medium text-white">{p.player_name || p.player_id}</p>
                          <p className="text-xs text-gray-500">{p.player_email}</p>
                        </div>
                      </td>
                      <td className="py-3 pr-4 text-xs text-gray-300">@{p.player_username || '-'}</td>
                      <td className="py-3 pr-4">
                        <div>
                          <p className="text-xs text-gray-300">{p.current_rank || '-'}</p>
                          <p className="text-xs text-gray-500">⭐ {p.current_stars || 0}</p>
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs ${p.status === 'PAID' ? 'border-green-500/30 bg-green-500/10 text-green-300' : p.status === 'FAILED' ? 'border-brand-500/30 bg-brand-500/10 text-brand-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300'}`}>
                          {p.status}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-gray-300">{p.amount ? `Rp ${p.amount.toLocaleString('id-ID')}` : '-'}</td>
                      <td className="py-3 pr-4 text-gray-300">{p.method || '-'}</td>
                      <td className="py-3 pr-4 text-xs text-gray-400">{p.paid_at ? new Date(p.paid_at).toLocaleString('id-ID') : '-'}</td>
                      <td className="py-3 text-xs text-gray-400">{p.verified_at ? new Date(p.verified_at).toLocaleString('id-ID') : '-'}</td>
                      <td className="py-3">
                        <div className="flex items-center gap-2">
                          {p.status !== 'PAID' ? (
                            <button
                              onClick={() => handleVerifyPaymentFromTable(p.player_id)}
                              className="rounded-lg border border-green-500/30 bg-green-500/10 px-3 py-1.5 text-xs font-semibold text-green-300 transition hover:bg-green-500/20"
                            >
                              Verifikasi
                            </button>
                          ) : (
                            <span className="text-xs text-green-400">Terverifikasi</span>
                          )}
                          <button
                            onClick={() => handleDeletePayment(p.id, p.player_id)}
                            className="rounded-lg border border-red-500/30 bg-red-500/10 px-3 py-1.5 text-xs font-semibold text-red-300 transition hover:bg-red-500/20"
                          >
                            Hapus
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </Card>
      )}

      {activeTab === 'audit' && (
        <Card>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-bold text-white">Log Audit</h2>
            <button onClick={loadDashboard} className="text-xs text-gray-400 transition hover:text-white">
              <RefreshCw className="h-4 w-4" />
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/10 text-xs uppercase text-gray-400">
                  <th className="pb-3 pt-1 font-medium">Aksi</th>
                  <th className="pb-3 pt-1 font-medium">Actor</th>
                  <th className="pb-3 pt-1 font-medium">Waktu</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {auditLogs.length === 0 && (
                  <tr>
                    <td colSpan={3} className="py-8 text-center text-sm text-gray-500">
                      Belum ada log audit
                    </td>
                  </tr>
                )}
                {auditLogs.map((log) => (
                  <tr key={log.id} className="transition hover:bg-white/5">
                    <td className="py-3 pr-4 font-medium text-white">{log.action}</td>
                    <td className="py-3 pr-4 text-gray-300">{log.actor}</td>
                    <td className="py-3 text-xs text-gray-400">{new Date(log.timestamp).toLocaleString('id-ID')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  )
}

function StatCard({
  title,
  value,
  sub,
  icon,
  color = 'brand',
}: {
  title: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  color?: 'brand' | 'green' | 'amber' | 'blue'
}) {
  const colorMap = {
    brand: 'text-brand-400 bg-brand-500/10',
    green: 'text-green-400 bg-green-500/10',
    amber: 'text-amber-400 bg-amber-500/10',
    blue: 'text-blue-400 bg-blue-500/10',
  }

  return (
    <Card hover className="group">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-gray-400">{title}</p>
          <p className="mt-1 text-2xl font-bold text-white">{value}</p>
          {sub && <p className="mt-1 text-xs text-gray-500">{sub}</p>}
        </div>
        <div className={`rounded-xl p-2.5 ${colorMap[color]}`}>{icon}</div>
      </div>
    </Card>
  )
}

function ActionCard({
  title,
  description,
  onClick,
  loading,
  icon,
  disabled,
  badge,
}: {
  title: string
  description: string
  onClick: () => void
  loading: boolean
  icon: React.ReactNode
  disabled?: boolean
  badge?: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      disabled={loading || disabled}
      className="group rounded-xl border border-white/10 bg-surface-950/60 p-4 text-left transition hover:border-brand-500/40 hover:bg-brand-950/20 disabled:cursor-not-allowed disabled:opacity-50"
    >
      <div className="flex items-start justify-between">
        <div className="rounded-lg bg-brand-500/10 p-2 text-brand-400 transition group-hover:bg-brand-500/20">{icon}</div>
        {loading && <div className="h-4 w-4 rounded-full border-2 border-brand-500/30 border-t-brand-500 animate-spin" />}
      </div>
      <h3 className="mt-3 text-sm font-semibold text-white">{title}</h3>
      <p className="mt-1 text-xs text-gray-400">{description}</p>
      {badge && <div className="mt-2">{badge}</div>}
    </button>
  )
}
