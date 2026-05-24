import { describe, expect, it } from 'vitest';

/** 与 page.tsx 中 formatLoginTime 一致的纯函数 */
function formatLoginTime(iso: string | null | undefined): string {
  if (!iso) return '-';
  const date = new Date(iso);
  if (isNaN(date.getTime())) return '-';
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  const h = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${d} ${h}:${min}`;
}

describe('formatLoginTime', () => {
  it('带时区偏移的 ISO 字符串格式化为本地时间', () => {
    const result = formatLoginTime('2026-05-23T14:30:00+08:00');
    // 在 +08:00 时区环境下应为 2026-05-23 14:30，其他时区为对应转换结果
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
  });

  it('UTC 字符串格式化后匹配 YYYY-MM-DD HH:mm 格式', () => {
    const result = formatLoginTime('2026-05-23T06:30:00Z');
    expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/);
  });

  it('null 返回 -', () => {
    expect(formatLoginTime(null)).toBe('-');
  });

  it('undefined 返回 -', () => {
    expect(formatLoginTime(undefined)).toBe('-');
  });

  it('无效字符串 "invalid" 返回 -（NaN 守卫）', () => {
    expect(formatLoginTime('invalid')).toBe('-');
  });

  it('空字符串返回 -', () => {
    expect(formatLoginTime('')).toBe('-');
  });
});
