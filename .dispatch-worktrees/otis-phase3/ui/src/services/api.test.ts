/**
 * Tests for API service
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import axios from 'axios';
import { orchestratorAPI, telemetryAPI, agentsAPI, healthAPI } from './api';

vi.mock('axios');
const mockedAxios = axios as any;

describe('orchestratorAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getStatus should fetch orchestrator status', async () => {
    const mockStatus = { status: 'running', batches_executed: 5 };
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockStatus }),
    });

    const result = await orchestratorAPI.getStatus();
    expect(result).toEqual(mockStatus);
  });

  it('getProgress should fetch progress', async () => {
    const mockProgress = { total: 10, completed: 5, percent_complete: 50 };
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockProgress }),
    });

    const result = await orchestratorAPI.getProgress();
    expect(result).toEqual(mockProgress);
  });

  it('getTasks should fetch tasks', async () => {
    const mockTasks = [{ id: '1', name: 'Task 1' }];
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockTasks }),
    });

    const result = await orchestratorAPI.getTasks();
    expect(result).toEqual(mockTasks);
  });

  it('pause should send pause request', async () => {
    const mockResponse = { success: true, status: 'paused' };
    mockedAxios.create.mockReturnValue({
      post: vi.fn().mockResolvedValue({ data: mockResponse }),
    });

    const result = await orchestratorAPI.pause();
    expect(result).toEqual(mockResponse);
  });
});

describe('telemetryAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getEvents should fetch events', async () => {
    const mockEvents = [{ event_id: '1', event_type: 'TASK_STARTED' }];
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockEvents }),
    });

    const result = await telemetryAPI.getEvents();
    expect(result).toEqual(mockEvents);
  });

  it('getStatistics should fetch statistics', async () => {
    const mockStats = { total_events: 100, events_by_type: {} };
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockStats }),
    });

    const result = await telemetryAPI.getStatistics();
    expect(result).toEqual(mockStats);
  });
});

describe('agentsAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getPool should fetch agent pool status', async () => {
    const mockPool = { total_sessions: 4, active_sessions: 2 };
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockPool }),
    });

    const result = await agentsAPI.getPool();
    expect(result).toEqual(mockPool);
  });

  it('getSessions should fetch sessions', async () => {
    const mockSessions = [{ session_id: '1', name: 'Session 1' }];
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockSessions }),
    });

    const result = await agentsAPI.getSessions();
    expect(result).toEqual(mockSessions);
  });
});

describe('healthAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('check should fetch health status', async () => {
    const mockHealth = { status: 'healthy', service: 'BuildRunner API' };
    mockedAxios.create.mockReturnValue({
      get: vi.fn().mockResolvedValue({ data: mockHealth }),
    });

    const result = await healthAPI.check();
    expect(result).toEqual(mockHealth);
  });
});
