'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { DndContext, DragEndEvent, DragStartEvent, DragOverlay, closestCorners } from '@dnd-kit/core';
import { useAuth } from '../../../hooks/useAuth';
import { useBoard } from '../../../hooks/useBoard';
import { useSocket } from '../../../hooks/useSocket';
import { getBoard, deleteColumn } from '../../../lib/api/boards';
import { moveTask } from '../../../lib/api/tasks';
import { useUserStore } from '../../../store/userStore';
import { useBoardStore } from '../../../store/boardStore';
import BoardColumn from '../../../components/board/BoardColumn';
import AddTaskForm from '../../../components/board/AddTaskForm';
import TaskDetailModal from '../../../components/modals/TaskDetailModal';
import BoardChat from '../../../components/chat/BoardChat';
import BurnDownChart from '../../../components/charts/BurnDownChart';
import { Button, Avatar, Card, Modal } from '../../../components/ui';
import { ArrowLeft, Share2, Users, Moon, Sun, BarChart3, Layout, Plus } from 'lucide-react';
import toast from 'react-hot-toast';

export default function DashboardPage() {
  const router = useRouter();
  const params = useParams();
  const boardId = params.boardId;
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL;

  const { isAuthenticated, user } = useAuth();
  const { isConnected } = useSocket();
  const { tasks, onlineUsers, loadTasks, loadStats, joinBoard, leaveBoard } = useBoard(boardId);
  const { board, columns, setBoard, setColumns, setTasks } = useBoardStore();
  const { token } = useUserStore();

  const [isLoading, setIsLoading] = useState(true);
  const [activeTask, setActiveTask] = useState(null);
  const [isAddTaskModalOpen, setIsAddTaskModalOpen] = useState(false);
  const [selectedColumnId, setSelectedColumnId] = useState(null);
  const [isStatsOpen, setIsStatsOpen] = useState(false);
  const [statsData, setStatsData] = useState(null);
  const [darkMode, setDarkMode] = useState(false);

  // Dark mode
  useEffect(() => {
    const isDark = localStorage.getItem('darkMode') === 'true';
    setDarkMode(isDark);
    if (isDark) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  // Debug logs
  useEffect(() => {
    console.log('=== PAGE RENDER ===');
    console.log('Columns:', columns.length);
    console.log('Tasks:', tasks.length);
    console.log('Is Loading:', isLoading);
    console.log('Is Auth:', isAuthenticated);
  }, [columns, tasks, isLoading, isAuthenticated]);

  useEffect(() => {
    if (isAuthenticated === false) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (boardId && isAuthenticated && token) {
      loadBoard();
      loadTasks();
      joinBoard();
    }

    return () => {
      if (boardId) {
        leaveBoard();
      }
    };
  }, [boardId, isAuthenticated, token]);

  const loadBoard = async () => {
    setIsLoading(true);
    try {
      const data = await getBoard(boardId);
      console.log('=== LOAD BOARD ===');
      console.log('Board:', data);
      console.log('Columns from /boards/{id}:', data.columns?.length || 0);
      
      // Загрузить колонки отдельным запросом (если не вернулись с доской)
      let columns = data.columns || [];
      if (columns.length === 0) {
        console.log('No columns in board response, fetching separately...');
        const columnsResponse = await fetch(`${API_URL}/api/boards/${boardId}/columns`, {
          headers: {
            'Authorization': `Bearer ${useUserStore.getState().token ? `Bearer ${useUserStore.getState().token}` : ''}`,
            'Content-Type': 'application/json'
          }
        });
        if (columnsResponse.ok) {
          columns = await columnsResponse.json();
          console.log('Columns from separate request:', columns.length);
        }
      }
      
      if (columns.length > 0) {
        columns.forEach((c, i) => {
          console.log(`  Column ${i+1}: ${c.title} (ID: ${c.id})`);
        });
      }
      
      setBoard(data);
      setColumns(columns);
    } catch (error) {
      toast.error('Failed to load board');
      console.error('Load board error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDragStart = (event) => {
    const { active } = event;
    const task = tasks.find(t => t.id === active.id);
    setActiveTask(task);
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) return;

    const taskId = active.id;
    const newColumnId = over.id;

    // Find the task
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;

    // If dropped on a different column
    if (task.column_id !== newColumnId) {
      // Calculate new position
      const columnTasks = tasks.filter(t => t.column_id === newColumnId);
      const newPosition = columnTasks.length;

      try {
        // Optimistic update
        useBoardStore.getState().updateTask(taskId, { column_id: newColumnId, position: newPosition });

        // API call
        await moveTask(taskId, newColumnId, newPosition);
        toast.success('Task moved');
      } catch (error) {
        // Rollback on error
        useBoardStore.getState().updateTask(taskId, { column_id: task.column_id, position: task.position });
        toast.error('Failed to move task');
        console.error(error);
      }
    }
  };

  const handleTaskClick = (task) => {
    // Открыть модальное окно задачи
    setActiveTask(task);
  };

  const handleAddTask = (columnId) => {
    setSelectedColumnId(columnId);
    setIsAddTaskModalOpen(true);
  };

  const handleDeleteColumn = async (columnId, columnName) => {
    if (!confirm(`Delete column "${columnName}"? All tasks in this column will be deleted.`)) {
      return;
    }
    
    try {
      await deleteColumn(boardId, columnId);
      
      // Обновить состояние
      setColumns(columns.filter(c => c.id !== columnId));
      toast.success('Column deleted');
    } catch (error) {
      toast.error('Failed to delete column');
      console.error(error);
    }
  };

  const handleTaskCreated = (newTask) => {
    // Обновить задачи после создания
    loadTasks();
  };

  const handleShowStats = async () => {
    const data = await loadStats();
    setStatsData(data);
    setIsStatsOpen(true);
  };

  const handleAddColumn = async () => {
    // Функция для чтения куки
    const getCookie = (name) => {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop().split(';').shift();
      return null;
    };
    
    // Читать токен из куки
    const t = getCookie('token');
    
    console.log('Token from cookie:', t ? t.substring(0, 50) + '...' : 'MISSING');
    
    if (!t) {
      toast.error('Not authenticated. Please login again.');
      return;
    }
    
    const columnName = prompt('Enter column name:');
    if (!columnName) return;
    
    try {
      const response = await fetch(`${API_URL}/api/boards/${boardId}/columns`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${t}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          title: columnName,
          position: columns.length
        })
      });
      
      console.log('Response status:', response.status);
      
      if (response.ok) {
        const newColumn = await response.json();
        console.log('Column created:', newColumn);
        
        // Добавить колонку в state (без reload!)
        setColumns([...columns, newColumn]);
        toast.success('Column created!');
        
        // НЕ делаем reload - колонка уже в state
        // window.location.reload(); ← УБРАТЬ!
      } else {
        const error = await response.json().catch(() => ({}));
        console.error('Error response:', error);
        toast.error(error.detail?.message || 'Failed to create column');
      }
    } catch (error) {
      console.error('Fetch error:', error);
      toast.error('Failed to create column');
    }
  };

  const toggleDarkMode = () => {
    const newDarkMode = !darkMode;
    setDarkMode(newDarkMode);
    localStorage.setItem('darkMode', String(newDarkMode));
    if (newDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-4">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => router.push('/')}
              >
                <ArrowLeft className="w-4 h-4 mr-2" />
                Back
              </Button>
              
              <div>
                <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {board?.name}
                </h1>
                {board?.description && (
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {board.description}
                  </p>
                )}
              </div>
            </div>

            <div className="flex items-center space-x-4">
              <Button variant="ghost" size="sm" onClick={handleShowStats}>
                <BarChart3 className="w-4 h-4 mr-2" />
                Stats
              </Button>

              <Button variant="ghost" size="sm" onClick={handleAddColumn}>
                <Plus className="w-4 h-4 mr-2" />
                Add Column
              </Button>

              <Button variant="ghost" size="sm">
                <Share2 className="w-4 h-4 mr-2" />
                Share
              </Button>

              <div className="flex items-center space-x-2 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 rounded-full">
                <Users className="w-4 h-4 text-gray-500 dark:text-gray-400" />
                <span className="text-sm text-gray-600 dark:text-gray-300">
                  {onlineUsers.length}
                </span>
              </div>

              <button
                onClick={toggleDarkMode}
                className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                {darkMode ? (
                  <Sun className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                ) : (
                  <Moon className="w-5 h-5 text-gray-600 dark:text-gray-300" />
                )}
              </button>

              <Avatar name={user?.name} size="sm" />
            </div>
          </div>
        </div>
      </header>

      {/* Board Content */}
      <main className="h-[calc(100vh-4rem)] overflow-x-auto">
        <DndContext
          collisionDetection={closestCorners}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="flex h-full p-6 space-x-4">
            {columns.map((column) => (
              <BoardColumn
                key={column.id}
                column={column}
                tasks={tasks.filter(t => t.column_id === column.id).sort((a, b) => a.position - b.position)}
                onTaskClick={handleTaskClick}
                onAddTask={handleAddTask}
                onDeleteColumn={handleDeleteColumn}
              />
            ))}
          </div>

          <DragOverlay>
            {activeTask ? (
              <div className="w-72 bg-white dark:bg-gray-800 rounded-lg p-4 shadow-lg border border-gray-200 dark:border-gray-700 rotate-3">
                <h4 className="font-medium text-gray-900 dark:text-gray-100">
                  {activeTask.title}
                </h4>
              </div>
            ) : null}
          </DragOverlay>
        </DndContext>
      </main>

      {/* Chat */}
      <BoardChat boardId={boardId} />

      {/* Add Task Modal */}
      <AddTaskForm
        isOpen={isAddTaskModalOpen}
        onClose={() => {
          setIsAddTaskModalOpen(false);
          setSelectedColumnId(null);
        }}
        columnId={selectedColumnId}
        boardId={boardId}
        onSuccess={handleTaskCreated}
      />

      {/* Task Detail Modal */}
      <TaskDetailModal
        isOpen={!!activeTask?.id && !activeTask.dragging}
        onClose={() => setActiveTask(null)}
        taskId={activeTask?.id}
        boardId={boardId}
      />

      {/* Stats Modal */}
      <Modal
        isOpen={isStatsOpen}
        onClose={() => setIsStatsOpen(false)}
        title="Board Statistics"
        size="lg"
      >
        <BurnDownChart data={statsData} />
      </Modal>
    </div>
  );
}
