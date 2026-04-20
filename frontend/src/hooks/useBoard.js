'use client';

import { useCallback, useEffect } from 'react';
import toast from 'react-hot-toast';
import { socket, emit } from '../lib/socket';
import { getBoardStats } from '../lib/api/boards';
import { getTasks, getComments } from '../lib/api/tasks';
import { useBoardStore } from '../store/boardStore';

function normalizePresenceUser(user) {
  if (!user) {
    return null;
  }

  if (typeof user === 'string') {
    return { id: user, name: user };
  }

  const id = user.id || user.userId || user.user_id || user.email;
  if (!id) {
    return null;
  }

  return {
    id,
    name: user.name || user.email || id,
  };
}

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
  } = useBoardStore();

  const loadTasks = useCallback(async () => {
    try {
      const data = await getTasks(boardId);
      console.log('=== LOAD TASKS ===');
      console.log('Tasks from API:', data.length);
      if (data.length > 0) {
        data.forEach((task, index) => {
          console.log(`  Task ${index + 1}: ${task.title} (Column: ${task.column_id})`);
        });
      }
      setTasks(data);
    } catch (error) {
      toast.error('Failed to load tasks');
      console.error('Load tasks error:', error);
    }
  }, [boardId, setTasks]);

  const loadComments = useCallback(async (taskId) => {
    try {
      const data = await getComments(taskId);
      setComments(taskId, data);
    } catch (error) {
      toast.error('Failed to load comments');
      console.error(error);
    }
  }, [setComments]);

  const loadStats = useCallback(async () => {
    try {
      return await getBoardStats(boardId);
    } catch (error) {
      toast.error('Failed to load stats');
      console.error(error);
      return null;
    }
  }, [boardId]);

  const joinBoard = useCallback(() => {
    emit('join:board', { boardId });
  }, [boardId]);

  const leaveBoard = useCallback(() => {
    emit('leave:board', { boardId });
  }, [boardId]);

  useEffect(() => {
    if (!boardId) return;

    const handleSocketConnect = () => {
      emit('join:board', { boardId });
    };

    const matchesBoard = (payload) => {
      if (!payload || typeof payload !== 'object') return false;
      const targetBoardId = payload.board_id ?? payload.boardId;
      if (!targetBoardId) return true;
      return String(targetBoardId) === String(boardId);
    };

    const handleTaskCreated = (payload) => {
      if (!matchesBoard(payload) || !payload?.id) return;
      addTask(payload);
      toast.success('New task created');
    };

    const handleTaskUpdated = (payload) => {
      if (!matchesBoard(payload) || !payload?.id) return;
      const { id, board_id: _b, user_id: _u, timestamp: _t, changes: _c, ...updates } = payload;
      updateTask(id, updates);
    };

    const handleTaskMoved = (payload) => {
      if (!matchesBoard(payload) || !payload?.id) return;
      const updates = {};
      if (payload.column_id !== undefined) updates.column_id = payload.column_id;
      if (payload.position !== undefined) updates.position = payload.position;
      updateTask(payload.id, updates);
    };

    const handleTaskDeleted = (payload) => {
      if (!matchesBoard(payload) || !payload?.id) return;
      removeTask(payload.id);
      toast.success('Task deleted');
    };

    const handleCommentAdded = (payload) => {
      if (!matchesBoard(payload) || !payload?.task_id || !payload?.id) return;
      addComment(payload.task_id, payload);
    };

    const handleUserJoined = (user) => {
      if (user?.boardId && user.boardId !== boardId) {
        return;
      }

      const normalizedUser = normalizePresenceUser(user);
      if (!normalizedUser) {
        return;
      }

      addOnlineUser(normalizedUser);
    };

    const handleUserLeft = (payload) => {
      const userId = typeof payload === 'string' ? payload : payload?.userId || payload?.id;
      if (!userId) {
        return;
      }

      removeOnlineUser(userId);
    };

    const handleOnlineUsers = (payload) => {
      const users = Array.isArray(payload) ? payload : payload?.users;
      setOnlineUsers((users || []).map(normalizePresenceUser).filter(Boolean));
    };

    socket.on('connect', handleSocketConnect);
    socket.on('task:created', handleTaskCreated);
    socket.on('task:updated', handleTaskUpdated);
    socket.on('task:moved', handleTaskMoved);
    socket.on('task:deleted', handleTaskDeleted);
    socket.on('comment:added', handleCommentAdded);
    socket.on('user:online', handleOnlineUsers);
    socket.on('user:joined', handleUserJoined);
    socket.on('user:left', handleUserLeft);
    socket.on('online:users', handleOnlineUsers);

    return () => {
      socket.off('connect', handleSocketConnect);
      socket.off('task:created', handleTaskCreated);
      socket.off('task:updated', handleTaskUpdated);
      socket.off('task:moved', handleTaskMoved);
      socket.off('task:deleted', handleTaskDeleted);
      socket.off('comment:added', handleCommentAdded);
      socket.off('user:online', handleOnlineUsers);
      socket.off('user:joined', handleUserJoined);
      socket.off('user:left', handleUserLeft);
      socket.off('online:users', handleOnlineUsers);
    };
  }, [boardId, addTask, updateTask, removeTask, addOnlineUser, removeOnlineUser, setOnlineUsers, addComment]);

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
