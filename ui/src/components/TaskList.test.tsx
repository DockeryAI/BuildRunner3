/**
 * Tests for TaskList component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { TaskList } from './TaskList';
import * as api from '../services/api';

vi.mock('../services/api');

const mockTasks = [
  {
    id: 'task-1',
    name: 'Task 1',
    description: 'Description 1',
    status: 'completed',
    domain: 'backend',
    complexity: 'medium',
    estimated_minutes: 60,
    dependencies: [],
    retry_count: 0,
  },
  {
    id: 'task-2',
    name: 'Task 2',
    description: 'Description 2',
    status: 'in_progress',
    domain: 'frontend',
    complexity: 'simple',
    estimated_minutes: 30,
    dependencies: [],
    retry_count: 0,
  },
];

describe('TaskList', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading state initially', () => {
    vi.spyOn(api.orchestratorAPI, 'getTasks').mockImplementation(
      () => new Promise(() => {})
    );

    render(<TaskList />);
    expect(screen.getByText(/loading tasks/i)).toBeInTheDocument();
  });

  it('renders tasks when loaded', async () => {
    vi.spyOn(api.orchestratorAPI, 'getTasks').mockResolvedValue(mockTasks);

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Task 1')).toBeInTheDocument();
      expect(screen.getByText('Task 2')).toBeInTheDocument();
    });
  });

  it('renders error state on failure', async () => {
    vi.spyOn(api.orchestratorAPI, 'getTasks').mockRejectedValue(
      new Error('Failed to load')
    );

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText(/failed to load tasks/i)).toBeInTheDocument();
    });
  });

  it('renders empty state when no tasks', async () => {
    vi.spyOn(api.orchestratorAPI, 'getTasks').mockResolvedValue([]);

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText(/no tasks found/i)).toBeInTheDocument();
    });
  });

  it('displays task details correctly', async () => {
    vi.spyOn(api.orchestratorAPI, 'getTasks').mockResolvedValue(mockTasks);

    render(<TaskList />);

    await waitFor(() => {
      expect(screen.getByText('Task 1')).toBeInTheDocument();
      expect(screen.getByText('Description 1')).toBeInTheDocument();
      expect(screen.getByText('backend')).toBeInTheDocument();
      expect(screen.getByText('medium')).toBeInTheDocument();
    });
  });

  it('filters tasks by status', async () => {
    vi.spyOn(api.orchestratorAPI, 'getTasks').mockResolvedValue([mockTasks[0]]);

    render(<TaskList filterStatus="completed" />);

    await waitFor(() => {
      expect(api.orchestratorAPI.getTasks).toHaveBeenCalledWith('completed');
    });
  });

  it('calls onTaskClick when task is clicked', async () => {
    vi.spyOn(api.orchestratorAPI, 'getTasks').mockResolvedValue(mockTasks);
    const onTaskClick = vi.fn();

    const { container } = render(<TaskList onTaskClick={onTaskClick} />);

    await waitFor(() => {
      expect(screen.getByText('Task 1')).toBeInTheDocument();
    });

    const taskItem = container.querySelector('.task-item');
    if (taskItem) {
      taskItem.click();
      expect(onTaskClick).toHaveBeenCalled();
    }
  });
});
