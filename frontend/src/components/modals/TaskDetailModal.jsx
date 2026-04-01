'use client';

import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { format } from 'date-fns';
import { Modal, Button, Input, Textarea, Select, Avatar, Badge } from '../ui';
import { updateTask, deleteTask, getComments, addComment, deleteComment } from '../../lib/api/tasks';
import { useBoardStore } from '../../store/boardStore';
import { useUserStore } from '../../store/userStore';
import { X, Trash2, Edit2, Calendar, Flag, User } from 'lucide-react';
import toast from 'react-hot-toast';

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

const getPriorityColor = (priority) => {
  switch (priority) {
    case 'high': return 'danger';
    case 'medium': return 'warning';
    case 'low': return 'success';
    default: return 'default';
  }
};

export default function TaskDetailModal({ isOpen, onClose, taskId, boardId }) {
  const { user } = useUserStore();
  const { tasks, updateTask: updateTaskStore, removeTask: removeTaskStore, comments, setComments, addComment: addCommentStore, removeComment: removeCommentStore } = useBoardStore();
  const [isLoading, setIsLoading] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [commentText, setCommentText] = useState('');
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);

  const task = tasks.find(t => t.id === taskId);

  const { register, handleSubmit, formState: { errors }, reset } = useForm({
    defaultValues: {
      title: '',
      description: '',
      priority: 'medium',
      deadline: '',
    },
  });

  useEffect(() => {
    if (task && isOpen) {
      reset({
        title: task.title || '',
        description: task.description || '',
        priority: task.priority || 'medium',
        deadline: task.deadline ? format(new Date(task.deadline), 'yyyy-MM-dd') : '',
      });
      loadComments();
    }
  }, [task, isOpen, reset]);

  const loadComments = async () => {
    if (!taskId) return;
    try {
      const data = await getComments(taskId);
      setComments(taskId, data);
    } catch (error) {
      console.error('Failed to load comments:', error);
    }
  };

  const handleUpdate = async (data) => {
    setIsLoading(true);
    try {
      const updated = await updateTask(taskId, data);
      updateTaskStore(taskId, updated);
      toast.success('Task updated');
      setIsEditing(false);
    } catch (error) {
      toast.error(error.message || 'Failed to update task');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Are you sure you want to delete this task?')) return;
    
    setIsLoading(true);
    try {
      await deleteTask(taskId);
      removeTaskStore(taskId);
      toast.success('Task deleted');
      onClose();
    } catch (error) {
      toast.error(error.message || 'Failed to delete task');
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddComment = async (e) => {
    e.preventDefault();
    if (!commentText.trim()) return;

    setIsSubmittingComment(true);
    try {
      const newComment = await addComment(taskId, commentText);
      addCommentStore(taskId, newComment);
      setCommentText('');
      toast.success('Comment added');
    } catch (error) {
      toast.error(error.message || 'Failed to add comment');
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const handleDeleteComment = async (commentId) => {
    try {
      await deleteComment(taskId, commentId);
      removeCommentStore(taskId, commentId);
      toast.success('Comment deleted');
    } catch (error) {
      toast.error(error.message || 'Failed to delete comment');
    }
  };

  const taskComments = comments[taskId] || [];

  if (!task) return null;

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title=""
      size="lg"
    >
      <div className="space-y-6">
        {/* Header */}
        <div className="flex justify-between items-start">
          {isEditing ? (
            <form onSubmit={handleSubmit(handleUpdate)} className="flex-1 space-y-4">
              <Input
                label="Title"
                error={errors.title?.message}
                {...register('title', { required: 'Title is required' })}
              />
              <Textarea
                label="Description"
                error={errors.description?.message}
                {...register('description')}
              />
              <div className="grid grid-cols-2 gap-4">
                <Select
                  label="Priority"
                  options={PRIORITY_OPTIONS}
                  {...register('priority')}
                />
                <Input
                  label="Deadline"
                  type="date"
                  {...register('deadline')}
                />
              </div>
              <div className="flex justify-end space-x-3">
                <Button type="button" variant="secondary" onClick={() => setIsEditing(false)}>
                  Cancel
                </Button>
                <Button type="submit" loading={isLoading}>
                  Save Changes
                </Button>
              </div>
            </form>
          ) : (
            <div className="flex-1">
              <div className="flex justify-between items-start mb-4">
                <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                  {task.title}
                </h2>
                <div className="flex items-center space-x-2">
                  {user && (task.assigneeId === user.id || task.createdBy === user.id) && (
                    <>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setIsEditing(true)}
                      >
                        <Edit2 className="w-4 h-4" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={handleDelete}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Trash2 className="w-4 h-4" />
                      </Button>
                    </>
                  )}
                </div>
              </div>

              <div className="flex flex-wrap gap-2 mb-4">
                <Badge variant={getPriorityColor(task.priority)}>
                  <Flag className="w-3 h-3 mr-1" />
                  {task.priority}
                </Badge>
                {task.deadline && (
                  <Badge variant="default">
                    <Calendar className="w-3 h-3 mr-1" />
                    {task.deadline ? format(new Date(task.deadline), 'MMM d, yyyy') : 'No deadline'}
                  </Badge>
                )}
                {task.assignee && (
                  <div className="flex items-center space-x-1">
                    <Avatar name={task.assignee.name} size="sm" />
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {task.assignee.name}
                    </span>
                  </div>
                )}
              </div>

              {task.description && (
                <p className="text-gray-600 dark:text-gray-400">
                  {task.description}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Comments Section */}
        <div className="border-t dark:border-gray-700 pt-6">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
            Comments ({taskComments.length})
          </h3>

          {/* Comments List */}
          <div className="space-y-4 mb-6 max-h-64 overflow-y-auto">
            {taskComments.length === 0 ? (
              <p className="text-sm text-gray-500 dark:text-gray-400 text-center py-4">
                No comments yet
              </p>
            ) : (
              taskComments.map((comment) => (
                <div
                  key={comment.id}
                  className="flex space-x-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <Avatar name={comment.author?.name || 'User'} size="sm" />
                  <div className="flex-1">
                    <div className="flex justify-between items-start">
                      <span className="font-medium text-sm text-gray-900 dark:text-gray-100">
                        {comment.author?.name || 'Anonymous'}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-gray-400">
                        {comment.createdAt ? format(new Date(comment.createdAt), 'MMM d, HH:mm') : 'Just now'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-gray-400 mt-1">
                      {comment.content || comment.text}
                    </p>
                    {user && comment.authorId === user.id && (
                      <button
                        onClick={() => handleDeleteComment(comment.id)}
                        className="text-xs text-red-600 hover:text-red-700 mt-2"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Add Comment Form */}
          <form onSubmit={handleAddComment} className="flex space-x-3">
            <Avatar name={user?.name || 'User'} size="sm" />
            <div className="flex-1 flex space-x-2">
              <input
                type="text"
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
                placeholder="Write a comment..."
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
              <Button
                type="submit"
                disabled={!commentText.trim() || isSubmittingComment}
                loading={isSubmittingComment}
              >
                Send
              </Button>
            </div>
          </form>
        </div>
      </div>
    </Modal>
  );
}
