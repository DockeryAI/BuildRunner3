/**
 * Type definitions for BuildRunner UI
 */

export interface Task {
  id: string;
  name: string;
  description: string;
  status: 'pending' | 'ready' | 'in_progress' | 'completed' | 'failed' | 'blocked' | 'skipped';
  domain: string;
  complexity: string;
  estimated_minutes: number;
  dependencies: string[];
  started_at?: string;
  completed_at?: string;
  error_message?: string;
  retry_count: number;
}

export interface Progress {
  total: number;
  completed: number;
  failed: number;
  in_progress: number;
  pending: number;
  blocked: number;
  skipped: number;
  percent_complete: number;
}

export interface OrchestratorStatus {
  status: 'idle' | 'running' | 'paused' | 'completed' | 'failed';
  current_batch?: string;
  batches_executed: number;
  tasks_completed: number;
  execution_errors: number;
  completed_batches: number;
  failed_batches: number;
}

export interface TelemetryEvent {
  event_id: string;
  event_type: string;
  timestamp: string;
  session_id: string;
  metadata: Record<string, any>;
}

export interface Session {
  session_id: string;
  name: string;
  status: 'created' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  created_at: string;
  started_at?: string;
  completed_at?: string;
  total_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  in_progress_tasks: number;
  worker_id?: string;
  progress_percent: number;
}

export interface AgentPoolStatus {
  total_sessions: number;
  active_sessions: number;
  paused_sessions: number;
  completed_sessions: number;
  failed_sessions: number;
  max_concurrent: number;
  available_slots: number;
}

export interface WebSocketMessage {
  type: 'connection' | 'task_update' | 'telemetry_event' | 'progress_update' | 'session_update' | 'heartbeat' | 'error';
  timestamp: string;
  [key: string]: any;
}

export interface Statistics {
  total_events: number;
  events_by_type: Record<string, number>;
  oldest_event?: string;
  newest_event?: string;
}
