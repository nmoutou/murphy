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

const logger = rootLogger.child({ context: 'chatWebSocket' });

const RATE_LIMIT_ERROR = 'Too many requests, please try again later';
const INVALID_JSON_ERROR = 'Invalid request: payload is not valid JSON';

const sendErrorAndClose = (ws: WebSocket, errorText: string): void => {
  ws.send(JSON.stringify({ type: 'error', errorText }));
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
    sendErrorAndClose(ws, RATE_LIMIT_ERROR);
    return;
  }

  const payload = parseJson(raw);
  if (payload === undefined) {
    sendErrorAndClose(ws, INVALID_JSON_ERROR);
    return;
  }

  const request = parseChatRequest(payload);
  if (!request.isValid) {
    const details = request.issues.map((issue) => `${issue.field}: ${issue.message}`).join('; ');
    sendErrorAndClose(ws, `Invalid request: ${details}`);
    return;
  }

  try {
    await forwardStream(ws, await createChatStream(request.messages));
  } catch (error) {
    logger.error({ err: error }, 'WebSocket chat stream failed');
    sendErrorAndClose(ws, error instanceof Error ? error.message : String(error));
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
