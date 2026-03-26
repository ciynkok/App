'use client';

import { useDroppable } from '@dnd-kit/core';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import TaskCard from './TaskCard';
import { Plus } from 'lucide-react';

export default function BoardColumn({ column, tasks, onTaskClick, onAddTask }) {
  const { setNodeRef, isOver } = useDroppable({
    id: column.id,
  });

  return (
    <div
      className={`
        flex-shrink-0 w-80 max-h-full
        bg-gray-100 dark:bg-gray-800/50
        rounded-lg p-4
        flex flex-col
        ${isOver ? 'drag-over' : ''}
      `}
    >
      {/* Column Header */}
      <div className="flex justify-between items-center mb-4">
        <div className="flex items-center space-x-2">
          <div
            className="w-3 h-3 rounded-full"
            style={{ backgroundColor: column.color || '#6b7280' }}
          />
          <h3 className="font-semibold text-gray-900 dark:text-gray-100">
            {column.name}
          </h3>
          <span className="text-sm text-gray-500 dark:text-gray-400">
            ({tasks.length})
          </span>
        </div>
        <button
          onClick={() => onAddTask(column.id)}
          className="p-1 rounded hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-500 dark:text-gray-400"
        >
          <Plus className="w-4 h-4" />
        </button>
      </div>

      {/* Tasks List */}
      <div
        ref={setNodeRef}
        className="flex-1 overflow-y-auto pr-2"
      >
        <SortableContext
          items={tasks.map(t => t.id)}
          strategy={verticalListSortingStrategy}
        >
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onClick={onTaskClick}
            />
          ))}
        </SortableContext>
        
        {tasks.length === 0 && (
          <div className="text-center py-8 text-gray-400 dark:text-gray-500 text-sm">
            No tasks yet
          </div>
        )}
      </div>
    </div>
  );
}
