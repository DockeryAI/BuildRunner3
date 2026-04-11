/**
 * Tests for API service
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

const { mockGet, mockPost } = vi.hoisted(() => ({
  mockGet: vi.fn(),
  mockPost: vi.fn(),
}));

vi.mock('axios', () => ({
  __esModule: true,
  default: {
    create: vi.fn(() => ({
      get: mockGet,
      post: mockPost,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    })),
  },
}));

import { orchestratorAPI, telemetryAPI, agentsAPI, healthAPI } from './api';

describe('orchestratorAPI', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('getStatus should fetch orchestrator status', async () => {
    const mockStatus = { status: 'running', batches_executed: 5 };
    mockGet.mockResolvedValueOnce({ data: mockStatus });

    const result = await orchestratorAPI.getStatus();
    expect(result).toEqual(mockStatus);
  });

  it('getProgress should fetch progress', async () => {
    const mockProgress = { total: 10, completed: 5, percent_complete: 50 };
    mockGet.mockResolvedValueOnce({ data: mockProgress });

    const result = await orchestratorAPI.getProgress();
    expect(result).toEqual(mockProgress);
  });

  it('getTasks should fetch tasks', async () => {
    const mockTasks = [{ id: '1', name: 'Task 1' }];
    mockGet.mockResolvedValueOnce({ data: mockTasks });

    const result = await orchestratorAPI.getTasks();
    expect(result).toEqual(mockTasks);
  });

  it('pause should send pause request', async () => {
    const mockResponse = { success: true, status: 'paused' };
    mockPost.mockResolvedValueOnce({ data: mockResponse });

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
    mockGet.mockResolvedValueOnce({ data: mockEvents });

    const result = await telemetryAPI.getEvents();
    expect(result).toEqual(mockEvents);
  });

  it('getStatistics should fetch statistics', async () => {
    const mockStats = { total_events: 100, events_by_type: {} };
    mockGet.mockResolvedValueOnce({ data: mockStats });

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
    mockGet.mockResolvedValueOnce({ data: mockPool });

    const result = await agentsAPI.getPool();
    expect(result).toEqual(mockPool);
  });

  it('getSessions should fetch sessions', async () => {
    const mockSessions = [{ session_id: '1', name: 'Session 1' }];
    mockGet.mockResolvedValueOnce({ data: mockSessions });

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
    mockGet.mockResolvedValueOnce({ data: mockHealth });

    const result = await healthAPI.check();
    expect(result).toEqual(mockHealth);
  });
});
