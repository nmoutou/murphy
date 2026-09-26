/**
 * Chat Routes Tests
 * HTTP transports (SSE and drained JSON) over a mocked pipeline
 */

import express, { Express } from 'express';
import request from 'supertest';
import type { InferUIMessageChunk } from 'ai';
import chatRouter from '../../routes/chat';
import { createChatStream } from '../../services/chatService';
import type { AppUIMessage } from '@murphy/contract/messages';
import { serializeChatError } from '@murphy/contract/errors';
import { RagError } from '../../types/rag';

jest.mock('../../services/chatService', () => ({ createChatStream: jest.fn() }));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

type AppChunk = InferUIMessageChunk<AppUIMessage>;

const MESSAGE_ID = 'message-1';
const VALID_BODY = { messages: [{ id: 'user-1', role: 'user', parts: [{ type: 'text', text: 'Quel délai ?' }] }] };

const streamOf = (parts: AppChunk[]): ReadableStream<AppChunk> =>
  new ReadableStream<AppChunk>({
    start(controller) {
      parts.forEach((part) => controller.enqueue(part));
      controller.close();
    },
  });

const ANSWER_PARTS: AppChunk[] = [
  { type: 'start', messageId: MESSAGE_ID },
  { type: 'text-start', id: MESSAGE_ID },
  {
    type: 'data-document',
    data: { chunkId: 'chunk-1', identifier: 'LEGIARTI1', highlightStart: 0, highlightEnd: 4, score: 0.9 },
  },
  { type: 'text-delta', id: MESSAGE_ID, delta: 'Cinq ' },
  { type: 'text-delta', id: MESSAGE_ID, delta: 'ans.' },
  { type: 'text-end', id: MESSAGE_ID },
  { type: 'finish', finishReason: 'stop' },
];

let app: Express;

beforeEach(() => {
  app = express();
  app.use(express.json());
  app.use('/api/v1/chat', chatRouter);
});

describe('request validation', () => {
  it.each([
    ['an empty message list', { messages: [] }],
    ['an unknown role', { messages: [{ id: 'm-1', role: 'robot', parts: [] }] }],
    ['a message without parts', { messages: [{ id: 'm-1', role: 'user', content: 'Quel délai ?' }] }],
    ['a null part', { messages: [{ id: 'm-1', role: 'user', parts: [null] }] }],
  ])('rejects %s with a 400', async (_case, body) => {
    const response = await request(app).post('/api/v1/chat/completions').send(body);

    expect(response.status).toBe(400);
    expect(response.body.status.message).toBe('VALIDATION_ERROR');
    expect(createChatStream).not.toHaveBeenCalled();
  });
});

describe('POST /api/v1/chat/completions', () => {
  it('drains the stream into the full answer text', async () => {
    jest.mocked(createChatStream).mockResolvedValue(streamOf(ANSWER_PARTS));

    const response = await request(app).post('/api/v1/chat/completions').send(VALID_BODY);

    expect(response.status).toBe(200);
    expect(response.body.data).toEqual({ role: 'assistant', parts: [{ type: 'text', text: 'Cinq ans.' }] });
    expect(createChatStream).toHaveBeenCalledWith(VALID_BODY.messages, expect.any(AbortSignal));
  });

  it('answers 500 with the stage and code when the stream carries an error part', async () => {
    const chatError = { stage: 'retrieval', code: 'SEARCH_FAILED' } as const;
    jest.mocked(createChatStream).mockResolvedValue(
      streamOf([{ type: 'start', messageId: MESSAGE_ID }, { type: 'error', errorText: serializeChatError(chatError) }]),
    );

    const response = await request(app).post('/api/v1/chat/completions').send(VALID_BODY);

    expect(response.status).toBe(500);
    expect(response.body.status.message).toBe('CHAT_STREAM_ERROR');
    expect(response.body.data).toEqual(chatError);
  });

  it('answers 500 when the pipeline cannot start', async () => {
    jest.mocked(createChatStream).mockRejectedValue(new RagError('request', 'NO_QUESTION', 'No question provided'));

    const response = await request(app).post('/api/v1/chat/completions').send(VALID_BODY);

    expect(response.status).toBe(500);
    expect(response.body.status.message).toBe('CHAT_STREAM_ERROR');
    expect(response.body.data).toEqual({ stage: 'request', code: 'NO_QUESTION' });
  });
});

describe('POST /api/v1/chat/streams', () => {
  it('streams the parts as server-sent events', async () => {
    jest.mocked(createChatStream).mockResolvedValue(streamOf(ANSWER_PARTS));

    const response = await request(app).post('/api/v1/chat/streams').send(VALID_BODY);

    expect(response.status).toBe(200);
    expect(response.headers['content-type']).toContain('text/event-stream');
    expect(response.text).toContain(
      'data: {"type":"data-document","data":{"chunkId":"chunk-1","identifier":"LEGIARTI1",' +
        '"highlightStart":0,"highlightEnd":4,"score":0.9}}',
    );
    expect(response.text).toContain('data: {"type":"text-delta","id":"message-1","delta":"ans."}');
    expect(createChatStream).toHaveBeenCalledWith(VALID_BODY.messages, expect.any(AbortSignal));
  });
});
