import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';

const INTERNAL_ERROR_STATUS = 500;
const INTERNAL_ERROR_CODE = 'INTERNAL_ERROR';

/**
 * Async route wrapper to catch errors
 */
export const asyncHandler = (
  fn: (req: Request, res: Response, next: NextFunction) => Promise<void>
) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

/**
 * Global error handler middleware: any error that reaches it is an unexpected 500
 */
export const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  _next: NextFunction
): void => {
  logger.error({
    err: error,
    code: INTERNAL_ERROR_CODE,
    statusCode: INTERNAL_ERROR_STATUS,
    path: req.path,
    method: req.method,
  }, 'Request error');

  res.status(INTERNAL_ERROR_STATUS).json(buildApiResponse(INTERNAL_ERROR_STATUS, INTERNAL_ERROR_CODE));
};

/**
 * 404 Not Found handler
 */
export const notFoundHandler = (_req: Request, res: Response): void => {
  res.status(404).json(buildApiResponse(404, 'NOT_FOUND'));
};
