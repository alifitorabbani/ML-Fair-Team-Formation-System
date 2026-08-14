'use client'

export default function LoadingSpinner({ text = 'Memuat...' }: { text?: string }) {
  return (
    <div className="flex items-center justify-center py-16">
      <div className="relative">
        <div className="h-12 w-12 rounded-full border-4 border-brand-500/20 border-t-brand-500 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-2 w-2 rounded-full bg-brand-500 animate-pulse" />
        </div>
      </div>
      <p className="ml-4 text-sm text-gray-400">{text}</p>
    </div>
  )
}
