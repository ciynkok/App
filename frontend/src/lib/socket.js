import { io } from 'socket.io-client';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL;

export const socket = io(WS_URL, {
  autoConnect: false,
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  path: '/socket.io/',  // Socket.io path
});

export function connectSocket(token) {
  if (token) {
    // Переподключаемся с токеном в query params
    socket.io.opts.query = { token };
    socket.connect();
  }
}

export function disconnectSocket() {
  socket.disconnect();
}
