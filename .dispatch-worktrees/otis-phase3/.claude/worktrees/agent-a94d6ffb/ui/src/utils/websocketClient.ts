type MessageType = 'connection' | 'component_update' | 'feature_update' | 'checkpoint_update' | 'terminal_output' | 'build_progress' | 'file_change' | 'error';

interface WSMessage {
  type: MessageType;
  [key: string]: any;
}

type MessageHandler<T = WSMessage> = (data: T) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private readonly maxReconnectAttempts = 10;
  private readonly backoffDelays = [1000, 2000, 4000, 8000, 16000];
  private reconnectTimeout: number | null = null;
  private pingInterval: number | null = null;
  private sessionId: string | null = null;
  private handlers: Map<MessageType, Set<MessageHandler>> = new Map();
  private url: string = '';

  constructor() {
    const types: MessageType[] = ['connection', 'component_update', 'feature_update', 'checkpoint_update', 'terminal_output', 'build_progress', 'file_change', 'error'];
    types.forEach((type) => this.handlers.set(type, new Set()));
  }

  connect(sessionId: string): void {
    this.sessionId = sessionId;
    this.url = `ws://localhost:8080/api/build/stream/${sessionId}`;

    this.ws = new WebSocket(this.url);

    this.ws.onopen = () => {
      console.log('[WebSocket] Connected');
      this.reconnectAttempts = 0;
      this.startPingInterval();
      this.emit('connection', { status: 'connected' });
    };

    this.ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        this.handleMessage(message);
      } catch (error) {
        console.error('[WebSocket] Parse error:', error);
      }
    };

    this.ws.onerror = (error) => {
      console.error('[WebSocket] Error:', error);
    };

    this.ws.onclose = () => {
      console.log('[WebSocket] Disconnected');
      this.stopPingInterval();
      this.handleReconnect();
    };
  }

  private handleMessage(message: WSMessage): void {
    const handlers = this.handlers.get(message.type);
    if (handlers) handlers.forEach((handler) => handler(message));
  }

  private handleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      this.emit('error', { message: 'Max reconnect attempts reached' });
      return;
    }

    const delayIndex = Math.min(this.reconnectAttempts, this.backoffDelays.length - 1);
    const delay = this.backoffDelays[delayIndex];

    this.emit('connection', { status: 'reconnecting', attempt: this.reconnectAttempts + 1 });

    this.reconnectTimeout = window.setTimeout(() => {
      this.reconnectAttempts++;
      if (this.sessionId) this.connect(this.sessionId);
    }, delay);
  }

  private startPingInterval(): void {
    this.pingInterval = window.setInterval(() => {
      if (this.isConnected()) this.send({ type: 'ping' });
    }, 30000);
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  send(message: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(message));
    }
  }

  on<T extends MessageType>(type: T, handler: MessageHandler<any>): void {
    this.handlers.get(type)?.add(handler);
  }

  off<T extends MessageType>(type: T, handler: MessageHandler<any>): void {
    this.handlers.get(type)?.delete(handler);
  }

  private emit(type: MessageType, data: any): void {
    const handlers = this.handlers.get(type);
    if (handlers) handlers.forEach((handler) => handler({ type, ...data }));
  }

  disconnect(): void {
    if (this.reconnectTimeout) clearTimeout(this.reconnectTimeout);
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.sessionId = null;
    this.reconnectAttempts = 0;
  }

  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }
}
