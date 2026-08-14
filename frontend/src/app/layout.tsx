import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'ML Fair Team Formation',
  description: 'Sistem pembentukan tim kompetitif Mobile Legends yang adil',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="id" className="antialiased">
      <body className={inter.className}>{children}</body>
    </html>
  )
}
