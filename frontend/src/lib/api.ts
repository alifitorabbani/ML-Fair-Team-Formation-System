import {
  LoginResponse,
  SystemStateResponse,
  AdminDashboardStats,
  PaymentResponse,
  RankingVersionResponse,
  TeamVersionResponse,
  AuditLogResponse,
} from '@/types'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? ''

function timeout<T>(ms: number, fn: (signal: AbortSignal) => Promise<T>): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), ms)
  return fn(controller.signal).finally(() => clearTimeout(timer))
}

async function fetchJSON(url: string, init?: RequestInit & { timeoutMs?: number }): Promise<any> {
  const { timeoutMs = 15_000, ...rest } = init || {}
  const response = await timeout(timeoutMs, (signal) =>
    fetch(url, { ...rest, signal }),
  )

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error((error as any)?.detail || `Request failed: ${response.status}`)
  }

  return response.json()
}

async function postJSON<T>(url: string, body: unknown, token?: string, timeoutMs = 15_000): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token) headers['X-User-Token'] = token

  return fetchJSON(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    timeoutMs,
  })
}

async function getJSON<T>(url: string, token?: string, timeoutMs = 15_000): Promise<T> {
  const headers: Record<string, string> = {}
  if (token) headers['X-User-Token'] = token

  return fetchJSON(url, {
    headers,
    timeoutMs,
  })
}

async function deleteJSON(url: string, token?: string, timeoutMs = 15_000): Promise<any> {
  const headers: Record<string, string> = {}
  if (token) headers['X-User-Token'] = token

  return fetchJSON(url, {
    method: 'DELETE',
    headers,
    timeoutMs,
  })
}

const SYSTEM_STATE_CACHE_KEY = 'system_state_cache'
const SYSTEM_STATE_CACHE_TTL_MS = 60_000

