/**
 * TaskList Component
 *
 * Displays list of tasks with their status and progress
 */

import { useEffect, useState } from 'react';
import { orchestratorAPI } from '../services/api';
import type { Task } from '../types';
import './TaskList.css';

interface TaskListProps {
  filterStatus?: string;
  onTaskClick?: (task: Task) => void;
}

export function TaskList({ filterStatus, onTaskClick }: TaskListProps) {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadTasks();
    const interval = setInterval(loadTasks, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, [filterStatus]);

  const loadTasks = async () => {
    try {
      setLoading(true);
      const data = await orchestratorAPI.getTasks(filterStatus);
      setTasks(data);
      setError(null);
    } catch (err) {
      setError('Failed to load tasks');
      console.error('Error loading tasks:', err);
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: string): string => {
    const colors: Record<string, string> = {
      pending: '#888',
      ready: '#0066cc',
      in_progress: '#ff9800',
      completed: '#4caf50',
      failed: '#f44336',
      blocked: '#9c27b0',
      skipped: '#607d8b',
    };
    return colors[status] || '#888';
  };

  if (loading && tasks.length === 0) {
    return <div className="task-list-loading">Loading tasks...</div>;
  }

  if (error) {
    return <div className="task-list-error">{error}</div>;
  }

  if (tasks.length === 0) {
    return <div className="task-list-empty">No tasks found</div>;
  }

  return (
    <div className="task-list">
      <h2>Tasks {filterStatus && `(${filterStatus})`}</h2>
      <div className="task-list-items">
        {tasks.map((task) => (
          <div
            key={task.id}
            className="task-item"
            onClick={() => onTaskClick?.(task)}
          >
            <div className="task-header">
              <span
                className="task-status"
                style={{ backgroundColor: getStatusColor(task.status) }}
              >
                {task.status}
              </span>
              <span className="task-name">{task.name}</span>
            </div>
            <div className="task-details">
              <span className="task-domain">{task.domain}</span>
              <span className="task-complexity">{task.complexity}</span>
              <span className="task-estimate">{task.estimated_minutes}min</span>
            </div>
            <div className="task-description">{task.description}</div>
            {task.error_message && (
              <div className="task-error">{task.error_message}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default TaskList;
