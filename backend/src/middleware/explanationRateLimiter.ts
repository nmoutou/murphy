/**
 * Les deux plafonds de `POST /explanations` (ADR-033 §12) : un appel au LLM coûte de
 * l'argent, à l'inverse d'une recherche.
 */

import rateLimit from 'express-rate-limit';
import { Request, Response } from 'express';
import { logger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';
import { config } from '../config';
import { HTTP_STATUS } from '../utils/httpStatus';

const ONE_DAY_MS = 86_400_000;
/** Un seul compteur pour tous les clients */
const GLOBAL_KEY = 'explanations';

/** `req.ip` ne suit `X-Forwarded-For` que si `trust proxy` l'autorise (`app.ts`) */
export const explanationRateLimiter = rateLimit({
  windowMs: config.http.explanationRateLimit.windowMs,
  limit: config.http.explanationRateLimit.limit,
  handler: (req: Request, res: Response) => {
    logger.warn({ ip: req.ip, endpoint: req.originalUrl }, 'Explanation rate limit exceeded');
    res
      .status(HTTP_STATUS.TOO_MANY_REQUESTS)
      .json(buildApiResponse(HTTP_STATUS.TOO_MANY_REQUESTS, 'EXPLANATION_RATE_LIMIT_EXCEEDED'));
  },
  standardHeaders: true,
  legacyHeaders: false,
});

/**
 * En mémoire : un redémarrage le remet à zéro, chaque instance a le sien. Une requête
 * refusée (4xx : validation, budget) ou dont le LLM a échoué avant le flux (5xx) ne
 * compte pas.
 */
export const explanationQuotaLimiter = rateLimit({
  windowMs: ONE_DAY_MS,
  limit: config.http.explanationDailyLimit,
  keyGenerator: () => GLOBAL_KEY,
  skipFailedRequests: true,
  handler: (req: Request, res: Response) => {
    logger.warn({ endpoint: req.originalUrl }, 'Explanation daily quota exceeded');
    res
      .status(HTTP_STATUS.TOO_MANY_REQUESTS)
      .json(buildApiResponse(HTTP_STATUS.TOO_MANY_REQUESTS, 'EXPLANATION_QUOTA_EXCEEDED'));
  },
  standardHeaders: false,
  legacyHeaders: false,
});
