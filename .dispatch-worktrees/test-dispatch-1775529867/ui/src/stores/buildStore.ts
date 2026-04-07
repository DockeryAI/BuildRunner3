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

      setSession: (session) => set({ session }),

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
