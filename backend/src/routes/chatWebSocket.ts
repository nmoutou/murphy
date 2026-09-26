/**
 * Chat WebSocket (`/api/v1/chat/ws`) — the transport the frontend uses
 * One `{ messages }` payload in, the AI SDK UI message parts out, then the socket closes
 */

import type { IncomingMessage } from 'http';
import { WebSocketServer, WebSocket } from 'ws';
import type { RawData } from 'ws';
import type { InferUIMessageChunk } from 'ai';
import { logger as rootLogger } from '../utils/logger';
import { createChatStream } from '../services/chatService';
import { consumeStreamQuota } from '../middleware/streamRateLimiter';
import { parseChatRequest } from '../validation/chatRequest';
import type { AppUIMessage } from '@murphy/contract/messages';
import type { ChatError } from '@murphy/contract/errors';
import { serializeChatError } from '@murphy/contract/errors';
import { toChatError } from '../types/rag';

const logger = rootLogger.child({ context: 'chatWebSocket' });

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
  if (!(await consumeStreamQuota(remoteAddress))) {
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

  const request = parseChatRequest(payload);
  if (!request.isValid) {
    logger.warn({ issues: request.issues }, 'Invalid chat request');
    sendErrorAndClose(ws, INVALID_REQUEST_ERROR);
    return;
  }

  // The client leaving stops the pipeline, the LLM included (ADR-041)
  const abortController = new AbortController();
  ws.on('close', () => abortController.abort());
  try {
    await forwardStream(ws, await createChatStream(request.messages, abortController.signal));
  } catch (error) {
    logger.error({ err: error }, 'WebSocket chat stream failed');
    sendErrorAndClose(ws, toChatError(error));
  }
};

export function registerChatWebSocket(wss: WebSocketServer): void {
  wss.on('connection', (ws: WebSocket, request: IncomingMessage) => {
    logger.info('WebSocket client connected');

    ws.once('message', (raw: RawData) => {
      handleChatMessage(ws, raw, request.socket.remoteAddress).catch((error: unknown) => {
        logger.error({ err: error }, 'WebSocket chat handler failed');
      });
    });
  });
}
