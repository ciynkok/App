'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUserStore } from '../store/userStore';
import { getMe, logout as logoutApi } from '../lib/api/auth';
import toast from 'react-hot-toast';

export function useAuth() {
  const router = useRouter();
  const { user, token, setUser, setToken, logout: logoutStore } = useUserStore();
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function loadUser() {
      if (!token) {
        setIsLoading(false);
        return;
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
  }, [token, setUser, logoutStore]);

  const login = (userData, authToken) => {
    setUser(userData);
    setToken(authToken);
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      logoutStore();
      router.push('/auth/login');
      toast.success('Logged out successfully');
    }
  };

  const isAuthenticated = !!token && !!user;

  return { user, token, isLoading, login, logout, isAuthenticated };
}
