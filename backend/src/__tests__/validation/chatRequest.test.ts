/**
 * Chat Request Validation Tests
 * `parseChatRequest`, the boundary check shared by the HTTP and WebSocket transports
 */

import { parseChatRequest } from '../../validation/chatRequest';

const USER_MESSAGE = { id: 'user-1', role: 'user', parts: [{ type: 'text', text: 'Quel délai ?' }] };

describe('parseChatRequest', () => {
  it('accepts a well-formed request and returns its messages', () => {
    const body = { messages: [USER_MESSAGE] };

    expect(parseChatRequest(body)).toEqual({ isValid: true, messages: body.messages });
  });

  it.each([
    ['a non-object body', 'Quel délai ?'],
    ['a missing message list', {}],
    ['an empty message list', { messages: [] }],
  ])('rejects %s', (_case, body) => {
    expect(parseChatRequest(body)).toEqual({
      isValid: false,
      issues: [{ field: 'messages', message: 'messages must be a non-empty array' }],
    });
  });

  it.each([
    ['an unknown role', { ...USER_MESSAGE, role: 'robot' }, 'messages[0].role'],
    ['missing parts', { id: 'user-1', role: 'user', content: 'Quel délai ?' }, 'messages[0].parts'],
    ['a null part', { ...USER_MESSAGE, parts: [null] }, 'messages[0].parts'],
    ['a part without type', { ...USER_MESSAGE, parts: [{ text: 'Quel délai ?' }] }, 'messages[0].parts'],
  ])('rejects %s', (_case, message, field) => {
    const request = parseChatRequest({ messages: [message] });

    expect(request.isValid).toBe(false);
    expect(request.isValid ? [] : request.issues.map((issue) => issue.field)).toEqual([field]);
  });

  it('reports every issue with the index of its message', () => {
    const request = parseChatRequest({ messages: [USER_MESSAGE, null] });

    expect(request.isValid ? [] : request.issues.map((issue) => issue.field)).toEqual([
      'messages[1].role',
      'messages[1].parts',
    ]);
  });
});
