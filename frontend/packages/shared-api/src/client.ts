import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';
import { useAuthStore } from '@shared/hooks';

type AppType = 'admin' | 'tenant';

interface ApiClientOptions {
  baseURL?: string;
}

let isRefreshing = false;
let failedQueue: { resolve: (token: string) => void; reject: (err: unknown) => void }[] = [];

const REFRESH_TIMEOUT_MS = 10_000;

function processQueue(error: unknown, token: string | null) {
  for (const { resolve, reject } of failedQueue) {
    if (token) {
      resolve(token);
    } else {
      reject(error);
    }
  }
  failedQueue = [];
}

export function createApiClient(appType: AppType, options: ApiClientOptions = {}): AxiosInstance {
  const rootBaseURL = options.baseURL ?? '';

  const client = axios.create({
    baseURL: rootBaseURL,
    timeout: 30_000,
    withCredentials: true,
    headers: { 'Content-Type': 'application/json' },
  });

  client.interceptors.request.use((config) => {
    const { token, payload } = useAuthStore.getState();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (appType === 'tenant' && payload?.slug) {
      config.baseURL = `${rootBaseURL}/t/${payload.slug}`;
    } else if (appType === 'admin') {
      config.baseURL = `${rootBaseURL}/admin`;
    }
    return config;
  });

  client.interceptors.response.use(
    (res) => res,
    async (error) => {
      const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

      if (error.response?.status !== 401 || originalRequest._retry) {
        return Promise.reject(error);
      }

      const requestUrl = originalRequest.url ?? '';
      if (requestUrl.includes('/auth/refresh')) {
        const slug = useAuthStore.getState().payload?.slug;
        useAuthStore.getState().logout();
        window.location.href = slug ? `/login?slug=${slug}` : '/login';
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject });
          setTimeout(() => reject(new Error('refresh timeout')), REFRESH_TIMEOUT_MS);
        }).then((newToken) => {
          originalRequest._retry = true;
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return client(originalRequest);
        });
      }

      isRefreshing = true;
      originalRequest._retry = true;

      try {
        const refreshResp = await axios.post(
          `${rootBaseURL}/admin/api/v1/auth/refresh`,
          {},
          { withCredentials: true },
        );
        const newToken: string = refreshResp.data.data.access_token;

        useAuthStore.getState().setToken(newToken);
        await fetch('/api/auth/set-token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: newToken }),
        });

        processQueue(null, newToken);

        originalRequest.headers.Authorization = `Bearer ${newToken}`;
        return client(originalRequest);
      } catch (refreshError: unknown) {
        processQueue(refreshError, null);

        const isNetworkError =
          refreshError instanceof Error &&
          'response' in refreshError === false &&
          !axios.isAxiosError(refreshError);
        const isAxiosNetworkError =
          axios.isAxiosError(refreshError) && !refreshError.response;

        if (isNetworkError || isAxiosNetworkError) {
          return Promise.reject(error);
        }

        const slug = useAuthStore.getState().payload?.slug;
        useAuthStore.getState().logout();
        window.location.href = slug ? `/login?slug=${slug}` : '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    },
  );

  return client;
}
