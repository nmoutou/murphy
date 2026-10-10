/**
 * WebSocket du chat, le transport du frontend : un `{ messages }` en entrée, les parts
 * du message en sortie, puis la socket se ferme.
 */

import type { IncomingMessage, Server } from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import type { RawData, VerifyClientCallbackAsync } from 'ws';
import type { InferUIMessageChunk } from 'ai';
import { logger as rootLogger } from '../utils/logger';
import { createChatStream } from '../services/chatService';
import { consumeSearchQuota } from '../middleware/searchRateLimiter';
import { parseChatRequest } from '../validation/chatRequest';
import type { AppUIMessage } from '@murphy/contract/messages';
import type { ChatError } from '@murphy/contract/errors';
import { serializeChatError } from '@murphy/contract/errors';
import { toChatError } from '../types/rag';
import { HTTP_STATUS } from '../utils/httpStatus';
import { MAX_REQUEST_BODY_BYTES } from '../utils/requestLimits';

const logger = rootLogger.child({ context: 'chatWebSocket' });

export const CHAT_WEBSOCKET_PATH = '/api/v1/chat/ws';
/** Le frontend envoie sa question dès l'ouverture */
const FIRST_MESSAGE_TIMEOUT_MS = 10_000;
/** Code de fermeture RFC 6455 : violation de politique */
const POLICY_VIOLATION_CLOSE_CODE = 1008;

interface ChatWebSocketOptions {
  readonly server: Server;
  /** `config.http.corsOrigins` : `false` refuse tout navigateur */
  readonly allowedOrigins: readonly string[] | false;
  readonly firstMessageTimeoutMs?: number;
}

const RATE_LIMITED_ERROR: ChatError = { stage: 'request', code: 'RATE_LIMITED' };
const INVALID_JSON_ERROR: ChatError = { stage: 'request', code: 'INVALID_JSON' };
const INVALID_REQUEST_ERROR: ChatError = { stage: 'request', code: 'INVALID_REQUEST' };

const sendErrorAndClose = (ws: WebSocket, chatError: ChatError): void => {
  ws.send(JSON.stringify({ type: 'error', errorText: serializeChatError(chatError) }));
  ws.close();
};

const parseJson = (raw: RawData): unknown => {
  try {
    return JSON.parse(raw.toString());
  } catch {
    return undefined;
  }
};

const forwardStream = async (ws: WebSocket, stream: ReadableStream<InferUIMessageChunk<AppUIMessage>>): Promise<void> => {
  const reader = stream.getReader();
  ws.on('close', () => {
    reader.cancel().catch(() => undefined);
  });

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    ws.send(JSON.stringify(value));
  }
  ws.close();
};

const handleChatMessage = async (ws: WebSocket, raw: RawData, remoteAddress: string | undefined): Promise<void> => {
  if (!(await consumeSearchQuota(remoteAddress))) {
    logger.warn({ ip: remoteAddress }, 'Stream rate limit exceeded');
    sendErrorAndClose(ws, RATE_LIMITED_ERROR);
    return;
  }

  const payload = parseJson(raw);
  if (payload === undefined) {
    logger.warn('Chat payload is not valid JSON');
    sendErrorAndClose(ws, INVALID_JSON_ERROR);
    return;
  }

  const request = await parseChatRequest(payload);
  if (!request.isValid) {
    logger.warn({ issues: request.issues }, 'Invalid chat request');
    sendErrorAndClose(ws, INVALID_REQUEST_ERROR);
    return;
  }

  // Le départ du client arrête le pipeline, LLM compris (ADR-017)
  const abortController = new AbortController();
  ws.on('close', () => abortController.abort());
  try {
    await forwardStream(ws, await createChatStream(request.messages, abortController.signal));
  } catch (error) {
    logger.error({ err: error }, 'WebSocket chat stream failed');
    sendErrorAndClose(ws, toChatError(error));
  }
};

/** Seul un navigateur envoie `Origin`, infalsifiable par une page tierce : même liste que le CORS HTTP */
const isOriginAllowed = (origin: string | undefined, allowedOrigins: readonly string[] | false): boolean => {
  if (origin === undefined) return true;
  return allowedOrigins !== false && allowedOrigins.includes(origin);
};

const createOriginVerifier =
  (allowedOrigins: readonly string[] | false): VerifyClientCallbackAsync =>
  ({ req }, callback) => {
    const { origin } = req.headers;
    if (isOriginAllowed(origin, allowedOrigins)) {
      callback(true);
      return;
    }
    logger.warn({ origin }, 'WebSocket origin refused');
    callback(false, HTTP_STATUS.FORBIDDEN);
  };

const handleConnection = (ws: WebSocket, request: IncomingMessage, firstMessageTimeoutMs: number): void => {
  const remoteAddress = request.socket.remoteAddress;
  logger.info('WebSocket client connected');

  // Trame invalide ou trop grosse : ws ferme déjà la socket, mais un `error` sans
  // écouteur devient une exception non rattrapée qui arrête le serveur
  ws.on('error', (error: Error) => {
    logger.warn({ err: error, ip: remoteAddress }, 'WebSocket protocol error, socket closed');
  });

  const idleTimer = setTimeout(
    () => ws.close(POLICY_VIOLATION_CLOSE_CODE, 'No message received'),
    firstMessageTimeoutMs,
  );
  ws.on('close', () => clearTimeout(idleTimer));

  ws.once('message', (raw: RawData) => {
    clearTimeout(idleTimer);
    handleChatMessage(ws, raw, remoteAddress).catch((error: unknown) => {
      logger.error({ err: error }, 'WebSocket chat handler failed');
    });
  });
};

export const attachChatWebSocket = (options: ChatWebSocketOptions): void => {
  const { server, allowedOrigins, firstMessageTimeoutMs = FIRST_MESSAGE_TIMEOUT_MS } = options;
  const wss = new WebSocketServer({
    server,
    path: CHAT_WEBSOCKET_PATH,
    maxPayload: MAX_REQUEST_BODY_BYTES,
    verifyClient: createOriginVerifier(allowedOrigins),
  });
  wss.on('connection', (ws: WebSocket, request: IncomingMessage) => handleConnection(ws, request, firstMessageTimeoutMs));
};
