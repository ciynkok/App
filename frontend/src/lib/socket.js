import { io } from 'socket.io-client';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL;

export const socket = io(WS_URL, {
  autoConnect: false,
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
});

export function connectSocket(token) {
  if (token) {
    socket.auth = { token };
    socket.connect();
  }
}

export function disconnectSocket() {
  socket.disconnect();
}
