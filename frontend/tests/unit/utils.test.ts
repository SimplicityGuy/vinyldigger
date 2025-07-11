import { describe, it, expect } from 'vitest'
import { cn, formatProvider } from '@/lib/utils'

describe('cn utility', () => {
  it('should merge class names correctly', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
    expect(cn('foo', { bar: true })).toBe('foo bar')
    expect(cn('foo', { bar: false })).toBe('foo')
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4')
  })
})

describe('formatProvider utility', () => {
  it('should format provider names correctly', () => {
    expect(formatProvider('DISCOGS')).toBe('Discogs')
    expect(formatProvider('discogs')).toBe('Discogs')
    expect(formatProvider('EBAY')).toBe('eBay')
    expect(formatProvider('ebay')).toBe('eBay')
    expect(formatProvider('BOTH')).toBe('Both')
    expect(formatProvider('both')).toBe('Both')
  })

  it('should return original value for unknown providers', () => {
    expect(formatProvider('unknown')).toBe('unknown')
    expect(formatProvider('UNKNOWN')).toBe('UNKNOWN')
  })
})
