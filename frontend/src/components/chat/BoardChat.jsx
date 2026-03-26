'use client';

import { useState, useEffect, useRef } from 'react';
import { socket } from '../../lib/socket';
import { useUserStore } from '../../store/userStore';
import { Avatar } from '../ui';
import { Send, Users } from 'lucide-react';
import { format } from 'date-fns';

export default function BoardChat({ boardId }) {
  const { user } = useUserStore();
  const [messages, setMessages] = useState([]);
  const [messageText, setMessageText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [onlineUsers, setOnlineUsers] = useState([]);
  const [isOpen, setIsOpen] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    if (!boardId || !isOpen) return;

    // Join board room for chat
    socket.emit('join:board', { boardId });

    const handleMessage = (message) => {
      setMessages((prev) => [...prev, message]);
    };

    const handleOnlineUsers = (users) => {
      setOnlineUsers(users);
    };

    const handleUserJoined = (user) => {
      setOnlineUsers((prev) => [...prev, user]);
    };

    const handleUserLeft = (userId) => {
      setOnlineUsers((prev) => prev.filter(u => u.id !== userId));
    };

    socket.on('chat:message', handleMessage);
    socket.on('online:users', handleOnlineUsers);
    socket.on('user:joined', handleUserJoined);
    socket.on('user:left', handleUserLeft);

    return () => {
      socket.off('chat:message', handleMessage);
      socket.off('online:users', handleOnlineUsers);
      socket.off('user:joined', handleUserJoined);
      socket.off('user:left', handleUserLeft);
      socket.emit('leave:board', { boardId });
    };
  }, [boardId, isOpen]);

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!messageText.trim() || !socket.connected) return;

    setIsSubmitting(true);
    socket.emit('chat:message', {
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
      {/* Header */}
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

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
            No messages yet. Start the conversation!
          </p>
        ) : (
          messages.map((message, index) => (
            <div
              key={index}
              className={`flex space-x-2 ${
                message.authorId === user?.id ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              <Avatar name={message.author?.name || 'User'} size="sm" />
              <div className={`flex-1 ${
                message.authorId === user?.id ? 'text-right' : ''
              }`}>
                <div
                  className={`inline-block px-3 py-2 rounded-lg ${
                    message.authorId === user?.id
                      ? 'bg-primary-600 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
                  }`}
                >
                  <p className="text-sm">{message.text}</p>
                </div>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {format(new Date(message.createdAt), 'HH:mm')}
                </p>
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <form onSubmit={sendMessage} className="p-3 border-t dark:border-gray-700">
        <div className="flex space-x-2">
          <input
            type="text"
            value={messageText}
            onChange={(e) => setMessageText(e.target.value)}
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
