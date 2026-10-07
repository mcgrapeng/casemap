import { describe, expect, it } from 'vitest';
import { cn, formatDate, formatPercent, truncate } from '@/lib/utils';

describe('cn', () => {
  it('merges classes', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4');
    expect(cn('text-red-500', false && 'hidden', 'font-bold')).toBe('text-red-500 font-bold');
  });
});

describe('formatPercent', () => {
  it('renders decimal percent', () => {
    expect(formatPercent(0.123)).toBe('12.3%');
    expect(formatPercent(1)).toBe('100.0%');
  });
});

describe('formatDate', () => {
  it('handles invalid', () => {
    expect(formatDate(null)).toBe('—');
    expect(formatDate('not a date')).toBe('—');
  });
  it('formats ISO strings', () => {
    const s = formatDate('2024-01-02T00:00:00.000Z');
    expect(typeof s).toBe('string');
    expect(s.length).toBeGreaterThan(0);
  });
});

describe('truncate', () => {
  it('shortens long strings', () => {
    expect(truncate('abcdefghij', 5)).toBe('abcd…');
    expect(truncate('abc', 5)).toBe('abc');
  });
});
