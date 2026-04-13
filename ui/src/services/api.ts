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
  IntelItem,
  IntelAlerts,
  IntelImprovement,
  IntelFilters,
  DealItem,
  Hunt,
  PriceHistoryPoint,
  DealFilters,
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

// Project API
export const projectAPI = {
  async listProjects(): Promise<any> {
    const response = await api.get('/api/project/list');
    return response.data;
  },

  async attachProject(projectPath: string, dryRun: boolean = false): Promise<any> {
    const response = await api.post('/api/project/attach', {
      project_path: projectPath,
      dry_run: dryRun,
    });
    return response.data;
  },

  async initProject(projectName: string, projectRoot?: string): Promise<any> {
    const response = await api.post('/api/project/init', {
      project_name: projectName,
      project_root: projectRoot,
    });
    return response.data;
  },

  async setAlias(projectPath: string, alias: string): Promise<any> {
    const response = await api.post('/api/project/alias', {
      project_path: projectPath,
      alias: alias,
    });
    return response.data;
  },
};

// Intel API — talks to Lockwood intelligence service
const INTEL_API_URL = import.meta.env.VITE_INTEL_API_URL || 'http://localhost:8100';

const intelApi = axios.create({
  baseURL: INTEL_API_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const intelAPI = {
  async getIntelItems(filters?: IntelFilters): Promise<{ items: IntelItem[]; count: number }> {
    const params: Record<string, any> = {};
    if (filters?.priority) params.priority = filters.priority;
    if (filters?.category) params.category = filters.category;
    if (filters?.source_type) params.source_type = filters.source_type;
    if (filters?.read !== undefined) params.read = filters.read;
    if (filters?.days) params.days = filters.days;
    if (filters?.limit) params.limit = filters.limit;
    const response = await intelApi.get('/api/intel/items', { params });
    return response.data;
  },

  async getIntelAlerts(): Promise<IntelAlerts> {
    const response = await intelApi.get('/api/intel/alerts');
    return response.data;
  },

  async dismissIntelItem(id: number): Promise<{ status: string }> {
    const response = await intelApi.post(`/api/intel/items/${id}/dismiss`);
    return response.data;
  },

  async markIntelRead(id: number): Promise<{ status: string }> {
    const response = await intelApi.post(`/api/intel/items/${id}/read`);
    return response.data;
  },

  async saveToLibrary(id: number): Promise<{ status: string }> {
    const response = await intelApi.post(`/api/intel/items/${id}/save-to-library`);
    return response.data;
  },

  async getIntelImprovements(
    status?: string
  ): Promise<{ improvements: IntelImprovement[]; count: number }> {
    try {
      const params: Record<string, any> = {};
      if (status) params.status = status;
      const response = await intelApi.get('/api/intel/improvements', { params });
      return response.data;
    } catch {
      return { improvements: [], count: 0 };
    }
  },

  async updateImprovementStatus(
    id: number,
    status: string,
    buildSpecName?: string
  ): Promise<{ status: string }> {
    const body: Record<string, any> = { status };
    if (buildSpecName) body.build_spec_name = buildSpecName;
    const response = await intelApi.post(`/api/intel/improvements/${id}/status`, body);
    return response.data;
  },

  async getImprovementHistory(): Promise<{ improvements: IntelImprovement[]; count: number }> {
    try {
      const response = await intelApi.get('/api/intel/improvements', {
        params: { status: 'built' },
      });
      return response.data;
    } catch {
      return { improvements: [], count: 0 };
    }
  },
};

// Deals API — talks to Lockwood intelligence service (same base URL as intel)
export const dealsAPI = {
  async getDealItems(filters?: DealFilters): Promise<{ items: DealItem[]; count: number }> {
    const params: Record<string, any> = {};
    if (filters?.hunt_id) params.hunt_id = filters.hunt_id;
    if (filters?.min_score !== undefined) params.min_score = filters.min_score;
    if (filters?.limit) params.limit = filters.limit;
    if (filters?.ready_only !== undefined) params.ready_only = filters.ready_only;
    if (filters?.in_stock_only !== undefined) params.in_stock_only = filters.in_stock_only;
    if (filters?.seller_verified_only !== undefined)
      params.seller_verified_only = filters.seller_verified_only;
    const response = await intelApi.get('/api/deals/items', { params });
    return response.data;
  },

  async getHunts(): Promise<{ hunts: Hunt[] }> {
    const response = await intelApi.get('/api/deals/hunts');
    return response.data;
  },

  async getArchivedHunts(): Promise<{ hunts: Hunt[]; count: number }> {
    const response = await intelApi.get('/api/deals/hunts/archived');
    return response.data;
  },

  async createHunt(
    hunt: Omit<Hunt, 'id' | 'created_at' | 'active' | 'items_count' | 'last_checked'>
  ): Promise<Hunt> {
    const response = await intelApi.post('/api/deals/hunts', hunt);
    return response.data;
  },

  async archiveHunt(id: number): Promise<{ status: string }> {
    const response = await intelApi.post(`/api/deals/hunts/${id}/archive`);
    return response.data;
  },

  async getPriceHistory(dealItemId: number): Promise<{ history: PriceHistoryPoint[] }> {
    const response = await intelApi.get(`/api/deals/price-history/${dealItemId}`);
    return response.data;
  },

  async dismissDeal(id: number): Promise<{ status: string }> {
    const response = await intelApi.post(`/api/deals/items/${id}/dismiss`);
    return response.data;
  },

  async markDealRead(id: number): Promise<{ status: string }> {
    const response = await intelApi.post(`/api/deals/items/${id}/read`);
    return response.data;
  },

  async updateDeal(
    id: number,
    updates: {
      purchased?: number;
      delivery_status?: string;
      purchased_price?: number;
      tracking_number?: string;
      carrier?: string;
    }
  ): Promise<{ status: string }> {
    const response = await intelApi.patch(`/api/deals/items/${id}`, updates);
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
