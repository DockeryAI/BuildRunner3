/**
 * API Service for BuildRunner
 *
 * Provides methods to interact with the FastAPI backend
 */

import axios from 'axios';
import type {
  Task,
  Progress,
  OrchestratorStatus,
  TelemetryEvent,
  Session,
  AgentPoolStatus,
  Statistics,
} from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Orchestrator API
export const orchestratorAPI = {
  async getStatus(): Promise<OrchestratorStatus> {
    const response = await api.get('/api/orchestrator/status');
    return response.data;
  },

  async getProgress(): Promise<Progress> {
    const response = await api.get('/api/orchestrator/progress');
    return response.data;
  },

  async getTasks(status?: string): Promise<Task[]> {
    const params = status ? { status } : {};
    const response = await api.get('/api/orchestrator/tasks', { params });
    return response.data;
  },

  async getTask(taskId: string): Promise<Task> {
    const response = await api.get(`/api/orchestrator/tasks/${taskId}`);
    return response.data;
  },

  async pause(): Promise<{ success: boolean; status: string }> {
    const response = await api.post('/api/orchestrator/control/pause');
    return response.data;
  },

  async resume(): Promise<{ success: boolean; status: string }> {
    const response = await api.post('/api/orchestrator/control/resume');
    return response.data;
  },

  async stop(): Promise<{ success: boolean; status: string }> {
    const response = await api.post('/api/orchestrator/control/stop');
    return response.data;
  },

  async getStats(): Promise<any> {
    const response = await api.get('/api/orchestrator/stats');
    return response.data;
  },
};

// Telemetry API
export const telemetryAPI = {
  async getEvents(params?: {
    event_type?: string;
    session_id?: string;
    limit?: number;
  }): Promise<TelemetryEvent[]> {
    const response = await api.get('/api/telemetry/events', { params });
    return response.data;
  },

  async getRecentEvents(count: number = 50): Promise<TelemetryEvent[]> {
    const response = await api.get('/api/telemetry/events/recent', {
      params: { count },
    });
    return response.data;
  },

  async getTimeline(params?: {
    start_time?: string;
    end_time?: string;
    event_types?: string;
    limit?: number;
  }): Promise<{
    events: TelemetryEvent[];
    total: number;
    start_time?: string;
    end_time?: string;
  }> {
    const response = await api.get('/api/telemetry/timeline', { params });
    return response.data;
  },

  async getStatistics(): Promise<Statistics> {
    const response = await api.get('/api/telemetry/statistics');
    return response.data;
  },

  async getMetrics(): Promise<any> {
    const response = await api.get('/api/telemetry/metrics');
    return response.data;
  },

  async getPerformance(): Promise<any> {
    const response = await api.get('/api/telemetry/performance');
    return response.data;
  },
};

// Agents API
export const agentsAPI = {
  async getPool(): Promise<AgentPoolStatus> {
    const response = await api.get('/api/agents/pool');
    return response.data;
  },

  async getSessions(status?: string): Promise<Session[]> {
    const params = status ? { status } : {};
    const response = await api.get('/api/agents/sessions', { params });
    return response.data;
  },

  async getSession(sessionId: string): Promise<Session> {
    const response = await api.get(`/api/agents/sessions/${sessionId}`);
    return response.data;
  },

  async getActiveSessions(): Promise<Session[]> {
    const response = await api.get('/api/agents/active');
    return response.data;
  },

  async getWorkers(): Promise<any[]> {
    const response = await api.get('/api/agents/workers');
    return response.data;
  },

  async getDashboard(): Promise<any> {
    const response = await api.get('/api/agents/dashboard');
    return response.data;
  },

  async getMetrics(): Promise<any> {
    const response = await api.get('/api/agents/metrics');
    return response.data;
  },
};

// Health check
export const healthAPI = {
  async check(): Promise<{ status: string; service: string; version: string }> {
    const response = await api.get('/health');
    return response.data;
  },
};

export default api;
