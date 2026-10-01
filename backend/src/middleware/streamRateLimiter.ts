/**
 * Budget par IP du pipeline de chat, plus strict que le limiteur global. `/streams`,
 * `/completions` et le WebSocket le partagent : chacun lance tout le pipeline, LLM compris.
 */

import rateLimit, { ipKeyGenerator, MemoryStore } from 'express-rate-limit';
import { Request, Response } from 'express';
import { logger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';
import { config } from '../config';
import { HTTP_STATUS } from '../utils/httpStatus';


const streamQuotaStore = new MemoryStore();

/** `req.ip` ne suit `X-Forwarded-For` que si `trust proxy` l'autorise (`app.ts`) */
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
 * Pendant WebSocket : l'upgrade n'est pas une requête Express, donc chaque message
 * compte un hit sur le même store. `false` une fois le budget épuisé.
 */
export const consumeStreamQuota = async (remoteAddress: string | undefined): Promise<boolean> => {
  if (!remoteAddress) return false;
  const { totalHits } = await streamQuotaStore.increment(ipKeyGenerator(remoteAddress));
  return totalHits <= config.http.streamRateLimit.limit;
};
