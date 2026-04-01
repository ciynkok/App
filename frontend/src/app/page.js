'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { format } from 'date-fns';
import { useAuth } from '../hooks/useAuth';
import { getBoards, deleteBoard as deleteBoardApi } from '../lib/api/boards';
import { Button, Card, Avatar, Modal } from '../components/ui';
import { Plus, Trash2, Layout, LogOut, Moon, Sun, Users } from 'lucide-react';
import toast from 'react-hot-toast';
import CreateBoardModal from '../components/modals/CreateBoardModal';

export default function HomePage() {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuth();
  const [boards, setBoards] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [boardToDelete, setBoardToDelete] = useState(null);
  const [darkMode, setDarkMode] = useState(false);

  useEffect(() => {
    // Check for dark mode preference
    const isDark = localStorage.getItem('darkMode') === 'true';
    setDarkMode(isDark);
    if (isDark) {
      document.documentElement.classList.add('dark');
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated === false) {
      router.push('/auth/login');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadBoards();
    }
  }, [isAuthenticated]);

  const loadBoards = async () => {
    setIsLoading(true);
    try {
      const data = await getBoards();
      setBoards(data);
    } catch (error) {
      toast.error('Failed to load boards');
      console.error(error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteBoard = async () => {
    if (!boardToDelete) return;
    
    try {
      await deleteBoardApi(boardToDelete);
      setBoards(boards.filter(b => b.id !== boardToDelete));
      toast.success('Board deleted');
      setIsDeleteModalOpen(false);
      setBoardToDelete(null);
    } catch (error) {
      toast.error('Failed to delete board');
      console.error(error);
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

  const openDeleteModal = (boardId) => {
    setBoardToDelete(boardId);
    setIsDeleteModalOpen(true);
  };

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center space-x-3">
              <Layout className="w-8 h-8 text-primary-600" />
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                Collaborative Dashboard
              </h1>
            </div>
            
            <div className="flex items-center space-x-4">
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
              
              <div className="flex items-center space-x-2">
                <Avatar name={user?.name} size="sm" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {user?.name}
                </span>
              </div>
              
              <Button variant="ghost" size="sm" onClick={logout}>
                <LogOut className="w-4 h-4 mr-2" />
                Logout
              </Button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-8">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
              My Boards
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Manage and collaborate on your projects
            </p>
          </div>
          
          <Button onClick={() => setIsCreateModalOpen(true)}>
            <Plus className="w-5 h-5 mr-2" />
            Create Board
          </Button>
        </div>

        {/* Boards Grid */}
        {isLoading ? (
          <div className="flex justify-center items-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary-600"></div>
          </div>
        ) : boards.length === 0 ? (
          <Card className="text-center py-12">
            <Layout className="w-16 h-16 mx-auto text-gray-400 mb-4" />
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              No boards yet
            </h3>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Create your first board to get started
            </p>
            <Button onClick={() => setIsCreateModalOpen(true)}>
              <Plus className="w-5 h-5 mr-2" />
              Create Board
            </Button>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {boards.map((board) => (
              <Card
                key={board.id}
                className="hover:shadow-lg transition-shadow cursor-pointer group"
              >
                <Link href={`/dashboard/${board.id}`}>
                  <div
                    className="h-32 rounded-lg mb-4"
                    style={{ backgroundColor: board.color || '#3b82f6' }}
                  />
                  
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 group-hover:text-primary-600 transition-colors">
                      {board.name}
                    </h3>
                    
                    <button
                      onClick={(e) => {
                        e.preventDefault();
                        openDeleteModal(board.id);
                      }}
                      className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/20 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
                    {board.description || 'No description'}
                  </p>
                  
                  <div className="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
                    <span>
                      {/*format(new Date(board.createdAt), 'MMM d, yyyy')*/}
                      {board.createdAt ? format(new Date(board.createdAt), 'MMM d, yyyy') : 'N/A'}
                    </span>
                    <div className="flex items-center">
                      <Users className="w-3 h-3 mr-1" />
                      <span>{board.memberCount || 1} members</span>
                    </div>
                  </div>
                </Link>
              </Card>
            ))}
          </div>
        )}
      </main>

      {/* Create Board Modal */}
      <CreateBoardModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onCreate={(newBoard) => {
          setBoards([...boards, newBoard]);
          setIsCreateModalOpen(false);
        }}
      />

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Board"
        size="sm"
      >
        <p className="text-gray-600 dark:text-gray-400 mb-6">
          Are you sure you want to delete this board? This action cannot be undone.
        </p>
        <div className="flex justify-end space-x-3">
          <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>
            Cancel
          </Button>
          <Button variant="danger" onClick={handleDeleteBoard}>
            Delete
          </Button>
        </div>
      </Modal>
    </div>
  );
}
