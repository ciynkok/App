'use client';

import { useEffect, useCallback, useState } from 'react';
import { useUserStore } from '../store/userStore';
import { connectSocket, disconnectSocket, socket, emit } from '../lib/socket';
import toast from 'react-hot-toast';

export function useSocket() {
  const { token } = useUserStore();
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const handleConnect = () => {
      setIsConnected(true);
      console.log('Socket connected');
    };

    const handleDisconnect = () => {
      setIsConnected(false);
      console.log('Socket disconnected');
      toast.error('Connection lost. Reconnecting...');
    };

    const handleConnectError = (error) => {
      console.error('Socket connection error:', error);
      toast.error('Failed to connect to server');
    };

    socket.on('connect', handleConnect);
    socket.on('disconnect', handleDisconnect);
    socket.on('connect_error', handleConnectError);

    return () => {
      socket.off('connect', handleConnect);
      socket.off('disconnect', handleDisconnect);
      socket.off('connect_error', handleConnectError);
    };
  }, []);

  // Connect/disconnect based on auth state
  useEffect(() => {
    if (token) {
      connectSocket(token);
    } else {
      disconnectSocket();
    }
  }, [token]);

  const sendMessage = useCallback((event, data) => {
    emit(event, data);
  }, []);

  return { isConnected, sendMessage };
}
