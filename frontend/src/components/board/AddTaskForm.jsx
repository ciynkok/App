'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { Modal, Button, Input, Textarea, Select } from '../ui';
import { createTask } from '../../lib/api/tasks';
import toast from 'react-hot-toast';

const PRIORITY_OPTIONS = [
  { value: 'low', label: 'Low' },
  { value: 'medium', label: 'Medium' },
  { value: 'high', label: 'High' },
];

export default function AddTaskForm({ isOpen, onClose, columnId, boardId, onSuccess }) {
  const [isLoading, setIsLoading] = useState(false);
  
  const { register, handleSubmit, formState: { errors }, reset } = useForm({
    defaultValues: {
      title: '',
      description: '',
      priority: 'medium',
      deadline: '',
    },
  });

  const handleClose = () => {
    onClose();
    reset();
  };

  const onSubmit = async (data) => {
    setIsLoading(true);
    try {
      const newTask = await createTask({
        title: data.title,
        description: data.description,
        priority: data.priority,
        deadline: data.deadline,
        column_id: columnId,
        position: 0,
      });
      toast.success('Task created');
      onSuccess(newTask);
      handleClose();
    } catch (error) {
      toast.error(error.message || 'Failed to create task');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title="Add New Task"
      size="md"
    >
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <Input
          label="Task Title"
          placeholder="Enter task title"
          error={errors.title?.message}
          {...register('title', {
            required: 'Title is required',
            minLength: {
              value: 3,
              message: 'Title must be at least 3 characters',
            },
          })}
        />

        <Textarea
          label="Description"
          placeholder="Describe the task (optional)"
          rows={3}
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

        <div className="flex justify-end space-x-3 pt-4">
          <Button type="button" variant="secondary" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" loading={isLoading}>
            Create Task
          </Button>
        </div>
      </form>
    </Modal>
  );
}
