import { vi } from 'vitest';

/**
 * Socket de chat pilotée par le test, qui joue le backend. Comme une vraie, elle émet
 * `close` une seule fois ; contrairement à une vraie, elle livre encore des parts après,
 * pour tester les gardes du client.
 */
export class FakeWebSocket {
  readonly sent: string[] = [];
  /** Fermée par le client */
  readonly close = vi.fn(() => this.drop());
  private isClosed = false;
  onopen: (() => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onerror: (() => void) | null = null;
  onclose: (() => void) | null = null;

  constructor(readonly url: string) {}

  send(data: string): void {
    this.sent.push(data);
  }

  open(): void {
    this.onopen?.();
  }

  receive(part: unknown): void {
    this.receiveRaw(JSON.stringify(part));
  }

  receiveRaw(data: string): void {
    this.onmessage?.(new MessageEvent('message', { data }));
  }

  fail(): void {
    this.onerror?.();
  }

  /** Fermée par le backend */
  drop(): void {
    if (this.isClosed) return;
    this.isClosed = true;
    this.onclose?.();
  }
}

/** Remplace le `WebSocket` global ; la liste rendue se remplit à chaque socket ouverte */
export const stubWebSocket = (): FakeWebSocket[] => {
  const sockets: FakeWebSocket[] = [];
  class TrackedWebSocket extends FakeWebSocket {
    constructor(url: string) {
      super(url);
      sockets.push(this);
    }
  }
  vi.stubGlobal('WebSocket', TrackedWebSocket);
  return sockets;
};
