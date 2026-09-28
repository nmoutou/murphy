/**
 * Stream Rate Limiter
 * Per-IP budget for the chat pipeline, stricter than the global limiter. POST
 * `/api/v1/chat/streams`, POST `/api/v1/chat/completions` and the WebSocket
 * draw from the same budget: each one runs the whole pipeline, the LLM included.
 */

import rateLimit, { ipKeyGenerator, MemoryStore } from 'express-rate-limit';
import { Request, Response } from 'express';
import { logger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';
import { config } from '../config';
import { HTTP_STATUS } from '../utils/httpStatus';


const streamQuotaStore = new MemoryStore();

/**
 * HTTP side. The key is the default `ipKeyGenerator(req.ip)`: `req.ip` only
 * honours `X-Forwarded-For` as far as `trust proxy` allows (`app.ts`).
 */
export const streamRateLimiter = rateLimit({
  windowMs: config.http.streamRateLimit.windowMs,
  limit: config.http.streamRateLimit.limit,
  store: streamQuotaStore,
  handler: (req: Request, res: Response) => {
    logger.warn({ ip: req.ip, endpoint: req.originalUrl }, 'Stream rate limit exceeded');
    res.status(HTTP_STATUS.TOO_MANY_REQUESTS).json(buildApiResponse(HTTP_STATUS.TOO_MANY_REQUESTS, 'STREAM_RATE_LIMIT_EXCEEDED'));
  },
  standardHeaders: true,
  legacyHeaders: false,
});

/**
 * WebSocket side. The upgrade request is not an Express request, so the
 * middleware cannot run on it: each chat message counts one hit on the same
 * store instead. Resolves `false` once the budget is spent.
 */
export const consumeStreamQuota = async (remoteAddress: string | undefined): Promise<boolean> => {
  if (!remoteAddress) return false;
  const { totalHits } = await streamQuotaStore.increment(ipKeyGenerator(remoteAddress));
  return totalHits <= config.http.streamRateLimit.limit;
};
