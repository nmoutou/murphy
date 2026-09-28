/**
 * Chat Request Validation Tests
 * `parseChatRequest`, the boundary check shared by the HTTP and WebSocket transports
 */

import { parseChatRequest } from '../../validation/chatRequest';

const QUESTION = 'Quel délai de prescription ?';
const USER_MESSAGE = { id: 'user-1', role: 'user', parts: [{ type: 'text', text: QUESTION }] };
const PASSAGE = { chunkId: 'c-1', identifier: 'LEGIARTI000006419280', highlightStart: 0, highlightEnd: 12, score: 0.8 };
const PARENT = { identifier: 'LEGIARTI000006419280', title: 'Article 2224', content: 'Les actions…' };

const ASSISTANT_MESSAGE = {
  id: 'assistant-1',
  role: 'assistant',
  metadata: { ragTiming: { embeddingMs: 4, retrievalMs: 6, totalMs: 900 } },
  parts: [
    { type: 'step-start' },
    { type: 'data-parentDocument', data: PARENT },
    { type: 'data-document', data: PASSAGE },
    { type: 'text', text: 'Cinq ans.', state: 'done' },
  ],
};

const rejectedFields = async (body: unknown): Promise<string[]> => {
  const request = await parseChatRequest(body);
  return request.isValid ? [] : request.issues.map((issue) => issue.field);
};

describe('parseChatRequest', () => {
  it('accepts a well-formed request and returns its messages', async () => {
    const body = { messages: [USER_MESSAGE] };

    expect(await parseChatRequest(body)).toEqual({ isValid: true, messages: body.messages });
  });

  it('accepts a follow-up question, with the previous answer and its sources', async () => {
    const body = { messages: [USER_MESSAGE, ASSISTANT_MESSAGE, { ...USER_MESSAGE, id: 'user-2' }] };

    expect(await parseChatRequest(body)).toEqual({ isValid: true, messages: body.messages });
  });

  it.each([
    ['a non-object body', QUESTION],
    ['a missing message list', {}],
    ['a message list that is not an array', { messages: QUESTION }],
    ['an empty message list', { messages: [] }],
  ])('rejects %s', async (_case, body) => {
    expect(await rejectedFields(body)).toEqual(['messages']);
  });

  it.each([
    ['an unknown role', { ...USER_MESSAGE, role: 'robot' }, 'messages[0].role'],
    ['a message without id', { role: 'user', parts: USER_MESSAGE.parts }, 'messages[0].id'],
    ['missing parts', { id: 'user-1', role: 'user', content: QUESTION }, 'messages[0].parts'],
    ['a null part', { ...USER_MESSAGE, parts: [null] }, 'messages[0].parts[0]'],
    ['a part without type', { ...USER_MESSAGE, parts: [{ text: QUESTION }] }, 'messages[0].parts[0]'],
  ])('rejects %s', async (_case, message, field) => {
    expect(await rejectedFields({ messages: [message] })).toEqual([field]);
  });

  it.each([
    [
      'a passage whose score is not a number',
      { type: 'data-document', data: { ...PASSAGE, score: 'haut' } },
      'messages[1].parts[0].data.score',
    ],
    ['a data part the contract does not declare', { type: 'data-inconnue', data: {} }, 'messages[1].parts[0].data'],
  ])('rejects %s', async (_case, part, field) => {
    const answer = { ...ASSISTANT_MESSAGE, parts: [part] };

    expect(await rejectedFields({ messages: [USER_MESSAGE, answer] })).toEqual([field]);
  });

  it('rejects malformed timing metadata', async () => {
    const answer = { ...ASSISTANT_MESSAGE, metadata: { ragTiming: { embeddingMs: 'vite', retrievalMs: 6, totalMs: 9 } } };

    expect(await rejectedFields({ messages: [USER_MESSAGE, answer] })).toEqual([
      'messages[1].metadata.ragTiming.embeddingMs',
    ]);
  });

  it('never echoes the received conversation in its issues', async () => {
    const request = await parseChatRequest({ messages: [USER_MESSAGE, { ...USER_MESSAGE, role: 'robot' }] });

    expect(JSON.stringify(request)).not.toContain(QUESTION);
  });
});
