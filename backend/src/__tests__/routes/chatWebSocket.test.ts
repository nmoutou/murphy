/**
 * Chat WebSocket Tests
 * A real WebSocket server on an ephemeral port, over a mocked pipeline and quota
 */

import http from 'http';
import { WebSocket, WebSocketServer } from 'ws';
import type { InferUIMessageChunk } from 'ai';
import { registerChatWebSocket } from '../../routes/chatWebSocket';
import { createChatStream } from '../../services/chatService';
import { consumeStreamQuota } from '../../middleware/streamRateLimiter';
import type { AppUIMessage } from '@murphy/contract/messages';
import type { ChatError } from '@murphy/contract/errors';
import { serializeChatError } from '@murphy/contract/errors';
import { RagError } from '../../types/rag';

jest.mock('../../services/chatService', () => ({ createChatStream: jest.fn() }));
jest.mock('../../middleware/streamRateLimiter', () => ({ consumeStreamQuota: jest.fn() }));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

type AppChunk = InferUIMessageChunk<AppUIMessage>;

const MESSAGE_ID = 'message-1';
const VALID_PAYLOAD = { messages: [{ id: 'user-1', role: 'user', parts: [{ type: 'text', text: 'Quel délai ?' }] }] };

const ANSWER_PARTS: AppChunk[] = [
  { type: 'start', messageId: MESSAGE_ID },
  {
    type: 'data-document',
    data: { chunkId: 'chunk-1', identifier: 'LEGIARTI1', highlightStart: 0, highlightEnd: 4, score: 0.9 },
  },
  { type: 'text-delta', id: MESSAGE_ID, delta: 'Cinq ans.' },
  { type: 'finish', finishReason: 'stop' },
];

const errorPart = (chatError: ChatError): AppChunk => ({ type: 'error', errorText: serializeChatError(chatError) });

const streamOf = (parts: AppChunk[]): ReadableStream<AppChunk> =>
  new ReadableStream<AppChunk>({
    start(controller) {
      parts.forEach((part) => controller.enqueue(part));
      controller.close();
    },
  });

let server: http.Server;
let serverUrl: string;

beforeAll(async () => {
  server = http.createServer();
  registerChatWebSocket(new WebSocketServer({ server }));
  await new Promise<void>((resolve) => server.listen(0, resolve));
  const address = server.address();
  if (address === null || typeof address === 'string') throw new Error('Expected the server to listen on a TCP port');
  serverUrl = `ws://127.0.0.1:${address.port}`;
});

afterAll(async () => {
  await new Promise<void>((resolve) => server.close(() => resolve()));
});

beforeEach(() => {
  jest.mocked(consumeStreamQuota).mockResolvedValue(true);
});

/** Sends one raw message and collects every part received until the server closes the socket */
const exchange = (rawPayload: string): Promise<unknown[]> =>
  new Promise((resolve, reject) => {
    const received: unknown[] = [];
    const client = new WebSocket(serverUrl);
    client.on('open', () => client.send(rawPayload));
    client.on('message', (raw) => received.push(JSON.parse(raw.toString())));
    client.on('close', () => resolve(received));
    client.on('error', reject);
  });

describe('chat WebSocket', () => {
  it('forwards the pipeline parts in order, then closes', async () => {
    jest.mocked(createChatStream).mockResolvedValue(streamOf(ANSWER_PARTS));

    await expect(exchange(JSON.stringify(VALID_PAYLOAD))).resolves.toEqual(ANSWER_PARTS);
    expect(createChatStream).toHaveBeenCalledWith(VALID_PAYLOAD.messages, expect.any(AbortSignal));
  });

  it.each([
    ['a payload that is not JSON', 'Quel délai ?', 'INVALID_JSON'],
    [
      'a message without parts',
      JSON.stringify({ messages: [{ id: 'user-1', role: 'user', content: 'Quel délai ?' }] }),
      'INVALID_REQUEST',
    ],
  ])('answers %s with a request error, without running the pipeline', async (_case, rawPayload, code) => {
    await expect(exchange(rawPayload)).resolves.toEqual([errorPart({ stage: 'request', code })]);
    expect(createChatStream).not.toHaveBeenCalled();
  });

  it('refuses the question once the stream quota is spent', async () => {
    jest.mocked(consumeStreamQuota).mockResolvedValue(false);

    await expect(exchange(JSON.stringify(VALID_PAYLOAD))).resolves.toEqual([
      errorPart({ stage: 'request', code: 'RATE_LIMITED' }),
    ]);
    expect(createChatStream).not.toHaveBeenCalled();
  });

  it('answers with an error part when the pipeline cannot start', async () => {
    jest.mocked(createChatStream).mockRejectedValue(new RagError('request', 'NO_QUESTION', 'No question provided'));

    await expect(exchange(JSON.stringify(VALID_PAYLOAD))).resolves.toEqual([
      errorPart({ stage: 'request', code: 'NO_QUESTION' }),
    ]);
  });

  it('raises the abort signal when the client leaves mid-stream', async () => {
    let pipelineSignal: AbortSignal | undefined;
    jest.mocked(createChatStream).mockImplementation(async (_messages, abortSignal) => {
      pipelineSignal = abortSignal;
      // A pipeline still running: one part, and the stream stays open
      return new ReadableStream<AppChunk>({ start: (controller) => controller.enqueue(ANSWER_PARTS[0]) });
    });

    const client = new WebSocket(serverUrl);
    client.on('open', () => client.send(JSON.stringify(VALID_PAYLOAD)));
    client.on('message', () => client.close());
    await new Promise((resolve) => client.on('close', resolve));
    // The server may see the close before or after the client does
    await new Promise<void>((resolve) => {
      if (pipelineSignal?.aborted) resolve();
      pipelineSignal?.addEventListener('abort', () => resolve());
    });

    expect(pipelineSignal?.aborted).toBe(true);
  });
});
