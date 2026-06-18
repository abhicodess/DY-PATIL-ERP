import { create } from 'zustand';

export const useAuthStore = create((set) => ({
  accessToken: null,
  user: null,
  csrfToken: null,
  setAccessToken: (token) => set({ accessToken: token }),
  setUser: (user) => set({ user }),
  setCsrfToken: (token) => set({ csrfToken: token }),
  clearAuth: () => set({ accessToken: null, user: null }),
}));
