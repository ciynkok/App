'use client';

import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { motion } from 'framer-motion';
import { Calendar, CheckCircle2, Circle, Clock3, Flag, SearchCheck } from 'lucide-react';
import { Avatar, Badge } from '../ui';

const getPriorityColor = (priority) => {
  switch (priority) {
    case 'high': return 'danger';
    case 'medium': return 'warning';
    case 'low': return 'success';
    default: return 'default';
  }
};

const STATUS_META = {
  todo: {
    label: 'To do',
    variant: 'default',
    icon: Circle,
  },
  in_progress: {
    label: 'In progress',
    variant: 'primary',
    icon: Clock3,
  },
  review: {
    label: 'Review',
    variant: 'warning',
    icon: SearchCheck,
  },
  done: {
    label: 'Done',
    variant: 'success',
    icon: CheckCircle2,
  },
};

export default function TaskCard({ task, onClick }) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const statusMeta = STATUS_META[task.status] || STATUS_META.todo;
  const StatusIcon = statusMeta.icon;

  return (
    <motion.div
      ref={setNodeRef}
      style={style}
      {...attributes}
      layoutId={task.id}
      className={`
        bg-white dark:bg-gray-800 rounded-lg p-4 mb-3
        border border-gray-200 dark:border-gray-700
        shadow-sm hover:shadow-md transition-shadow
        cursor-move
        ${isDragging ? 'dragging rotate-2 opacity-50' : ''}
      `}
      onClick={() => !isDragging && onClick(task)}
    >
      {/* Drag handle — видная полоска для перетаскивания */}
      <div
        {...listeners}
        onClick={(e) => e.stopPropagation()}
        className="cursor-move mb-3 pb-2 -mx-4 px-4 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-t-lg transition-colors"
        title="Drag to move"
      >
        <div className="flex justify-center">
          <div className="w-12 h-1.5 bg-gray-400 dark:bg-gray-500 rounded-full"></div>
        </div>
      </div>
      
      {/* Content — клик открывает задачу */}
      <div>
        <div className="flex justify-between items-start mb-2">
          <h4 className="font-medium text-gray-900 dark:text-gray-100 line-clamp-2">
            {task.title}
          </h4>
          {task.priority && (
            <Badge variant={getPriorityColor(task.priority)} className="flex-shrink-0 ml-2">
              <Flag className="w-3 h-3" />
            </Badge>
          )}
        </div>

        <div className="mb-3">
          <Badge variant={statusMeta.variant}>
            <StatusIcon className="w-3 h-3 mr-1" />
            {statusMeta.label}
          </Badge>
        </div>

        {task.description && (
          <p className="text-sm text-gray-600 dark:text-gray-400 mb-3 line-clamp-2">
            {task.description}
          </p>
        )}

        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            {task.assignee && (
              <Avatar name={task.assignee.name} size="sm" />
            )}
            {task.deadline && (
              <span className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                <Calendar className="w-3 h-3 mr-1" />
                {new Date(task.deadline).toLocaleDateString()}
              </span>
            )}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
