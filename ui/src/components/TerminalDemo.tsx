/**
 * Terminal Demo Component
 * Example of integrating TerminalPanel with WebSocket updates
 */

import { useEffect } from 'react';
import { TerminalPanel } from './TerminalPanel';
import { useBuildStore } from '../stores/buildStore';
import { useWebSocket } from '../hooks/useWebSocket';

export function TerminalDemo() {
  const addTerminalLine = useBuildStore((state) => state.addTerminalLine);
  const setWebSocketConnected = useBuildStore((state) => state.setWebSocketConnected);
  const setWebSocketError = useBuildStore((state) => state.setWebSocketError);

  // WebSocket integration
  const { isConnected, lastMessage } = useWebSocket({
    onConnect: () => {
      setWebSocketConnected(true);
      addTerminalLine({
        timestamp: Date.now(),
        type: 'success',
        content: 'Connected to BuildRunner WebSocket',
      });
    },
    onDisconnect: () => {
      setWebSocketConnected(false);
      addTerminalLine({
        timestamp: Date.now(),
        type: 'error',
        content: 'Disconnected from BuildRunner WebSocket',
      });
    },
    onError: (error) => {
      setWebSocketError('WebSocket connection error');
      addTerminalLine({
        timestamp: Date.now(),
        type: 'error',
        content: `WebSocket error: ${error}`,
      });
    },
  });

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    // Example: Convert WebSocket messages to terminal lines
    switch (lastMessage.type) {
      case 'task_update':
        addTerminalLine({
          timestamp: Date.now(),
          type: 'info',
          content: `Task update: ${JSON.stringify(lastMessage)}`,
        });
        break;

      case 'telemetry_event':
        if (lastMessage.event_type === 'command_executed') {
          addTerminalLine({
            timestamp: Date.now(),
            type: 'stdout',
            content: lastMessage.metadata?.output || 'Command executed',
          });
        }
        break;

      case 'error':
        addTerminalLine({
          timestamp: Date.now(),
          type: 'error',
          content: lastMessage.message || 'Unknown error',
        });
        break;

      default:
        // Log other message types as info
        addTerminalLine({
          timestamp: Date.now(),
          type: 'info',
          content: `[${lastMessage.type}] ${JSON.stringify(lastMessage).substring(0, 100)}`,
        });
    }
  }, [lastMessage, addTerminalLine]);

  return (
    <div style={{ padding: '20px' }}>
      <h2>BuildRunner Terminal</h2>
      <p>Connection status: {isConnected ? '🟢 Connected' : '🔴 Disconnected'}</p>
      <TerminalPanel height="500px" />
    </div>
  );
}

export default TerminalDemo;
