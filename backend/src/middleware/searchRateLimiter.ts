/**
 * Budget par IP de la recherche, plus strict que le limiteur global : chaque recherche
 * appelle TEI et OpenSearch (ADR-031 §5).
 */

import rateLimit from 'express-rate-limit';
import { Request, Response } from 'express';
import { logger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';
import { config } from '../config';
import { HTTP_STATUS } from '../utils/httpStatus';

/** `req.ip` ne suit `X-Forwarded-For` que si `trust proxy` l'autorise (`app.ts`) */
export const searchRateLimiter = rateLimit({
  windowMs: config.http.searchRateLimit.windowMs,
  limit: config.http.searchRateLimit.limit,
  handler: (req: Request, res: Response) => {
    logger.warn({ ip: req.ip, endpoint: req.originalUrl }, 'Search rate limit exceeded');
    res
      .status(HTTP_STATUS.TOO_MANY_REQUESTS)
      .json(buildApiResponse(HTTP_STATUS.TOO_MANY_REQUESTS, 'SEARCH_RATE_LIMIT_EXCEEDED'));
  },
  standardHeaders: true,
  legacyHeaders: false,
});
