import { vi } from 'vitest';

/**
 * A chat socket driven by the test, which plays the backend: it opens, sends parts,
 * fails or drops when told to. Like a real socket, it fires `close` once, whichever side
 * closes; unlike one, it still delivers parts afterwards, to test the client's guards.
 */
export class FakeWebSocket {
  readonly sent: string[] = [];
  /** Closed by the client */
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

  /** Closed by the backend */
  drop(): void {
    if (this.isClosed) return;
    this.isClosed = true;
    this.onclose?.();
  }
}

/** Replaces the global `WebSocket`; the returned list fills as the code opens sockets */
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
