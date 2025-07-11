import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatProvider(provider: string): string {
  const providerMap: Record<string, string> = {
    'DISCOGS': 'Discogs',
    'EBAY': 'eBay',
    'discogs': 'Discogs',
    'ebay': 'eBay',
    'BOTH': 'Both',
    'both': 'Both'
  }
  return providerMap[provider] || provider
}
