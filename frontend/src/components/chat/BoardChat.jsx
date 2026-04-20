'use client';

import { useEffect, useRef, useState } from 'react';
import { format } from 'date-fns';
import { Send, Users } from 'lucide-react';
import { socket, emit } from '../../lib/socket';
import { useUserStore } from '../../store/userStore';
import { Avatar } from '../ui';

function normalizeUser(user) {
  if (!user) {
    return { id: 'unknown', name: 'Unknown user' };
  }

  if (typeof user === 'string') {
    return {
      id: user,
      name: user,
    };
  }

  const id = user.id || user.userId || user.user_id || user.email || 'unknown';
  const name = user.name || user.email || user.userId || user.user_id || id;

  return { id, name };
}

function normalizeMessage(message) {
  return {
    id: message.id || `${message.from || message.authorId || 'unknown'}:${message.ts || message.createdAt || Date.now()}`,
    boardId: message.boardId,
    text: message.text || '',
    authorId: message.authorId || message.from || null,
    authorName: message.author?.name || message.name || 'User',
    createdAt: message.createdAt || message.ts || new Date().toISOString(),
  };
}

export default function BoardChat({ boardId }) {
  const { user } = useUserStore();
  const [messages, setMessages] = useState([]);
  const [messageText, setMessageText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!boardId) return;

    const handleHistory = (payload) => {
      if (payload?.boardId && payload.boardId !== boardId) {
        return;
      }

      setMessages((payload?.messages || []).map(normalizeMessage));
    };

    const handleMessage = (message) => {
      if (message?.boardId && message.boardId !== boardId) {
        return;
      }

      setMessages((prev) => [...prev, normalizeMessage(message)]);
    };

    const handleOnlineUsers = (payload) => {
      const users = Array.isArray(payload) ? payload : payload?.users;
      setOnlineUsers((users || []).map(normalizeUser));
    };

    const handleUserJoined = (nextUser) => {
      if (nextUser?.boardId && nextUser.boardId !== boardId) {
        return;
      }

      const normalizedUser = normalizeUser(nextUser);
      setOnlineUsers((prev) => [
        ...prev.filter((existingUser) => existingUser.id !== normalizedUser.id),
        normalizedUser,
      ]);
    };

    const handleUserLeft = (payload) => {
      const userId = typeof payload === 'string' ? payload : payload?.userId || payload?.id;
      if (!userId) {
        return;
      }

      setOnlineUsers((prev) => prev.filter((currentUser) => currentUser.id !== userId));
    };

    socket.on('chat:history', handleHistory);
    socket.on('chat:message', handleMessage);
    socket.on('user:online', handleOnlineUsers);
    socket.on('online:users', handleOnlineUsers);
    socket.on('user:joined', handleUserJoined);
    socket.on('user:left', handleUserLeft);

    return () => {
      socket.off('chat:history', handleHistory);
      socket.off('chat:message', handleMessage);
      socket.off('user:online', handleOnlineUsers);
      socket.off('online:users', handleOnlineUsers);
      socket.off('user:joined', handleUserJoined);
      socket.off('user:left', handleUserLeft);
    };
  }, [boardId]);

  useEffect(() => {
    if (!boardId || !isOpen) return;

    emit('chat:sync', { boardId });
  }, [boardId, isOpen]);

  useEffect(() => {
    if (!boardId) return;

    const handleConnect = () => {
      if (isOpen) {
        emit('chat:sync', { boardId });
      }
    };

    socket.on('connect', handleConnect);

    return () => {
      socket.off('connect', handleConnect);
    };
  }, [boardId, isOpen]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const sendMessage = async (event) => {
    event.preventDefault();
    if (!messageText.trim()) return;

    setIsSubmitting(true);
    emit('chat:message', {
      boardId,
      text: messageText,
    });
    setMessageText('');
    setIsSubmitting(false);
  };

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-4 right-4 bg-primary-600 hover:bg-primary-700 text-white p-4 rounded-full shadow-lg transition-colors z-40"
      >
        <Send className="w-6 h-6" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-4 right-4 w-80 bg-white dark:bg-gray-800 rounded-lg shadow-xl border border-gray-200 dark:border-gray-700 z-40 flex flex-col max-h-96">
      <div className="flex justify-between items-center p-4 border-b dark:border-gray-700">
        <div className="flex items-center space-x-2">
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            Board Chat
          </h3>
          <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
            <Users className="w-3 h-3 mr-1" />
            {onlineUsers.length}
          </div>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            No messages yet. Start the conversation!
          </p>
        ) : (
          messages.map((message, index) => {
            const isOwnMessage = message.authorId === user?.id;
            const createdAt = new Date(message.createdAt);
            const timeLabel = Number.isNaN(createdAt.getTime())
              ? ''
              : format(createdAt, 'HH:mm');

            return (
              <div
                key={`${message.id}-${index}`}
                className={`flex space-x-2 ${isOwnMessage ? 'flex-row-reverse space-x-reverse' : ''}`}
              >
                <Avatar name={message.authorName} size="sm" />
                <div className={`flex-1 ${isOwnMessage ? 'text-right' : ''}`}>
                  <div
                    className={`inline-block px-3 py-2 rounded-lg ${
                      isOwnMessage
                        ? 'bg-primary-600 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                    }`}
                  >
                    <p className="text-sm">{message.text}</p>
                  </div>
                  {timeLabel && (
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                      {timeLabel}
                    </p>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      <form onSubmit={sendMessage} className="p-3 border-t dark:border-gray-700">
        <div className="flex space-x-2">
          <input
            type="text"
            value={messageText}
            onChange={(event) => setMessageText(event.target.value)}
            placeholder="Type a message..."
            className="flex-1 px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
          />
          <button
            type="submit"
            disabled={!messageText.trim() || isSubmitting}
            className="p-2 bg-primary-600 hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
      </form>
    </div>
  );
}
