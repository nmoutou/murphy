/**
 * Chat Routes
 * HTTP endpoints for RAG-powered chat (the frontend uses the WebSocket, `chatWebSocket.ts`)
 */

import express, { Request, Response } from 'express';
import type { InferUIMessageChunk } from 'ai';
import { pipeUIMessageStreamToResponse } from 'ai';
import { logger as rootLogger } from '../utils/logger';
import { createChatStream } from '../services/chatService';
import { asyncHandler } from '../middleware/errorHandler';
import { streamRateLimiter } from '../middleware/streamRateLimiter';
import { buildApiResponse } from '../utils/response';
import { parseChatRequest } from '../validation/chatRequest';
import type { ValidationIssue } from '../validation/chatRequest';
import type { AppUIMessage } from '@murphy/contract/messages';
import type { ChatError } from '@murphy/contract/errors';
import { parseChatError } from '@murphy/contract/errors';
import { toChatError } from '../types/rag';

const logger = rootLogger.child({ context: 'chatRoutes' });
const router = express.Router();

const HTTP_BAD_REQUEST = 400;
const HTTP_SERVER_ERROR = 500;
const CHAT_STREAM_ERROR = 'CHAT_STREAM_ERROR';

const sendValidationError = (res: Response, issues: readonly ValidationIssue[]): void => {
  res.status(HTTP_BAD_REQUEST).json({ ...buildApiResponse(HTTP_BAD_REQUEST, 'VALIDATION_ERROR'), errors: issues });
};

/** Raised when the client leaves: the pipeline stops, the LLM included (ADR-041) */
const abortOnClose = (res: Response): AbortSignal => {
  const abortController = new AbortController();
  res.on('close', () => abortController.abort());
  return abortController.signal;
};

interface DrainedAnswer {
  readonly text: string;
  /** Set when the stream ended on an `error` part */
  readonly chatError?: ChatError;
}

const drainAnswer = async (stream: ReadableStream<InferUIMessageChunk<AppUIMessage>>): Promise<DrainedAnswer> => {
  const reader = stream.getReader();
  let text = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) return { text };
    if (value.type === 'text-delta') text += value.delta;
    if (value.type === 'error') return { text, chatError: parseChatError(value.errorText) };
  }
};

/**
 * POST /api/v1/chat/streams
 * Stream RAG-powered chat response via SSE
 *
 * Request body: { messages: AppUIMessage[] } — only the last `user` message is used
 *
 * Response: SSE stream of AI SDK UI message parts (start, data-document, text-delta,
 * finish, or error)
 */
router.post(
  '/streams',
  streamRateLimiter,
  asyncHandler(async (req: Request, res: Response) => {
    const request = await parseChatRequest(req.body);
    if (!request.isValid) {
      sendValidationError(res, request.issues);
      return;
    }
    try {
      const stream = await createChatStream(request.messages, abortOnClose(res));

      pipeUIMessageStreamToResponse({
        response: res,
        stream,
      });
    } catch (error) {
      logger.error({ err: error }, 'Chat stream error');
      res.status(HTTP_SERVER_ERROR).json(buildApiResponse(HTTP_SERVER_ERROR, CHAT_STREAM_ERROR, toChatError(error)));
    }
  })
);

/**
 * POST /api/v1/chat/completions
 * Same pipeline, drained into a single JSON response with the full answer text
 */
router.post(
  '/completions',
  streamRateLimiter,
  asyncHandler(async (req: Request, res: Response) => {
    const request = await parseChatRequest(req.body);
    if (!request.isValid) {
      sendValidationError(res, request.issues);
      return;
    }
    try {
      const { text, chatError } = await drainAnswer(await createChatStream(request.messages, abortOnClose(res)));
      if (chatError) {
        res.status(HTTP_SERVER_ERROR).json(buildApiResponse(HTTP_SERVER_ERROR, CHAT_STREAM_ERROR, chatError));
        return;
      }
      res.json(buildApiResponse(200, 'OK', { role: 'assistant', parts: [{ type: 'text', text }] }));
    } catch (error) {
      logger.error({ err: error }, 'Chat completions error');
      res.status(HTTP_SERVER_ERROR).json(buildApiResponse(HTTP_SERVER_ERROR, CHAT_STREAM_ERROR, toChatError(error)));
    }
  })
);

export default router;
