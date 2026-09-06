import { describe, expect, it } from 'vitest';
import { cn, pct, fixed, MODULE_PATH } from '@/lib/format';

describe('format helpers', () => {
  it('cn merges tailwind classes', () => {
    expect(cn('p-2', 'p-4')).toBe('p-4');
  });
  it('pct and fixed print stable numbers', () => {
    expect(pct(0.756)).toBe('76%');
    expect(fixed(1.2345, 2)).toBe('1.23');
  });
  it('module paths are URL safe', () => {
    for (const p of Object.values(MODULE_PATH)) expect(p).toMatch(/^[a-z-]+$/);
  });
});
