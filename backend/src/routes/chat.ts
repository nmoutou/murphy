/** Points d'entrée HTTP du chat ; le frontend, lui, passe par `chatWebSocket.ts` */

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
import { HTTP_STATUS } from '../utils/httpStatus';

const logger = rootLogger.child({ context: 'chatRoutes' });
const router = express.Router();

const CHAT_STREAM_ERROR = 'CHAT_STREAM_ERROR';

const sendValidationError = (res: Response, issues: readonly ValidationIssue[]): void => {
  res.status(HTTP_STATUS.BAD_REQUEST).json({ ...buildApiResponse(HTTP_STATUS.BAD_REQUEST, 'VALIDATION_ERROR'), errors: issues });
};

const sendChatError = (res: Response, chatError: ChatError): void => {
  res
    .status(HTTP_STATUS.INTERNAL_SERVER_ERROR)
    .json(buildApiResponse(HTTP_STATUS.INTERNAL_SERVER_ERROR, CHAT_STREAM_ERROR, chatError));
};

/** Levé quand le client part : le pipeline s'arrête, LLM compris (ADR-017) */
const abortOnClose = (res: Response): AbortSignal => {
  const abortController = new AbortController();
  res.on('close', () => abortController.abort());
  return abortController.signal;
};

interface DrainedAnswer {
  readonly text: string;
  /** Présent si le flux a fini sur une part `error` */
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
 * POST /api/v1/chat/streams — la réponse en SSE, part par part. Seul le dernier
 * message `user` de `{ messages }` compte.
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
      sendChatError(res, toChatError(error));
    }
  })
);

/** POST /api/v1/chat/completions — le même pipeline, rendu en une seule réponse JSON */
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
        sendChatError(res, chatError);
        return;
      }
      res.json(buildApiResponse(HTTP_STATUS.OK, 'OK', { role: 'assistant', parts: [{ type: 'text', text }] }));
    } catch (error) {
      logger.error({ err: error }, 'Chat completions error');
      sendChatError(res, toChatError(error));
    }
  })
);

export default router;