function getCachedSystemState(): SystemStateResponse | null {
  try {
    const raw = localStorage.getItem(SYSTEM_STATE_CACHE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { value: SystemStateResponse; expiresAt: number }
    if (Date.now() > parsed.expiresAt) {
      localStorage.removeItem(SYSTEM_STATE_CACHE_KEY)
      return null
    }
    return parsed.value
  } catch {
    return null
  }
}

function setCachedSystemState(value: SystemStateResponse) {
  try {
    localStorage.setItem(
      SYSTEM_STATE_CACHE_KEY,
      JSON.stringify({ value, expiresAt: Date.now() + SYSTEM_STATE_CACHE_TTL_MS }),
    )
  } catch {
    // ignore quota errors
  }
}

export async function login(email: string): Promise<LoginResponse> {
  return postJSON<LoginResponse>(`${API_BASE}/api/login`, { email })
}

export async function getSystemState(): Promise<SystemStateResponse> {
  const cached = getCachedSystemState()
  if (cached) return cached

  const data = await getJSON<SystemStateResponse>(`${API_BASE}/api/system-state`, undefined, 10_000)
  setCachedSystemState(data)
  return data
}

export async function getConfig(): Promise<any> {
  return getJSON(`${API_BASE}/api/config`)
}

export async function getMyRanking(token: string): Promise<{ rank: number; total: number; player: any }> {
  return getJSON(`${API_BASE}/api/me/ranking`, token)
}

export async function getMyTeam(token: string): Promise<{ team_id: string | null; team: any; message?: string }> {
  return getJSON(`${API_BASE}/api/me/team`, token)
}

export async function getMyPayment(token: string): Promise<PaymentResponse> {
  return getJSON(`${API_BASE}/api/me/payment`, token)
}

export async function adminProcessParticipants(token: string): Promise<{ message: string; count: number }> {
  return postJSON(`${API_BASE}/api/admin/process-participants`, {}, token)
}

export async function adminGenerateRanking(token: string, randomSeed?: number): Promise<any> {
  return postJSON(`${API_BASE}/api/admin/generate-ranking`, { random_seed: randomSeed }, token, 30_000)
}

export async function adminRankingPreview(token: string): Promise<any> {
  return getJSON(`${API_BASE}/api/admin/ranking-preview`, token, 20_000)
}

export async function adminGetRankings(token: string): Promise<any> {
  return getJSON(`${API_BASE}/api/admin/rankings`, token)
}

export async function adminConfirmRanking(token: string, rankingVersionId: string): Promise<any> {
  return postJSON(`${API_BASE}/api/admin/confirm-ranking?ranking_version_id=${encodeURIComponent(rankingVersionId)}`, {}, token)
}

export async function adminGenerateTeam(token: string, randomSeed?: number): Promise<any> {
  return postJSON(`${API_BASE}/api/admin/generate-team`, { random_seed: randomSeed }, token, 30_000)
}

export async function adminGetDashboard(token: string): Promise<AdminDashboardStats> {
  return getJSON(`${API_BASE}/api/admin/dashboard`, token)
}

export async function adminSeedPayments(token: string): Promise<{ inserted_count: number; total_qualified: number }> {
  return postJSON(`${API_BASE}/api/admin/seed-payments`, {}, token)
}

export async function adminSyncParticipants(token: string): Promise<{ deleted_count: number; inserted_count: number; updated_count: number; total_participants: number; team_regenerated: boolean; message: string }> {
  return postJSON(`${API_BASE}/api/admin/sync-participants`, {}, token, 30_000)
}

export async function adminVerifyPayment(token: string, playerId: string, status: string, transactionId?: string, notes?: string): Promise<any> {
  return postJSON(`${API_BASE}/api/admin/verify-payment`, { player_id: playerId, status, transaction_id: transactionId, notes }, token)
}

export async function adminGetPayments(token: string): Promise<{ payments: PaymentResponse[] }> {
  return getJSON(`${API_BASE}/api/admin/payments`, token)
}

export async function adminDeletePayment(token: string, paymentId: string): Promise<{ success: boolean }> {
  return deleteJSON(`${API_BASE}/api/admin/payments/${encodeURIComponent(paymentId)}`, token)
}

export async function adminGetAuditLog(token: string): Promise<{ logs: AuditLogResponse[] }> {
  return getJSON(`${API_BASE}/api/admin/audit-log`, token)
}

export async function adminGetRankingVersions(token: string): Promise<{ versions: RankingVersionResponse[] }> {
  return getJSON(`${API_BASE}/api/admin/ranking-versions`, token)
}

export async function adminGetTeamVersions(token: string): Promise<{ versions: TeamVersionResponse[] }> {
  return getJSON(`${API_BASE}/api/admin/team-versions`, token)
}

export async function adminGetTeamVersionDetail(
  token: string,
  versionId: string,
): Promise<any> {
  return getJSON(`${API_BASE}/api/admin/team-versions/${encodeURIComponent(versionId)}`, token)
}

export function isAdminError(err: unknown): boolean {
  return (
    typeof err === 'object' &&
    err !== null &&
    'message' in err &&
    typeof (err as any).message === 'string' &&
    ((err as any).message.toLowerCase().includes('forbidden') ||
      (err as any).message.toLowerCase().includes('unauthorized'))
  )
}

export function clearSession() {
  try {
    localStorage.removeItem('user_session')
  } catch {
    // ignore
  }
}

export async function submitPayment(token: string, proof: File, notes?: string): Promise<any> {
  const form = new FormData()
  form.append('proof', proof)
  if (notes) form.append('notes', notes)

  const headers: Record<string, string> = { 'X-User-Token': token }

  return timeout(15_000, (signal) =>
    fetch(`${API_BASE}/api/me/submit-payment`, {
      method: 'POST',
      headers,
      body: form,
      signal,
    }).then((response) => {
      if (!response.ok) {
        return response.json().then((error) => {
          throw new Error(error.detail || 'Failed to submit payment')
        })
      }
      return response.json()
    }),
  )
}

export async function getPaymentStatus(token: string): Promise<{
  total_qualified: number
  paid_count: number
  pending_count: number
  all_paid: boolean
  payment_amount: number
  payment_method: string
  payment_account_number: string
  payment_account_name: string
}> {
  return getJSON(`${API_BASE}/api/me/payment-status`, token)
}

export async function getAllRankings(token: string): Promise<{
  rankings: any[]
  total: number
  current_user_id: string
  current_role: string
}> {
  return getJSON(`${API_BASE}/api/rankings`, token)
}

export async function getAllTeams(token: string): Promise<{
  teams: any[]
  current_user_id: string
  current_role: string
  all_paid: boolean
  paid_count: number
  total_qualified: number
}> {
  return getJSON(`${API_BASE}/api/teams`, token)
}
