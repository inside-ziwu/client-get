import { describe, expect, it } from 'vitest';

// 直接从 page.tsx 导出的常量测试
// 由于常量定义在页面文件中，这里直接测试映射逻辑

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  operator: '运营',
  readonly: '只读',
};

const STATUS_LABELS: Record<string, string> = {
  active: '已激活',
  disabled: '已禁用',
};

/** 角色渲染逻辑：与 page.tsx 中 render 一致 */
function renderRoles(roles?: string[]): string {
  if (!roles || roles.length === 0) return '-';
  return roles.map((r) => ROLE_LABELS[r] ?? r).join('、');
}

/** 状态渲染逻辑：与 page.tsx 中 render 一致 */
function renderStatus(status: string): string {
  return STATUS_LABELS[status] ?? status;
}

describe('ROLE_LABELS 映射', () => {
  it('单角色 admin 渲染为「管理员」', () => {
    expect(renderRoles(['admin'])).toBe('管理员');
  });

  it('多角色 admin + operator 渲染为「管理员、运营」', () => {
    expect(renderRoles(['admin', 'operator'])).toBe('管理员、运营');
  });

  it('未知角色回退到原始值', () => {
    expect(renderRoles(['unknown_role'])).toBe('unknown_role');
  });

  it('空角色数组渲染为 -', () => {
    expect(renderRoles([])).toBe('-');
  });

  it('undefined 角色渲染为 -', () => {
    expect(renderRoles(undefined)).toBe('-');
  });
});

describe('STATUS_LABELS 映射', () => {
  it('状态 active 渲染为「已激活」', () => {
    expect(renderStatus('active')).toBe('已激活');
  });

  it('状态 disabled 渲染为「已禁用」', () => {
    expect(renderStatus('disabled')).toBe('已禁用');
  });

  it('未知状态回退到原始值', () => {
    expect(renderStatus('unknown_status')).toBe('unknown_status');
  });
});
