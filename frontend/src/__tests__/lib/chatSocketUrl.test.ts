/**
 * Chat Socket URL Tests
 * The WebSocket address derived from `NEXT_PUBLIC_API_URL`
 */

import { describe, expect, it, vi } from 'vitest';
import { getChatSocketUrl } from '@/lib/chatSocketUrl';

describe('getChatSocketUrl', () => {
  it.each([
    ['http://backend:5000', 'ws://backend:5000/api/v1/chat/ws'],
    ['https://murphy.example', 'wss://murphy.example/api/v1/chat/ws'],
    ['', 'ws://localhost:5000/api/v1/chat/ws'],
  ])('derives the socket of %j', (backendUrl, socketUrl) => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', backendUrl);

    expect(getChatSocketUrl()).toBe(socketUrl);
  });

  it('names the malformed value it could not read', () => {
    vi.stubEnv('NEXT_PUBLIC_API_URL', 'backend sans schéma');

    expect(getChatSocketUrl).toThrow('"backend sans schéma"');
  });
});
