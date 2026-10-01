import http from 'http';
import { WebSocket } from 'ws';
import type { ClientOptions } from 'ws';
import type { InferUIMessageChunk } from 'ai';
import { attachChatWebSocket, CHAT_WEBSOCKET_PATH } from '../../routes/chatWebSocket';
import { createChatStream } from '../../services/chatService';
import { consumeStreamQuota } from '../../middleware/streamRateLimiter';
import type { AppUIMessage } from '@murphy/contract/messages';
import type { ChatError } from '@murphy/contract/errors';
import { serializeChatError } from '@murphy/contract/errors';
import { RagError } from '../../types/rag';
import { MAX_REQUEST_BODY_BYTES } from '../../utils/requestLimits';
import { logger } from '../../utils/logger';

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
    data: { chunkId: 'chunk-1', identifier: 'LEGIARTI1', highlightStart: 0, highlightEnd: 4, score: 0.9, documentType: 'article' },
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

const ALLOWED_ORIGIN = 'http://localhost:3000';
const CLOSE_CODES = { PROTOCOL_ERROR: 1002, POLICY_VIOLATION: 1008, MESSAGE_TOO_BIG: 1009 };

interface TestServer {
  readonly server: http.Server;
  readonly url: string;
}

/** Un vrai serveur HTTP sur un port éphémère, la socket de chat attachée comme dans `server.ts` */
const startServer = async (firstMessageTimeoutMs?: number): Promise<TestServer> => {
  const server = http.createServer();
  attachChatWebSocket({ server, allowedOrigins: [ALLOWED_ORIGIN], firstMessageTimeoutMs });
  await new Promise<void>((resolve) => server.listen(0, resolve));
  const address = server.address();
  if (address === null || typeof address === 'string') throw new Error('Expected the server to listen on a TCP port');
  return { server, url: `ws://127.0.0.1:${address.port}${CHAT_WEBSOCKET_PATH}` };
};

const stopServer = ({ server }: TestServer): Promise<void> =>
  new Promise<void>((resolve) => server.close(() => resolve()));

let testServer: TestServer;
let serverUrl: string;

beforeAll(async () => {
  testServer = await startServer();
  serverUrl = testServer.url;
});

afterAll(() => stopServer(testServer));

beforeEach(() => {
  jest.mocked(consumeStreamQuota).mockResolvedValue(true);
});

/** Envoie un message brut et collecte les parts reçues jusqu'à la fermeture par le serveur */
const exchange = (rawPayload: string): Promise<unknown[]> =>
  new Promise((resolve, reject) => {
    const received: unknown[] = [];
    const client = new WebSocket(serverUrl);
    client.on('open', () => client.send(rawPayload));
    client.on('message', (raw) => received.push(JSON.parse(raw.toString())));
    client.on('close', () => resolve(received));
    client.on('error', reject);
  });

const HANDSHAKE_HEADERS = {
  Connection: 'Upgrade',
  Upgrade: 'websocket',
  'Sec-WebSocket-Key': 'dGhlIHNhbXBsZSBub25jZQ==',
  'Sec-WebSocket-Version': '13',
};
/** Trame texte "hi" sans le bit de masque, que la RFC 6455 exige d'un client */
const UNMASKED_FRAME = Buffer.from([0x81, 0x02, 0x68, 0x69]);

/** Upgrade à la main, écrit une trame brute et rend les premiers octets renvoyés par le serveur */
const sendRawFrame = (frame: Buffer): Promise<Buffer> =>
  new Promise((resolve, reject) => {
    const request = http.request(serverUrl.replace(/^ws/, 'http'), { headers: HANDSHAKE_HEADERS });
    request.on('upgrade', (_response, socket) => {
      socket.once('data', (reply: Buffer) => {
        socket.destroy();
        resolve(reply);
      });
      socket.write(frame);
    });
    request.on('error', reject);
    request.end();
  });

/** Ouvre une socket, envoie `rawPayload` s'il est fourni, et rend le code de fermeture du serveur */
const closeCodeAfter = (url: string, rawPayload?: string): Promise<number> =>
  new Promise((resolve, reject) => {
    const client = new WebSocket(url);
    if (rawPayload !== undefined) client.on('open', () => client.send(rawPayload));
    client.on('close', (code) => resolve(code));
    client.on('error', reject);
  });

const SWITCHING_PROTOCOLS = 101;

/** Rend le statut HTTP de la poignée de main : 101 si la socket s'ouvre, sinon celui du refus */
const handshakeStatus = (options: ClientOptions): Promise<number> =>
  new Promise((resolve, reject) => {
    const client = new WebSocket(serverUrl, options);
    client.on('open', () => {
      client.close();
      resolve(SWITCHING_PROTOCOLS);
    });
    client.on('unexpected-response', (_request, response) => {
      client.terminate();
      resolve(response.statusCode ?? 0);
    });
    client.on('error', reject);
  });

describe('chat WebSocket limits', () => {
  it('survives an invalid frame: it closes that socket with a protocol error and keeps serving', async () => {
    jest.mocked(createChatStream).mockResolvedValue(streamOf(ANSWER_PARTS));

    const reply = await sendRawFrame(UNMASKED_FRAME);

    expect(reply.readUInt16BE(2)).toBe(CLOSE_CODES.PROTOCOL_ERROR);
    expect(logger.warn).toHaveBeenCalledWith(expect.objectContaining({ err: expect.any(RangeError) }), expect.any(String));
    await expect(exchange(JSON.stringify(VALID_PAYLOAD))).resolves.toEqual(ANSWER_PARTS);
  });

  it('closes the socket on a message larger than an HTTP request body, without running the pipeline', async () => {
    const oversizedPayload = 'x'.repeat(MAX_REQUEST_BODY_BYTES + 1);

    await expect(closeCodeAfter(serverUrl, oversizedPayload)).resolves.toBe(CLOSE_CODES.MESSAGE_TOO_BIG);
    expect(createChatStream).not.toHaveBeenCalled();
  });

  it.each([
    ['an allowed origin', { origin: ALLOWED_ORIGIN }, SWITCHING_PROTOCOLS],
    ['no origin (not a browser)', {}, SWITCHING_PROTOCOLS],
    ['another origin', { origin: 'https://evil.example' }, 403],
  ])('answers the handshake of %s with status %i', async (_case, options, status) => {
    await expect(handshakeStatus(options)).resolves.toBe(status);
  });

  it('closes a socket that sends nothing', async () => {
    const idleServer = await startServer(50);
    try {
      await expect(closeCodeAfter(idleServer.url)).resolves.toBe(CLOSE_CODES.POLICY_VIOLATION);
    } finally {
      await stopServer(idleServer);
    }
  });
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
      // Un pipeline encore en cours : une part, et le flux reste ouvert
      return new ReadableStream<AppChunk>({ start: (controller) => controller.enqueue(ANSWER_PARTS[0]) });
    });

    const client = new WebSocket(serverUrl);
    client.on('open', () => client.send(JSON.stringify(VALID_PAYLOAD)));
    client.on('message', () => client.close());
    await new Promise((resolve) => client.on('close', resolve));
    // Le serveur peut voir la fermeture avant ou après le client
    await new Promise<void>((resolve) => {
      if (pipelineSignal?.aborted) resolve();
      pipelineSignal?.addEventListener('abort', () => resolve());
    });

    expect(pipelineSignal?.aborted).toBe(true);
  });
});
