import 'server-only';

type ServerApiOptions = {
  token: string;
  params?: Record<string, string | number | boolean | null | undefined>;
};

function baseUrl() {
  return (process.env.BACKEND_INTERNAL_URL || 'http://localhost:8000').replace(/\/$/, '');
}

function buildUrl(path: string, params?: ServerApiOptions['params']) {
  const url = new URL(`${baseUrl()}/admin${path}`);

  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== '') {
      url.searchParams.set(key, String(value));
    }
  }

  return url;
}

async function request<T>(path: string, options: ServerApiOptions): Promise<T> {
  const url = buildUrl(path, options.params);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 3_000);
  const start = Date.now();

  try {
    const response = await fetch(url, {
      headers: {
        Accept: 'application/json',
        Authorization: `Bearer ${options.token}`,
      },
      cache: 'no-store',
      signal: controller.signal,
    });

    const elapsed = Date.now() - start;

    if (!response.ok) {
      console.error(`[SSR] ✗ ${response.status} ${url} (${elapsed}ms)`);
      throw new Error(`Server API request failed: ${response.status}`);
    }

    console.log(`[SSR] ✓ ${url} (${elapsed}ms)`);
    return (await response.json()) as T;
  } catch (err) {
    const elapsed = Date.now() - start;
    console.error(`[SSR] ✗ ${url} (${elapsed}ms)`, err instanceof Error ? err.message : err);
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export const serverApi = {
  get: request,
};
