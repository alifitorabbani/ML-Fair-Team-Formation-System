'use client'

import { useState, useEffect } from 'react'
import { getMyRanking, getMyPayment, submitPayment, getPaymentStatus } from '@/lib/api'
import { DollarSign, Clock, CheckCircle, XCircle, Upload, Wallet } from 'lucide-react'
import LoadingSpinner from '@/components/shared/LoadingSpinner'
import ErrorMessage from '@/components/shared/ErrorMessage'
import Card from '@/components/shared/Card'
import { StatusBadge } from '@/components/shared/StatusBadge'
import { useAuthToken } from '@/lib/hooks/useAuth'

export default function PaymentPage({ token: propToken }: { token?: string } = {}) {
  const token = propToken || useAuthToken()
  const [payment, setPayment] = useState<any>(null)
  const [playerRank, setPlayerRank] = useState<any>(null)
  const [paymentStatus, setPaymentStatus] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [proofFile, setProofFile] = useState<File | null>(null)
  const [notes, setNotes] = useState('')
  const [uploadSuccess, setUploadSuccess] = useState(false)

  useEffect(() => {
    if (!token) return

    const load = async () => {
      try {
        setLoading(true)
        const [paymentData, rankingData, statusData] = await Promise.all([
          getMyPayment(token).catch(() => null),
          getMyRanking(token).catch(() => null),
          getPaymentStatus(token).catch(() => null),
        ])
        setPayment(paymentData)
        setPlayerRank(rankingData)
        setPaymentStatus(statusData)
      } catch {
        setError('Gagal memuat data pembayaran')
      } finally {
        setLoading(false)
      }
    }

    load()
  }, [token])

  const handleSubmit = async () => {
    if (!proofFile || !token) return
    try {
      setUploading(true)
      const result = await submitPayment(token, proofFile, notes)
      setPayment(result)
      setProofFile(null)
      setNotes('')
      setUploadSuccess(true)
      const refreshed = await getPaymentStatus(token).catch(() => null)
      if (refreshed) setPaymentStatus(refreshed)
      setTimeout(() => setUploadSuccess(false), 4000)
    } catch {
      setError('Gagal mengupload bukti pembayaran')
    } finally {
      setUploading(false)
    }
  }

  if (loading) {
    return (
      <Card>
        <LoadingSpinner text="Memuat pembayaran..." />
      </Card>
    )
  }

  if (error) {
    return (
      <Card>
        <ErrorMessage title="Error" message={error} />
      </Card>
    )
  }

  const isQualified = playerRank?.player?.status === 'QUALIFIED'
  const isPaid = payment?.status === 'PAID'
  const isFailed = payment?.status === 'FAILED'
  const isPending = payment?.status === 'PENDING' || !payment?.status

  return (
    <div className="animate-fade-in space-y-6">
      <Card>
        <div className="mb-6 flex items-center gap-3">
          <div className="rounded-xl bg-brand-600/10 p-2.5 text-brand-400">
            <DollarSign className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-white">Pembayaran</h2>
            <p className="text-xs text-gray-400">Status dan instruksi pembayaran</p>
          </div>
        </div>

        {paymentStatus && (
          <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
            <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4 text-center">
              <p className="text-xs text-gray-400">Status Pembayaran</p>
              <div className="mt-2 flex justify-center">
                <StatusBadge status={payment?.status || 'PENDING'} />
              </div>
            </div>
            <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4 text-center">
              <p className="text-xs text-gray-400">Total Terverifikasi</p>
              <p className="mt-1 text-lg font-bold text-white">{paymentStatus.paid_count}/{paymentStatus.total_qualified}</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4 text-center">
              <p className="text-xs text-gray-400">Menunggu</p>
              <p className="mt-1 text-lg font-bold text-amber-400">{paymentStatus.pending_count}</p>
            </div>
            <div className="rounded-xl border border-white/5 bg-surface-950/60 p-4 text-center">
              <p className="text-xs text-gray-400">Nominal</p>
              <p className="mt-1 text-lg font-bold text-white">Rp {paymentStatus.payment_amount?.toLocaleString('id-ID') || '20.000'}</p>
            </div>
          </div>
        )}

        {isQualified && isPending && (
          <div className="animate-slide-up rounded-xl border border-amber-500/30 bg-amber-500/10 p-5">
            <div className="mb-3 flex items-center gap-2">
              <Wallet className="h-5 w-5 text-amber-400" />
              <h3 className="font-semibold text-amber-200">Instruksi Pembayaran</h3>
            </div>
            <div className="mb-4 grid grid-cols-1 gap-3 text-sm md:grid-cols-2">
              <div>
                <p className="text-xs text-gray-400">Metode</p>
                <p className="font-medium text-white">{paymentStatus?.payment_method || 'E-Money Dana/Link'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Nomor Rekening</p>
                <p className="font-medium text-white">{paymentStatus?.payment_account_number || '082141233543'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Atas Nama</p>
                <p className="font-medium text-white">{paymentStatus?.payment_account_name || 'Muhammad Syofiudin'}</p>
              </div>
              <div>
                <p className="text-xs text-gray-400">Jumlah</p>
                <p className="font-medium text-white">Rp {paymentStatus?.payment_amount?.toLocaleString('id-ID') || '20.000'}</p>
              </div>
            </div>

            <div className="rounded-xl border border-white/10 bg-surface-950/60 p-4">
              <p className="mb-2 text-sm font-semibold text-white">Upload Bukti Pembayaran</p>
              <input
                type="file"
                accept="image/*"
                onChange={(e) => setProofFile(e.target.files?.[0] || null)}
                className="mb-3 block w-full text-sm text-gray-400 file:mr-4 file:rounded-xl file:border-0 file:bg-brand-600 file:px-4 file:py-2 file:text-sm file:font-semibold file:text-white hover:file:bg-brand-500"
              />
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="Catatan (opsional)"
                className="mb-3 w-full rounded-xl border border-white/10 bg-surface-950/60 p-3 text-sm text-white placeholder-gray-500 outline-none transition focus:border-brand-500"
                rows={2}
              />
              <button
                onClick={handleSubmit}
                disabled={!proofFile || uploading}
                className="inline-flex items-center gap-2 rounded-xl border border-white/10 bg-surface-900/60 px-4 py-2 text-sm font-semibold text-gray-300 transition hover:border-brand-500/40 hover:text-white disabled:opacity-50"
              >
                {uploading ? (
                  <>
                    <div className="h-4 w-4 animate-spin rounded-full border-2 border-white/20 border-t-white" />
                    Mengupload...
                  </>
                ) : (
                  <>
                    <Upload className="h-4 w-4" />
                    Upload Bukti Pembayaran
                  </>
                )}
              </button>
              {uploadSuccess && (
                <div className="animate-fade-in mt-4 flex items-center gap-3 rounded-xl border border-green-500/30 bg-green-500/10 p-4">
                  <CheckCircle className="h-5 w-5 text-green-400" />
                  <div>
                    <p className="text-sm font-semibold text-green-200">Bukti pembayaran berhasil diupload</p>
                    <p className="text-xs text-green-300/80">Silakan tunggu admin memverifikasi pembayaran Anda.</p>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {isPaid && (
          <div className="flex items-center gap-3 rounded-xl border border-green-500/30 bg-green-500/10 p-4">
            <CheckCircle className="h-5 w-5 text-green-400" />
            <p className="text-sm text-green-200">Pembayaran Anda telah diverifikasi. Tim akan segera ditampilkan.</p>
          </div>
        )}

        {isFailed && (
          <div className="flex items-center gap-3 rounded-xl border border-brand-500/30 bg-brand-500/10 p-4">
            <XCircle className="h-5 w-5 text-brand-400" />
            <p className="text-sm text-brand-200">Pembayaran gagal. Silakan hubungi admin untuk informasi lebih lanjut.</p>
          </div>
        )}

        {isPending && !isQualified && (
          <div className="flex items-center gap-3 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
            <Clock className="h-5 w-5 text-amber-400" />
            <p className="text-sm text-amber-200">Anda belum lolos kualifikasi. Pembayaran hanya bisa dilakukan setelah lolos kualifikasi.</p>
          </div>
        )}
      </Card>
    </div>
  )
}