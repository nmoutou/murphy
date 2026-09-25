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
import type { AppUIMessage } from '../../types/messages';

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
  { type: 'data-document', data: { chunkId: 'chunk-1', score: 0.9 } },
  { type: 'text-delta', id: MESSAGE_ID, delta: 'Cinq ans.' },
  { type: 'finish', finishReason: 'stop' },
];

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
    expect(createChatStream).toHaveBeenCalledWith(VALID_PAYLOAD.messages);
  });

  it.each([
    ['a payload that is not JSON', 'Quel délai ?', 'Invalid request: payload is not valid JSON'],
    [
      'a message without parts',
      JSON.stringify({ messages: [{ id: 'user-1', role: 'user', content: 'Quel délai ?' }] }),
      'Invalid request: messages[0].parts: parts must be an array of objects with a string type',
    ],
  ])('answers %s with an error part, without running the pipeline', async (_case, rawPayload, errorText) => {
    await expect(exchange(rawPayload)).resolves.toEqual([{ type: 'error', errorText }]);
    expect(createChatStream).not.toHaveBeenCalled();
  });

  it('refuses the question once the stream quota is spent', async () => {
    jest.mocked(consumeStreamQuota).mockResolvedValue(false);

    await expect(exchange(JSON.stringify(VALID_PAYLOAD))).resolves.toEqual([
      { type: 'error', errorText: 'Too many requests, please try again later' },
    ]);
    expect(createChatStream).not.toHaveBeenCalled();
  });

  it('answers with an error part when the pipeline cannot start', async () => {
    jest.mocked(createChatStream).mockRejectedValue(new Error('No question provided'));

    await expect(exchange(JSON.stringify(VALID_PAYLOAD))).resolves.toEqual([
      { type: 'error', errorText: 'No question provided' },
    ]);
  });
});
