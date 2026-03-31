'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUserStore } from '../store/userStore';
import { getMe, logout as logoutApi } from '../lib/api/auth';
import toast from 'react-hot-toast';
import Cookies from 'js-cookie';

const API_URL = process.env.NEXT_PUBLIC_API_URL; // fix #4: добавлена константа

export function useAuth() {
  const router = useRouter();
  const { user, token, setUser, setToken, logout: logoutStore } = useUserStore();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      // Store сбрасывается при перезагрузке — восстанавливаем токен из cookie
      const activeToken = token || Cookies.get('token');
      if (!activeToken) {
        setIsLoading(false);
        return;
      }

      if (!token) {
        setToken(activeToken);
      }

      try {
        const userData = await getMe();
        setUser(userData);
      } catch (error) {
        console.error('Failed to load user:', error);
        logoutStore();
      } finally {
        setIsLoading(false);
      }
    }

    loadUser();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // fix #5: добавлен параметр refreshToken и сохранение в cookie
  const login = (userData, authToken, refreshToken) => {
    setUser(userData);
    setToken(authToken);
    Cookies.set('refreshToken', refreshToken, { expires: 30 });
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      logoutStore();
      Cookies.remove('token');        // fix #6: удаление cookies при logout
      Cookies.remove('refreshToken'); // fix #6
      router.push('/auth/login');
      toast.success('Logged out successfully');
    }
  };

  // fix #7: переименована переменная refreshTokenValue во избежание конфликта с именем метода
  const refreshToken = async () => {
    try {
      const refreshTokenValue = Cookies.get('refreshToken');
      if (!refreshTokenValue) throw new Error('No refresh token');

      const response = await fetch(`${API_URL}/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken: refreshTokenValue }),
      });

      const data = await response.json();
      login(data.user, data.accessToken, data.refreshToken);
    } catch (error) {
      logout();
    }
  };

  const isAuthenticated = !!token && !!user;

  return { user, token, isLoading, login, logout, isAuthenticated, refreshToken }; // fix #10: экспортирован refreshToken
}
