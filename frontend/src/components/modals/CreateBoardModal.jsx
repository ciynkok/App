'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Modal, Button, Input, Textarea } from '../ui';
import { createBoard } from '../../lib/api/boards';
import toast from 'react-hot-toast';

const COLORS = [
  { name: 'Blue', value: '#3b82f6' },
  { name: 'Green', value: '#10b981' },
  { name: 'Purple', value: '#8b5cf6' },
  { name: 'Red', value: '#ef4444' },
  { name: 'Orange', value: '#f59e0b' },
  { name: 'Pink', value: '#ec4899' },
  { name: 'Teal', value: '#14b8a6' },
  { name: 'Indigo', value: '#6366f1' },
];

export default function CreateBoardModal({ isOpen, onClose, onCreate }) {
  const [isLoading, setIsLoading] = useState(false);
  const [selectedColor, setSelectedColor] = useState(COLORS[0].value);
  
  const { register, handleSubmit, formState: { errors }, reset } = useForm({
    defaultValues: {
      name: '',
      description: '',
    },
  });

  const handleClose = () => {
    onClose();
    reset();
    setSelectedColor(COLORS[0].value);
  };

  const onSubmit = async (data) => {
    setIsLoading(true);
    try {
      const newBoard = await createBoard({
        ...data,
        color: selectedColor,
      });
      toast.success('Board created successfully');
      onCreate(newBoard);
      handleClose();
    } catch (error) {
      toast.error(error.message || 'Failed to create board');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Create New Board"
      size="md"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Board Name"
          placeholder="Enter board name"
          error={errors.name?.message}
          {...register('name', {
            required: 'Board name is required',
            minLength: {
              value: 3,
              message: 'Name must be at least 3 characters',
            },
          })}
        />

        <Textarea
          label="Description"
          placeholder="Describe your board (optional)"
          rows={3}
          error={errors.description?.message}
          {...register('description', {
            maxLength: {
              value: 500,
              message: 'Description must be less than 500 characters',
            },
          })}
        />

        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Board Color
          </label>
          <div className="grid grid-cols-4 gap-2">
            {COLORS.map((color) => (
              <button
                key={color.value}
                type="button"
                onClick={() => setSelectedColor(color.value)}
                className={`
                  h-10 rounded-lg transition-transform
                  ${selectedColor === color.value ? 'ring-2 ring-offset-2 ring-gray-400 scale-105' : ''}
                `}
                style={{ backgroundColor: color.value }}
                title={color.name}
              />
            ))}
          </div>
        </div>

        <div className="flex justify-end space-x-3 pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={isLoading}>
            Create Board
          </Button>
        </div>
      </form>
    </Modal>
  );
}
