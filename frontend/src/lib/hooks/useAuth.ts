'use client'

import { useState, useEffect } from 'react'

interface UserSession {
  token: string
  player_id: string
  email: string
  username?: string
  full_name?: string
  name?: string
  role: 'admin' | 'user'
}

export function useAuthToken(): string | null {
  const [token, setToken] = useState<string | null>(null)

  useEffect(() => {
    try {
      const stored = localStorage.getItem('user_session')
      if (stored) {
        const parsed = JSON.parse(stored) as UserSession
        setToken(parsed.token)
      }
    } catch {
      // ignore
    }
  }, [])

  return token
}

export function useUserSession(): UserSession | null {
  const [session, setSession] = useState<UserSession | null>(null)

  useEffect(() => {
    try {
      const stored = localStorage.getItem('user_session')
      if (stored) {
        setSession(JSON.parse(stored) as UserSession)
      }
    } catch {
      // ignore
    }
  }, [])

  return session
}
