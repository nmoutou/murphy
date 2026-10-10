/** GET /api/v1/documents/:identifier — le texte entier d'un document (ADR-031) */

import express, { Request, Response } from 'express';
import { asyncHandler } from '../middleware/errorHandler';
import { readDocument } from '../services/documentService';
import { buildApiResponse } from '../utils/response';
import { HTTP_STATUS } from '../utils/httpStatus';

const router = express.Router();

router.get(
  '/:identifier',
  asyncHandler(async (req: Request<{ identifier: string }>, res: Response) => {
    res.json(buildApiResponse(HTTP_STATUS.OK, 'OK', await readDocument(req.params.identifier)));
  }),
);

export default router;
