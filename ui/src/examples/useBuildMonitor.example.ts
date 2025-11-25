/**
 * Example: Using the Build Monitor State Management
 *
 * This example shows how to use the buildStore and WebSocket client together
 * to create a real-time build monitoring system.
 */

import { useEffect } from 'react';
import { useBuildStore } from '../stores/buildStore';
import { WebSocketClient } from '../utils/websocketClient';
import { parseArchitecture } from '../utils/architectureParser';
import type { BuildSession } from '../types/build';

// Initialize WebSocket client (singleton)
const wsClient = new WebSocketClient({
  onConnect: () => {
    console.log('WebSocket connected');
  },
  onDisconnect: () => {
    console.log('WebSocket disconnected');
  },
  onError: (error) => {
    console.error('WebSocket error:', error);
  },
  reconnectInterval: 3000,
  maxReconnectAttempts: 5,
});

/**
 * Example Hook: useBasicBuildMonitor
 */
export function useBasicBuildMonitor(sessionId: string) {
  const {
    session,
    terminalLines,
    websocket,
    setSession,
    updateComponent,
    updateFeature,
    addTerminalLine,
    setWebSocketConnected,
    setWebSocketReconnecting,
    setWebSocketError,
  } = useBuildStore();

  useEffect(() => {
    // Configure WebSocket message handler
    wsClient.options.onMessage = (message) => {
      switch (message.type) {
        case 'component_update':
          updateComponent(message.componentId, message.updates);
          break;

        case 'feature_update':
          updateFeature(message.featureId, message.updates);
          break;

        case 'terminal_output':
          addTerminalLine(message.line);
          break;

        case 'session_status':
          // Update session status
          if (session) {
            setSession({
              ...session,
              status: message.status,
            });
          }
          break;

        case 'error':
          setWebSocketError(message.message);
          break;
      }
    };

    // Configure connection handlers
    wsClient.options.onConnect = () => setWebSocketConnected(true);
    wsClient.options.onDisconnect = () => setWebSocketConnected(false);
    wsClient.options.onReconnecting = () => setWebSocketReconnecting(true);
    wsClient.options.onError = (error) => setWebSocketError(error.type);

    // Connect to WebSocket
    wsClient.connect(sessionId);

    // Cleanup on unmount
    return () => {
      wsClient.disconnect();
    };
  }, [sessionId]);

  return {
    session,
    terminalLines,
    websocket,
    isConnected: wsClient.isConnected(),
  };
}

/**
 * Example Hook: useArchitectureParser
 */
export function useArchitectureParser(prdContent: string) {
  const { setComponents } = useBuildStore();

  useEffect(() => {
    if (prdContent) {
      const components = parseArchitecture({ content: prdContent });
      setComponents(components);
    }
  }, [prdContent, setComponents]);
}

/**
 * Example: Initialize Build Session
 */
export function initializeBuildSession(prdContent: string): BuildSession {
  const components = parseArchitecture({ content: prdContent });

  const session: BuildSession = {
    id: `session-${Date.now()}`,
    projectName: 'My Project',
    projectAlias: 'my-project',
    projectPath: '/path/to/project',
    startTime: Date.now(),
    status: 'initializing',
    components,
    features: [],
  };

  return session;
}

/**
 * Example: Full Build Monitor Setup
 */
export function useBuildMonitor(sessionId: string, prdContent?: string) {
  const store = useBuildStore();

  // Parse architecture if PRD content provided
  useEffect(() => {
    if (prdContent && !store.session) {
      const session = initializeBuildSession(prdContent);
      store.setSession(session);
    }
  }, [prdContent, store.session]);

  // Connect WebSocket
  useEffect(() => {
    if (sessionId) {
      wsClient.options.onMessage = (message) => {
        switch (message.type) {
          case 'component_update':
            store.updateComponent(message.componentId, message.updates);
            break;
          case 'feature_update':
            store.updateFeature(message.featureId, message.updates);
            break;
          case 'terminal_output':
            store.addTerminalLine(message.line);
            break;
          case 'session_status':
            if (store.session) {
              store.setSession({ ...store.session, status: message.status });
            }
            break;
          case 'error':
            store.setWebSocketError(message.message);
            break;
        }
      };

      wsClient.options.onConnect = () => store.setWebSocketConnected(true);
      wsClient.options.onDisconnect = () => store.setWebSocketConnected(false);
      wsClient.options.onReconnecting = () => store.setWebSocketReconnecting(true);

      wsClient.connect(sessionId);

      return () => wsClient.disconnect();
    }
  }, [sessionId]);

  return {
    ...store,
    isConnected: wsClient.isConnected(),
    reconnectAttempts: wsClient.getReconnectAttempts(),
  };
}
