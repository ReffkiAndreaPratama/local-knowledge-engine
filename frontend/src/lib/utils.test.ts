import { describe, expect, it } from 'vitest'
import { formatBytes, formatDuration, splitHighlighted } from '@/lib/utils'

describe('splitHighlighted', () => {
  it('splits text into matching and non-matching parts', () => {
    const parts = splitHighlighted('The deployment port is 8080.', ['deployment', '8080'])
    expect(parts.filter((part) => part.match).map((part) => part.text)).toEqual([
      'deployment',
      '8080',
    ])
    expect(parts.map((part) => part.text).join('')).toBe('The deployment port is 8080.')
  })

  it('is case-insensitive', () => {
    const parts = splitHighlighted('Postgres and postgresql', ['Postgres'])
    expect(parts.filter((part) => part.match)).toHaveLength(2)
    // "postgresql" contains the term, so it is highlighted too
    expect(parts.filter((part) => part.match).map((part) => part.text)).toEqual([
      'Postgres',
      'postgres',
    ])
  })

  it('returns the whole text when there is nothing to highlight', () => {
    expect(splitHighlighted('plain text', [])).toEqual([{ text: 'plain text', match: false }])
  })

  it('escapes regular-expression characters in search terms', () => {
    const parts = splitHighlighted('cost is $5 (approx)', ['$5 (approx)'])
    expect(parts.some((part) => part.match)).toBe(true)
  })
})

describe('formatBytes', () => {
  it('formats byte sizes', () => {
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(512)).toBe('512 B')
    expect(formatBytes(2048)).toBe('2.0 KB')
    expect(formatBytes(null)).toBe('—')
  })
})

describe('formatDuration', () => {
  it('uses milliseconds below one second', () => {
    expect(formatDuration(12.4)).toBe('12 ms')
  })

  it('uses seconds above one second', () => {
    expect(formatDuration(2500)).toBe('2.50 s')
  })
})
