/**
 * PRD Store - Frontend state management for PRD system
 *
 * Features:
 * - Zustand state management
 * - WebSocket subscriptions for real-time updates
 * - Optimistic updates with rollback
 * - Multi-client consistency
 * - Version history management
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8080';
const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080';

export interface PRDFeature {
  id: string;
  name: string;
  description: string;
  priority: string;
  status: string;
  requirements: string[];
  acceptance_criteria: string[];
  technical_details: Record<string, any>;
  dependencies: string[];
}

export interface PRD {
  project_name: string;
  version: string;
  overview: string;
  features: PRDFeature[];
  architecture: Record<string, any>;
  metadata: Record<string, any>;
  last_updated: string;
}

export interface PRDVersion {
  index: number;
  timestamp: string;
  author: string;
  summary: string;
  feature_count: number;
}

export interface PRDUpdate {
  updates: Record<string, any>;
  author?: string;
}

interface PRDState {
  // State
  prd: PRD | null;
  versions: PRDVersion[];
  isLoading: boolean;
  isSaving: boolean;
  isRegenerating: boolean;
  error: string | null;
  wsConnected: boolean;
  ws: WebSocket | null;

  // Optimistic update tracking
  pendingUpdates: Map<string, PRDUpdate>;
  updateSequence: number;

  // Actions
  loadPRD: () => Promise<void>;
  updatePRD: (updates: Record<string, any>, author?: string) => Promise<void>;
  parseNaturalLanguage: (text: string) => Promise<{success: boolean; updates: Record<string, any>; preview: string}>;
  loadVersions: () => Promise<void>;
  rollbackToVersion: (versionIndex: number) => Promise<void>;
  connectWebSocket: () => void;
  disconnectWebSocket: () => void;
  clearError: () => void;

  // Internal
  _handleWSMessage: (event: MessageEvent) => void;
  _applyOptimisticUpdate: (updateId: string, updates: Record<string, any>) => void;
  _rollbackOptimisticUpdate: (updateId: string) => void;
  _confirmOptimisticUpdate: (updateId: string) => void;
}

export const usePRDStore = create<PRDState>()(
  devtools(
    (set, get) => ({
      // Initial state
      prd: null,
      versions: [],
      isLoading: false,
      isSaving: false,
      isRegenerating: false,
      error: null,
      wsConnected: false,
      ws: null,
      pendingUpdates: new Map(),
      updateSequence: 0,

      // Load current PRD
      loadPRD: async () => {
        set({ isLoading: true, error: null });

        try {
          const response = await fetch(`${API_URL}/api/prd/current`);
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const data = await response.json();
          set({ prd: data, isLoading: false });

          // Connect WebSocket after initial load
          if (!get().wsConnected) {
            get().connectWebSocket();
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to load PRD',
            isLoading: false
          });
        }
      },

      // Update PRD with optimistic updates
      updatePRD: async (updates: Record<string, any>, author: string = 'user') => {
        const updateId = `update-${get().updateSequence}`;
        set({ updateSequence: get().updateSequence + 1, isSaving: true, error: null });

        // Apply optimistic update
        get()._applyOptimisticUpdate(updateId, updates);

        try {
          const response = await fetch(`${API_URL}/api/prd/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ updates, author })
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const result = await response.json();

          // Confirm optimistic update
          get()._confirmOptimisticUpdate(updateId);
          set({ isSaving: false, isRegenerating: true });

          // Regeneration happens automatically via PRD controller
          // Wait a bit then clear regenerating flag
          setTimeout(() => {
            set({ isRegenerating: false });
          }, 3000);

        } catch (error) {
          // Rollback optimistic update
          get()._rollbackOptimisticUpdate(updateId);
          set({
            error: error instanceof Error ? error.message : 'Failed to update PRD',
            isSaving: false
          });
        }
      },

      // Parse natural language input
      parseNaturalLanguage: async (text: string) => {
        try {
          const response = await fetch(`${API_URL}/api/prd/parse-nl`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text })
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          return await response.json();
        } catch (error) {
          return {
            success: false,
            updates: {},
            preview: error instanceof Error ? error.message : 'Parse failed'
          };
        }
      },

      // Load version history
      loadVersions: async () => {
        try {
          const response = await fetch(`${API_URL}/api/prd/versions`);
          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          const data = await response.json();
          set({ versions: data.versions });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to load versions'
          });
        }
      },

      // Rollback to previous version
      rollbackToVersion: async (versionIndex: number) => {
        set({ isSaving: true, error: null });

        try {
          const response = await fetch(`${API_URL}/api/prd/rollback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ version_index: versionIndex })
          });

          if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
          }

          // Reload PRD after rollback
          await get().loadPRD();
          await get().loadVersions();

          set({ isSaving: false });
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : 'Failed to rollback',
            isSaving: false
          });
        }
      },

      // Connect WebSocket for real-time updates
      connectWebSocket: () => {
        if (get().ws?.readyState === WebSocket.OPEN) {
          return; // Already connected
        }

        try {
          const ws = new WebSocket(`${WS_URL}/api/prd/stream`);

          ws.onopen = () => {
            console.log('PRD WebSocket connected');
            set({ wsConnected: true, ws });
          };

          ws.onmessage = (event) => {
            get()._handleWSMessage(event);
          };

          ws.onerror = (error) => {
            console.error('PRD WebSocket error:', error);
            set({ wsConnected: false });
          };

          ws.onclose = () => {
            console.log('PRD WebSocket closed');
            set({ wsConnected: false, ws: null });

            // Attempt reconnection after 3 seconds
            setTimeout(() => {
              if (!get().wsConnected) {
                console.log('Attempting PRD WebSocket reconnection...');
                get().connectWebSocket();
              }
            }, 3000);
          };

          // Keep connection alive with ping/pong
          const pingInterval = setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send('ping');
            } else {
              clearInterval(pingInterval);
            }
          }, 30000); // Ping every 30 seconds

        } catch (error) {
          console.error('Failed to connect PRD WebSocket:', error);
          set({ wsConnected: false });
        }
      },

      // Disconnect WebSocket
      disconnectWebSocket: () => {
        const ws = get().ws;
        if (ws) {
          ws.close();
          set({ wsConnected: false, ws: null });
        }
      },

      // Clear error message
      clearError: () => {
        set({ error: null });
      },

      // Handle WebSocket messages
      _handleWSMessage: (event: MessageEvent) => {
        try {
          const message = JSON.parse(event.data);

          if (message.type === 'initial') {
            // Initial PRD state from server
            set({ prd: message.prd });
          } else if (message.type === 'prd_updated') {
            // PRD was updated (by another client or file edit)
            const currentPRD = get().prd;

            // Only update if we don't have pending updates
            // (to avoid conflicts with optimistic updates)
            if (get().pendingUpdates.size === 0) {
              set({
                prd: message.prd,
                isRegenerating: true
              });

              // Clear regenerating flag after delay
              setTimeout(() => {
                set({ isRegenerating: false });
              }, 1000);
            }
          }
        } catch (error) {
          console.error('Error handling WebSocket message:', error);
        }
      },

      // Apply optimistic update to local state
      _applyOptimisticUpdate: (updateId: string, updates: Record<string, any>) => {
        const currentPRD = get().prd;
        if (!currentPRD) return;

        // Store original state for rollback
        get().pendingUpdates.set(updateId, { updates });

        // Apply update to local state
        const newPRD = { ...currentPRD };

        if (updates.add_feature) {
          newPRD.features = [...newPRD.features, updates.add_feature as PRDFeature];
        }

        if (updates.remove_feature) {
          newPRD.features = newPRD.features.filter(
            f => f.id !== updates.remove_feature
          );
        }

        if (updates.update_feature) {
          const { id, updates: featureUpdates } = updates.update_feature;
          newPRD.features = newPRD.features.map(f =>
            f.id === id ? { ...f, ...featureUpdates } : f
          );
        }

        // Update metadata fields
        for (const key of ['project_name', 'version', 'overview', 'metadata']) {
          if (key in updates) {
            (newPRD as any)[key] = updates[key];
          }
        }

        newPRD.last_updated = new Date().toISOString();

        set({ prd: newPRD });
      },

      // Rollback optimistic update
      _rollbackOptimisticUpdate: (updateId: string) => {
        get().pendingUpdates.delete(updateId);

        // Reload PRD from server to get correct state
        get().loadPRD();
      },

      // Confirm optimistic update (server accepted it)
      _confirmOptimisticUpdate: (updateId: string) => {
        get().pendingUpdates.delete(updateId);

        // Optimistic update was successful, server state will come via WebSocket
      },
    }),
    {
      name: 'prd-store',
      enabled: process.env.NODE_ENV === 'development'
    }
  )
);

// Export hook for easier access
export default usePRDStore;
