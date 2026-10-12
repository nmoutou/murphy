/** POST /api/v1/explanations — le LLM explique les documents choisis, en flux SSE (ADR-033) */

import express, { Request, Response } from 'express';
import { asyncHandler } from '../middleware/errorHandler';
import { explanationQuotaLimiter, explanationRateLimiter } from '../middleware/explanationRateLimiter';
import { openAnswer, prepareExplanation } from '../services/explanationService';
import { streamExplanation } from '../services/explanationStream';
import { buildApiResponse } from '../utils/response';
import { HTTP_STATUS } from '../utils/httpStatus';
import { parseExplanationRequest } from '../validation/explanationRequest';

const router = express.Router();

/** `req.on('close')` part dès le corps lu : seule la fermeture de la réponse dit que le client est parti */
const abortWhenClientLeaves = (res: Response): AbortSignal => {
  const controller = new AbortController();
  res.on('close', () => {
    if (!res.writableEnded) controller.abort();
  });
  return controller.signal;
};

router.post(
  '/',
  explanationRateLimiter,
  explanationQuotaLimiter,
  asyncHandler(async (req: Request, res: Response) => {
    const parsed = parseExplanationRequest(req.body);
    if (!parsed.isValid) {
      res
        .status(HTTP_STATUS.BAD_REQUEST)
        .json({ ...buildApiResponse(HTTP_STATUS.BAD_REQUEST, 'VALIDATION_ERROR'), errors: parsed.issues });
      return;
    }
    const signal = abortWhenClientLeaves(res);
    const prepared = await prepareExplanation(parsed.request);
    const opened = await openAnswer(prepared, signal);
    streamExplanation({ response: res, prepared, opened, signal });
  }),
);

export default router;
