/**
 * Chat Routes
 * HTTP endpoints for RAG-powered chat (the frontend uses the WebSocket, `chatWebSocket.ts`)
 */

import express, { Request, Response } from 'express';
import { pipeUIMessageStreamToResponse } from 'ai';
import { logger as rootLogger } from '../utils/logger';
import { createChatStream } from '../services/chatService';
import { asyncHandler } from '../middleware/errorHandler';
import { streamRateLimiter } from '../middleware/streamRateLimiter';
import { buildApiResponse } from '../utils/response';
import { parseChatRequest } from '../validation/chatRequest';
import type { ValidationIssue } from '../validation/chatRequest';

const logger = rootLogger.child({ context: 'chatRoutes' });
const router = express.Router();

const HTTP_BAD_REQUEST = 400;

const sendValidationError = (res: Response, issues: readonly ValidationIssue[]): void => {
  res.status(HTTP_BAD_REQUEST).json({ ...buildApiResponse(HTTP_BAD_REQUEST, 'VALIDATION_ERROR'), errors: issues });
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
    const request = parseChatRequest(req.body);
    if (!request.isValid) {
      sendValidationError(res, request.issues);
      return;
    }
    try {
      const stream = await createChatStream(request.messages);

      pipeUIMessageStreamToResponse({
        response: res,
        stream,
      });
    } catch (error) {
      logger.error({ err: error }, 'Chat stream error');
      res.status(500).json(buildApiResponse(500, 'CHAT_STREAM_ERROR'));
    }
  })
);

/**
 * POST /api/v1/chat/completions
 * Same pipeline, drained into a single JSON response with the full answer text
 */
router.post(
  '/completions',
  asyncHandler(async (req: Request, res: Response) => {
    const request = parseChatRequest(req.body);
    if (!request.isValid) {
      sendValidationError(res, request.issues);
      return;
    }
    try {
      const stream = await createChatStream(request.messages);
      const reader = stream.getReader();
      let text = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        if (value.type === 'text-delta') {
          text += value.delta;
        }
        if (value.type === 'error') {
          throw new Error(value.errorText);
        }
      }

      res.json(buildApiResponse(200, 'OK', { role: 'assistant', parts: [{ type: 'text', text }] }));
    } catch (error) {
      logger.error({ err: error }, 'Chat completions error');
      res.status(500).json(buildApiResponse(500, 'CHAT_STREAM_ERROR'));
    }
  })
);

export default router;
