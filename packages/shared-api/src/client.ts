import axios, { type AxiosInstance } from 'axios';
import { useAuthStore } from '@shared/hooks';

type AppType = 'admin' | 'tenant';

export function createApiClient(appType: AppType): AxiosInstance {
  const client = axios.create({
    baseURL: import.meta.env.VITE_API_BASE_URL,
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
  });

  client.interceptors.request.use((config) => {
    const { token, payload } = useAuthStore.getState();
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    if (appType === 'tenant' && payload?.slug) {
      config.baseURL = `${import.meta.env.VITE_API_BASE_URL}/t/${payload.slug}`;
    } else if (appType === 'admin') {
      config.baseURL = `${import.meta.env.VITE_API_BASE_URL}/admin`;
    }
    return config;
  });

  client.interceptors.response.use(
    (res) => res,
    (error) => {
      if (error.response?.status === 401) {
        useAuthStore.getState().logout();
        window.location.href = '/login';
      }
      return Promise.reject(error);
    },
  );

  return client;
}
