/** POST /api/v1/search — une page de la recherche hybride (ADR-030) */

import express, { Request, Response } from 'express';
import { asyncHandler } from '../middleware/errorHandler';
import { searchRateLimiter } from '../middleware/searchRateLimiter';
import { searchDocuments } from '../services/searchService';
import { buildApiResponse } from '../utils/response';
import { HTTP_STATUS } from '../utils/httpStatus';
import { parseSearchRequest } from '../validation/searchRequest';

const router = express.Router();

router.post(
  '/',
  searchRateLimiter,
  asyncHandler(async (req: Request, res: Response) => {
    const parsed = parseSearchRequest(req.body);
    if (!parsed.isValid) {
      res
        .status(HTTP_STATUS.BAD_REQUEST)
        .json({ ...buildApiResponse(HTTP_STATUS.BAD_REQUEST, 'VALIDATION_ERROR'), errors: parsed.issues });
      return;
    }
    res.json(buildApiResponse(HTTP_STATUS.OK, 'OK', await searchDocuments(parsed.request)));
  }),
);

export default router;
