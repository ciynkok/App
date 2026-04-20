import { create } from 'zustand';
import Cookies from 'js-cookie'; // fix #2: default import, не именованный

// export const useUserStore = create(
//   persist(
//     (set) => ({
//       user: null,
//       token: null,
//       setUser: (user) => set({ user }),
//       setToken: (token) => set({ token }),
//       logout: () => set({ user: null, token: null }),
//     }),
//     { name: 'user-storage' }
//   )
// );

export const useUserStore = create((set) => ({
  user: null,
  token: null,
  setUser: (user) => set({ user }),
  setToken: (token) => {
    const isHttps = typeof window !== 'undefined' && window.location.protocol === 'https:';
    Cookies.set('token', token, {
      secure: isHttps,
      sameSite: 'lax',
      expires: 7, // 7 дней — кука не session-only, переживает перезагрузку
    });
    set({ token });
  },
  logout: () => {
    Cookies.remove('token');
    set({ user: null, token: null });
  },
}));
