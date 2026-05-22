import axios, { type AxiosInstance } from 'axios';
import { useAuthStore } from '@shared/hooks';

type AppType = 'admin' | 'tenant';

interface ApiClientOptions {
  baseURL?: string;
}

export function createApiClient(appType: AppType, options: ApiClientOptions = {}): AxiosInstance {
  const rootBaseURL = options.baseURL ?? '';

  const client = axios.create({
    baseURL: rootBaseURL,
    timeout: 30_000,
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
    (error) => {
      if (error.response?.status === 401) {
        const slug = useAuthStore.getState().payload?.slug;
        useAuthStore.getState().logout();
        window.location.href = slug ? `/login?slug=${slug}` : '/login';
      }
      return Promise.reject(error);
    },
  );

  return client;
}
