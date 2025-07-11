import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatProvider(provider: string): string {
  const normalized = provider.toLowerCase()
  const providerMap: Record<string, string> = {
    'discogs': 'Discogs',
    'ebay': 'eBay'
  }
  return providerMap[normalized] || provider
}
