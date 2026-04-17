import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import { jwtDecode } from 'jwt-decode';
import type { JWTPayload } from '@shared/types';

interface AuthState {
  token: string | null;
  payload: JWTPayload | null;
  setToken: (token: string) => void;
  logout: () => void;
  isExpired: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      token: null,
      payload: null,
      setToken: (token) => set({ token, payload: jwtDecode<JWTPayload>(token) }),
      logout: () => set({ token: null, payload: null }),
      isExpired: () => {
        const p = get().payload;
        return !p || p.exp * 1000 < Date.now();
      },
    }),
    {
      name: 'auth-storage',
      storage: createJSONStorage(() => sessionStorage),
    },
  ),
);
