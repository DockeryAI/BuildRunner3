/**
 * Tests for Dashboard component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { Dashboard } from './Dashboard';
import * as api from '../services/api';
import * as useWebSocketHook from '../hooks/useWebSocket';

vi.mock('../services/api');
vi.mock('../hooks/useWebSocket');
vi.mock('./TaskList', () => ({
  TaskList: () => <div>TaskList Component</div>,
}));
vi.mock('./AgentPool', () => ({
  AgentPool: () => <div>AgentPool Component</div>,
}));
vi.mock('./TelemetryTimeline', () => ({
  TelemetryTimeline: () => <div>TelemetryTimeline Component</div>,
}));

const mockStatus = {
  status: 'running',
  batches_executed: 5,
  tasks_completed: 10,
  execution_errors: 0,
  completed_batches: 3,
  failed_batches: 0,
};

const mockProgress = {
  total: 20,
  completed: 10,
  failed: 0,
  in_progress: 2,
  pending: 8,
  blocked: 0,
  skipped: 0,
  percent_complete: 50,
};

describe('Dashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(api.orchestratorAPI, 'getStatus').mockResolvedValue(mockStatus);
    vi.spyOn(api.orchestratorAPI, 'getProgress').mockResolvedValue(mockProgress);
    vi.spyOn(useWebSocketHook, 'useWebSocket').mockReturnValue({
      isConnected: true,
      lastMessage: null,
      connectionError: null,
      sendMessage: vi.fn(),
      ping: vi.fn(),
      subscribe: vi.fn(),
      reconnect: vi.fn(),
      disconnect: vi.fn(),
    } as any);
  });

  it('renders dashboard header', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/BuildRunner 3.2 Dashboard/i)).toBeInTheDocument();
    });
  });

  it('displays connection status', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/Live/i)).toBeInTheDocument();
    });
  });

  it('displays orchestration status', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText(/RUNNING/i)).toBeInTheDocument();
    });
  });

  it('displays progress statistics', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('20')).toBeInTheDocument(); // total
      expect(screen.getByText('10')).toBeInTheDocument(); // completed
      expect(screen.getByText(/50.0% Complete/i)).toBeInTheDocument();
    });
  });

  it('renders tabs', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Tasks')).toBeInTheDocument();
      expect(screen.getByText('Agent Pool')).toBeInTheDocument();
      expect(screen.getByText('Telemetry')).toBeInTheDocument();
    });
  });

  it('shows TaskList by default', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('TaskList Component')).toBeInTheDocument();
    });
  });

  it('shows pause and stop buttons when running', async () => {
    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Pause')).toBeInTheDocument();
      expect(screen.getByText('Stop')).toBeInTheDocument();
    });
  });

  it('shows resume button when paused', async () => {
    vi.spyOn(api.orchestratorAPI, 'getStatus').mockResolvedValue({
      ...mockStatus,
      status: 'paused',
    });

    render(<Dashboard />);

    await waitFor(() => {
      expect(screen.getByText('Resume')).toBeInTheDocument();
    });
  });
});
