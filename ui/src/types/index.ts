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
  type:
    | 'connection'
    | 'task_update'
    | 'telemetry_event'
    | 'progress_update'
    | 'session_update'
    | 'heartbeat'
    | 'error';
  timestamp: string;
  [key: string]: any;
}

export interface Statistics {
  total_events: number;
  events_by_type: Record<string, number>;
  oldest_event?: string;
  newest_event?: string;
}

// --- Intelligence Tab Types ---

export interface IntelItem {
  id: number;
  title: string;
  source: string;
  url: string;
  source_type: string; // Official | Community | Blog
  category: string; // api-change | model-release | community-tool | ecosystem-news | cluster-relevant | general-news
  priority: 'critical' | 'high' | 'medium' | 'low';
  score: number;
  summary: string;
  opus_synthesis: string | null;
  br3_improvement: boolean;
  read: boolean;
  dismissed: boolean;
  collected_at: string;
}

export interface IntelAlerts {
  critical_count: number;
  high_count: number;
}

export interface IntelImprovement {
  id: number;
  title: string;
  rationale: string;
  complexity: 'simple' | 'medium' | 'complex';
  setlist_prompt: string;
  affected_files: string[] | null;
  source_intel_id: number | null;
  status: 'pending' | 'planned' | 'built' | 'archived';
  build_spec_name: string | null;
  overlap_action: 'adopt' | 'adapt' | 'ignore' | null;
  overlap_notes: string | null;
  created_at: string;
}

export interface IntelFilters {
  source_type?: string;
  category?: string;
  priority?: string;
  days?: number;
  read?: boolean;
  limit?: number;
}

// --- Deals Tab Types ---

export interface DealItem {
  id: number;
  hunt_id: number;
  name: string;
  category: string;
  attributes: Record<string, any>;
  source_url: string;
  price: number;
  condition: string;
  seller: string;
  seller_rating: number;
  deal_score: number;
  verdict: 'exceptional' | 'good' | 'fair' | 'pass';
  opus_assessment: string | null;
  listing_url: string;
  collected_at: string;
  read: boolean;
  dismissed: boolean;
  in_stock: boolean | null;
  seller_verified: boolean | null;
  last_checked: string | null;
}

export interface Hunt {
  id: number;
  name: string;
  category: string;
  keywords: string;
  target_price: number;
  check_interval_minutes: number;
  source_urls: string[];
  active: boolean;
  created_at: string;
  items_count?: number;
  last_checked?: string;
}

export interface PriceHistoryPoint {
  price: number;
  source: string;
  recorded_at: string;
}

export interface DealFilters {
  hunt_id?: number;
  min_score?: number;
  limit?: number;
  ready_only?: boolean;
  in_stock_only?: boolean;
  seller_verified_only?: boolean;
}
