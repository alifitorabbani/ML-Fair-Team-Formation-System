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

export async function login(email: string): Promise<LoginResponse> {
  const response = await fetch(`${API_BASE}/api/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ email }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Login failed')
  }

  return response.json()
}

export async function getSystemState(): Promise<SystemStateResponse> {
  const response = await fetch(`${API_BASE}/api/system-state`)

  if (!response.ok) {
    throw new Error('Failed to fetch system state')
  }

  return response.json()
}

export async function getConfig(): Promise<any> {
  const response = await fetch(`${API_BASE}/api/config`)

  if (!response.ok) {
    throw new Error('Failed to fetch config')
  }

  return response.json()
}

export async function getMyRanking(token: string): Promise<{ rank: number; total: number; player: any }> {
  const response = await fetch(`${API_BASE}/api/me/ranking`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch ranking')
  }

  return response.json()
}

export async function getMyTeam(token: string): Promise<{ team_id: string | null; team: any; message?: string }> {
  const response = await fetch(`${API_BASE}/api/me/team`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch team')
  }

  return response.json()
}

export async function getMyPayment(token: string): Promise<PaymentResponse> {
  const response = await fetch(`${API_BASE}/api/me/payment`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch payment')
  }

  return response.json()
}

export async function adminProcessParticipants(token: string): Promise<{ message: string; count: number }> {
  const response = await fetch(`${API_BASE}/api/admin/process-participants`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify({}),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Gagal memproses peserta')
  }

  return response.json()
}

export async function adminGenerateRanking(token: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/generate-ranking`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify({}),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to generate ranking')
  }

  return response.json()
}

export async function adminRankingPreview(token: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/ranking-preview`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to get ranking preview')
  }

  return response.json()
}

export async function adminConfirmRanking(token: string, rankingVersionId: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/confirm-ranking?ranking_version_id=${rankingVersionId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to confirm ranking')
  }

  return response.json()
}

export async function adminGenerateTeam(token: string, randomSeed?: number): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/generate-team`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify({ random_seed: randomSeed }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to generate team')
  }

  return response.json()
}

export async function adminGetDashboard(token: string): Promise<AdminDashboardStats> {
  const response = await fetch(`${API_BASE}/api/admin/dashboard`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch dashboard')
  }

  return response.json()
}

export async function adminVerifyPayment(token: string, playerId: string, status: string, transactionId?: string, notes?: string): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/verify-payment`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Token': token,
    },
    body: JSON.stringify({ player_id: playerId, status, transaction_id: transactionId, notes }),
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to verify payment')
  }

  return response.json()
}

export async function adminGetPayments(token: string): Promise<{ payments: PaymentResponse[] }> {
  const response = await fetch(`${API_BASE}/api/admin/payments`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch payments')
  }

  return response.json()
}

export async function adminDeletePayment(token: string, paymentId: string): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE}/api/admin/payments/${encodeURIComponent(paymentId)}`, {
    method: 'DELETE',
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to delete payment')
  }

  return response.json()
}

export async function adminGetAuditLog(token: string): Promise<{ logs: AuditLogResponse[] }> {
  const response = await fetch(`${API_BASE}/api/admin/audit-log`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch audit log')
  }

  return response.json()
}

export async function adminGetRankingVersions(token: string): Promise<{ versions: RankingVersionResponse[] }> {
  const response = await fetch(`${API_BASE}/api/admin/ranking-versions`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch ranking versions')
  }

  return response.json()
}

export async function adminGetTeamVersions(token: string): Promise<{
  versions: TeamVersionResponse[]
}> {
  const response = await fetch(`${API_BASE}/api/admin/team-versions`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch team versions')
  }

  return response.json()
}

export async function adminGetTeamVersionDetail(
  token: string,
  versionId: string,
): Promise<any> {
  const response = await fetch(`${API_BASE}/api/admin/team-versions/${encodeURIComponent(versionId)}`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch team version detail')
  }

  return response.json()
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

  const response = await fetch(`${API_BASE}/api/me/submit-payment`, {
    method: 'POST',
    headers: {
      'X-User-Token': token,
    },
    body: form,
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to submit payment')
  }

  return response.json()
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
  const response = await fetch(`${API_BASE}/api/me/payment-status`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch payment status')
  }

  return response.json()
}

export async function getAllRankings(token: string): Promise<{
  rankings: any[]
  total: number
  current_user_id: string
  current_role: string
}> {
  const response = await fetch(`${API_BASE}/api/rankings`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch rankings')
  }

  return response.json()
}

export async function getAllTeams(token: string): Promise<{
  teams: any[]
  current_user_id: string
  current_role: string
  all_paid: boolean
  paid_count: number
  total_qualified: number
}> {
  const response = await fetch(`${API_BASE}/api/teams`, {
    headers: {
      'X-User-Token': token,
    },
  })

  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to fetch teams')
  }

  return response.json()
}
