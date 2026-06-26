/**
 * Chat Routes
 * SSE streaming endpoint for RAG-powered chat
 */

import express, { Request, Response } from 'express';
import { pipeUIMessageStreamToResponse } from 'ai';
import { logger as rootLogger } from '../utils/logger';
import { createChatStream } from '../services/chatService';
import { asyncHandler } from '../middleware/errorHandler';
import { chatValidation, validationErrorHandler } from '../middleware/validation';
import { streamRateLimiter } from '../middleware/streamRateLimiter';
import { buildApiResponse } from '../utils/response';
import { AppUIMessage } from '../types/messages';

export { createChatStream } from '../services/chatService';

const logger = rootLogger.child({ context: 'chatRoutes' });
const router = express.Router();

/**
 * POST /api/chat/stream
 * Stream RAG-powered chat response via SSE
 *
 * Request body:
 * {
 *   id: string (request ID for tracking)
 *   question: string (user question)
 *   history?: Array<{role, content}> (ignored in V1, for future use)
 * }
 *
 * Response: SSE stream with events (start, token, token, ..., end or error)
 */
router.post(
  '/streams',
  streamRateLimiter,
  chatValidation,
  validationErrorHandler,
  asyncHandler(async (req: Request, res: Response) => {
    try {
      const { messages } = req.body as { messages: AppUIMessage[] };
      const stream = await createChatStream(messages || []);

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

router.post(
  '/completions',
  chatValidation,
  validationErrorHandler,
  asyncHandler(async (req: Request, res: Response) => {
    try {
      const { messages } = req.body as { messages: AppUIMessage[] };
      const stream = await createChatStream(messages || []);
      const reader = stream.getReader();
      let text = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const part = value as { type: string; delta?: string; errorText?: string };
        if (part.type === 'text-delta') {
          text += part.delta;
        }
        if (part.type === 'error') {
          throw new Error(part.errorText);
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
