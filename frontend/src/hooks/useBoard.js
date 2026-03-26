'use client';

import { useEffect, useCallback } from 'react';
import { socket } from '../lib/socket';
import { useBoardStore } from '../store/boardStore';
import { getTasks, getComments } from '../lib/api/tasks';
import { getBoardStats } from '../lib/api/boards';
import toast from 'react-hot-toast';

export function useBoard(boardId) {
  const {
    tasks,
    setTasks,
    addTask,
    updateTask,
    removeTask,
    onlineUsers,
    setOnlineUsers,
    addOnlineUser,
    removeOnlineUser,
    setComments,
    addComment,
    removeComment,
  } = useBoardStore();

  // Load tasks for the board
  const loadTasks = useCallback(async () => {
    try {
      const data = await getTasks(boardId);
      setTasks(data);
    } catch (error) {
      toast.error('Failed to load tasks');
      console.error(error);
    }
  }, [boardId, setTasks]);

  // Load comments for a task
  const loadComments = useCallback(async (taskId) => {
    try {
      const data = await getComments(taskId);
      setComments(taskId, data);
    } catch (error) {
      toast.error('Failed to load comments');
      console.error(error);
    }
  }, [setComments]);

  // Load board stats
  const loadStats = useCallback(async () => {
    try {
      return await getBoardStats(boardId);
    } catch (error) {
      toast.error('Failed to load stats');
      console.error(error);
      return null;
    }
  }, [boardId]);

  // Join board room
  const joinBoard = useCallback(() => {
    socket.emit('join:board', { boardId });
  }, [boardId]);

  // Leave board room
  const leaveBoard = useCallback(() => {
    socket.emit('leave:board', { boardId });
  }, [boardId]);

  // Subscribe to board events
  useEffect(() => {
    if (!boardId) return;

    // Task events
    const handleTaskCreated = (task) => {
      addTask(task);
      toast.success('New task created');
    };

    const handleTaskUpdated = (taskId, updates) => {
      updateTask(taskId, updates);
    };

    const handleTaskMoved = (taskId, columnId, position) => {
      updateTask(taskId, { columnId, position });
    };

    const handleTaskDeleted = (taskId) => {
      removeTask(taskId);
      toast.success('Task deleted');
    };

    // Comment events
    const handleCommentAdded = (taskId, comment) => {
      addComment(taskId, comment);
    };

    // Online users events
    const handleUserJoined = (user) => {
      addOnlineUser(user);
      toast.success(`${user.name} joined`);
    };

    const handleUserLeft = (userId) => {
      removeOnlineUser(userId);
    };

    const handleOnlineUsers = (users) => {
      setOnlineUsers(users);
    };

    // Socket event listeners
    socket.on('task:created', handleTaskCreated);
    socket.on('task:updated', handleTaskUpdated);
    socket.on('task:moved', handleTaskMoved);
    socket.on('task:deleted', handleTaskDeleted);
    socket.on('comment:added', handleCommentAdded);
    socket.on('user:joined', handleUserJoined);
    socket.on('user:left', handleUserLeft);
    socket.on('online:users', handleOnlineUsers);

    return () => {
      socket.off('task:created', handleTaskCreated);
      socket.off('task:updated', handleTaskUpdated);
      socket.off('task:moved', handleTaskMoved);
      socket.off('task:deleted', handleTaskDeleted);
      socket.off('comment:added', handleCommentAdded);
      socket.off('user:joined', handleUserJoined);
      socket.off('user:left', handleUserLeft);
      socket.off('online:users', handleOnlineUsers);
    };
  }, [boardId, addTask, updateTask, removeTask, addOnlineUser, removeOnlineUser, setOnlineUsers, addComment, removeComment]);

  return {
    tasks,
    onlineUsers,
    loadTasks,
    loadComments,
    loadStats,
    joinBoard,
    leaveBoard,
  };
}
