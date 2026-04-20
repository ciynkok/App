import { io } from 'socket.io-client';

// Пустая строка → socket.io-client использует текущий origin (same-origin),
// что нужно для доступа по локальной сети через nginx.
const WS_URL = process.env.NEXT_PUBLIC_WS_URL || undefined;

// Очередь сообщений на случай отправки до подключения
const pendingMessages = [];

export const socket = io(WS_URL, {
  autoConnect: false,
  transports: ['websocket'],
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  path: '/socket.io/',  // Socket.io path
});

// При подключении — отправить всё что накопилось в очереди
socket.on('connect', () => {
  while (pendingMessages.length > 0) {
    const [event, data] = pendingMessages.shift();
    socket.emit(event, data);
  }
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

/**
 * Отправить событие через WebSocket.
 * Если сокет ещё не подключён — сообщение ставится в очередь.
 */
export function emit(event, data) {
  if (socket.connected) {
    socket.emit(event, data);
  } else {
    console.warn(`[socket] Not connected, queuing: ${event}`);
    pendingMessages.push([event, data]);
  }
}
