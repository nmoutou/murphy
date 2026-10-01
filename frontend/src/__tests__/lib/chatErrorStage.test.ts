import { describe, expect, it } from 'vitest';
import { CHAT_ERROR_STAGES, serializeChatError } from '@murphy/contract/errors';
import { CONNECTION_ERROR_MESSAGE, readErrorStage } from '@/lib/chatErrorStage';

describe('readErrorStage', () => {
  it('names the connection when the socket failed or dropped the answer', () => {
    expect(readErrorStage(new Error(CONNECTION_ERROR_MESSAGE))).toBe('connection');
  });

  it.each(CHAT_ERROR_STAGES)('reads the %s stage the backend names', (stage) => {
    const errorText = serializeChatError({ stage, code: 'TIMEOUT' });

    expect(readErrorStage(new Error(errorText))).toBe(stage);
  });

  it.each([
    ['text that is not JSON', 'Invalid input'],
    ['JSON without a stage', '{"code":"TIMEOUT"}'],
    ['an unknown stage', '{"stage":"reranking","code":"TIMEOUT"}'],
  ])('falls back to internal on %s', (_case, message) => {
    expect(readErrorStage(new Error(message))).toBe('internal');
  });
});
