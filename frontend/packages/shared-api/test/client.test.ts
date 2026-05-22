import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const mockLogout = vi.fn();
let mockPayload: { slug?: string } | null = null;

vi.mock('@shared/hooks', () => ({
  useAuthStore: {
    getState: () => ({
      token: 'fake-token',
      payload: mockPayload,
      logout: mockLogout,
    }),
  },
}));

import { createApiClient } from '../src/client';

describe('401 拦截器', () => {
  let hrefSpy: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mockLogout.mockClear();
    hrefSpy = vi.fn();
    Object.defineProperty(window, 'location', {
      value: { href: 'http://localhost:3000/', set href(v: string) { hrefSpy(v); } },
      writable: true,
      configurable: true,
    });
    // make the getter work via spy
    Object.defineProperty(window.location, 'href', {
      get: () => hrefSpy.mock.calls.at(-1)?.[0] ?? 'http://localhost:3000/',
      set: (v: string) => hrefSpy(v),
      configurable: true,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, 'location', {
      value: new URL('http://localhost:3000/'),
      writable: true,
      configurable: true,
    });
  });

  it('401 响应 + payload 有 slug → 跳转 /login?slug=acme，调用 logout', async () => {
    mockPayload = { slug: 'acme' };
    const client = createApiClient('tenant');

    try {
      await client.get('http://localhost/test-401', {
        adapter: () => Promise.reject({ response: { status: 401 }, config: {}, isAxiosError: true }),
      });
    } catch {
      // expected
    }

    expect(mockLogout).toHaveBeenCalled();
    expect(hrefSpy).toHaveBeenCalledWith('/login?slug=acme');
  });

  it('401 响应 + payload 无 slug → 跳转 /login，调用 logout', async () => {
    mockPayload = null;
    const client = createApiClient('tenant');

    try {
      await client.get('http://localhost/test-401', {
        adapter: () => Promise.reject({ response: { status: 401 }, config: {}, isAxiosError: true }),
      });
    } catch {
      // expected
    }

    expect(mockLogout).toHaveBeenCalled();
    expect(hrefSpy).toHaveBeenCalledWith('/login');
  });

  it('非 401 响应 → 不触发重定向，不调用 logout', async () => {
    mockPayload = { slug: 'acme' };
    const client = createApiClient('tenant');

    try {
      await client.get('http://localhost/test-500', {
        adapter: () => Promise.reject({ response: { status: 500 }, config: {}, isAxiosError: true }),
      });
    } catch {
      // expected
    }

    expect(mockLogout).not.toHaveBeenCalled();
    expect(hrefSpy).not.toHaveBeenCalled();
  });
});
