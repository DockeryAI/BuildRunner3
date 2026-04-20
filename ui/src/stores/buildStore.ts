import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type ComponentStatus = 'not_started' | 'in_progress' | 'completed' | 'error' | 'blocked';

export interface Component {
  id: string;
  name: string;
  type: 'frontend' | 'backend' | 'database' | 'service' | 'api';
  status: ComponentStatus;
  progress: number;
  dependencies: string[];
  files: string[];
  testsPass: boolean;
  startTime?: number;
  endTime?: number;
  error?: string;
}

export interface Feature {
  id: string;
  name: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  component: string;
  status: ComponentStatus;
  progress: number;
  tasks: Task[];
  estimatedTime: number;
  actualTime?: number;
}

export interface Task {
  id: string;
  name: string;
  completed: boolean;
  timestamp?: number;
}

export interface BuildSession {
  id: string;
  projectName: string;
  projectAlias: string;
  projectPath: string;
  startTime: number;
  endTime?: number;
  status: 'initializing' | 'running' | 'paused' | 'completed' | 'error';
  components: Component[];
  features: Feature[];
  currentComponent?: string;
  currentFeature?: string;
  runtime: string;
  backend?: string;
  runtimeSource?: string;
  runtimeSessionId?: string;
  capabilities?: Record<string, unknown>;
  dispatchMode?: string;
  shadowRuntime?: string;
  shadowStatus?: string;
}

type BuildSessionPayload = Partial<BuildSession> | Record<string, unknown>;

function asRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null ? (value as Record<string, unknown>) : {};
}

function asPlainObject(value: unknown): Record<string, unknown> | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }
  return value as Record<string, unknown>;
}

export function normalizeBuildSession(payload: BuildSessionPayload): Partial<BuildSession> {
  const raw = asRecord(payload);
  const session = payload as Partial<BuildSession>;
  const capabilities =
    asPlainObject(raw.capabilities) ??
    asPlainObject(raw.runtime_capabilities) ??
    asPlainObject(session.capabilities);
  const normalized: Partial<BuildSession> = {
    ...session,
    id: (raw.id as string | undefined) ?? session.id,
    projectName: (raw.projectName as string | undefined) ?? (raw.project_name as string | undefined) ?? session.projectName,
    projectAlias: (raw.projectAlias as string | undefined) ?? (raw.project_alias as string | undefined) ?? session.projectAlias,
    projectPath: (raw.projectPath as string | undefined) ?? (raw.project_path as string | undefined) ?? session.projectPath,
    startTime: (raw.startTime as number | undefined) ?? (raw.start_time as number | undefined) ?? session.startTime,
    endTime: (raw.endTime as number | undefined) ?? (raw.end_time as number | undefined) ?? session.endTime,
    currentComponent:
      (raw.currentComponent as string | undefined) ??
      (raw.current_component as string | undefined) ??
      session.currentComponent,
    currentFeature:
      (raw.currentFeature as string | undefined) ??
      (raw.current_feature as string | undefined) ??
      session.currentFeature,
    runtime: (raw.runtime as string | undefined) ?? session.runtime,
    backend: (raw.backend as string | undefined) ?? session.backend,
    runtimeSource:
      (raw.runtimeSource as string | undefined) ??
      (raw.runtime_source as string | undefined) ??
      session.runtimeSource,
    runtimeSessionId:
      (raw.runtimeSessionId as string | undefined) ??
      (raw.runtime_session_id as string | undefined) ??
      session.runtimeSessionId,
    capabilities,
    dispatchMode:
      (raw.dispatchMode as string | undefined) ??
      (raw.dispatch_mode as string | undefined) ??
      session.dispatchMode,
    shadowRuntime:
      (raw.shadowRuntime as string | undefined) ??
      (raw.shadow_runtime as string | undefined) ??
      session.shadowRuntime,
    shadowStatus:
      (raw.shadowStatus as string | undefined) ??
      (raw.shadow_status as string | undefined) ??
      session.shadowStatus,
    components: (raw.components as Component[] | undefined) ?? session.components,
    features: (raw.features as Feature[] | undefined) ?? session.features,
    status: (raw.status as BuildSession['status'] | undefined) ?? session.status,
  };
  return Object.fromEntries(
    Object.entries(normalized).filter(([, value]) => value !== undefined)
  ) as Partial<BuildSession>;
}

export interface TerminalLine {
  id: string;
  timestamp: number;
  type: 'stdout' | 'stderr' | 'info' | 'error' | 'success';
  content: string;
}

interface BuildStore {
  session: BuildSession | null;
  terminalLines: TerminalLine[];
  websocket: {
    connected: boolean;
    reconnecting: boolean;
    error: string | null;
  };

  setSession: (session: BuildSession) => void;
  patchSession: (session: Partial<BuildSession> | BuildSessionPayload) => void;
  updateComponent: (componentId: string, updates: Partial<Component>) => void;
  updateFeature: (featureId: string, updates: Partial<Feature>) => void;
  addTerminalLine: (line: TerminalLine) => void;
  clearTerminalLines: () => void;
  setWebSocketState: (state: Partial<BuildStore['websocket']>) => void;
  resetStore: () => void;
}

const MAX_TERMINAL_LINES = 1000;

export const useBuildStore = create<BuildStore>()(
  persist(
    (set) => ({
      session: null,
      terminalLines: [],
      websocket: { connected: false, reconnecting: false, error: null },

      setSession: (session) => set({ session: normalizeBuildSession(session) as BuildSession }),

      patchSession: (session) =>
        set((state) => {
          if (!state.session) {
            return { session: normalizeBuildSession(session) as BuildSession };
          }
          return {
            session: {
              ...state.session,
              ...normalizeBuildSession(session),
            },
          };
        }),

      updateComponent: (componentId, updates) =>
        set((state) => {
          if (!state.session) return state;
          const components = state.session.components.map((comp) =>
            comp.id === componentId ? { ...comp, ...updates } : comp
          );
          return { session: { ...state.session, components } };
        }),

      updateFeature: (featureId, updates) =>
        set((state) => {
          if (!state.session) return state;
          const features = state.session.features.map((feat) =>
            feat.id === featureId ? { ...feat, ...updates } : feat
          );
          return { session: { ...state.session, features } };
        }),

      addTerminalLine: (line) =>
        set((state) => {
          const updatedLines = [...state.terminalLines, line];
          if (updatedLines.length > MAX_TERMINAL_LINES) updatedLines.shift();
          return { terminalLines: updatedLines };
        }),

      clearTerminalLines: () => set({ terminalLines: [] }),

      setWebSocketState: (wsState) =>
        set((state) => ({ websocket: { ...state.websocket, ...wsState } })),

      resetStore: () =>
        set({
          session: null,
          terminalLines: [],
          websocket: { connected: false, reconnecting: false, error: null },
        }),
    }),
    {
      name: 'build-monitor-storage',
      partialize: (state) => ({
        session: state.session,
        terminalLines: state.terminalLines.slice(-100),
      }),
    }
  )
);
