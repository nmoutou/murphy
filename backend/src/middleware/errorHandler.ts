import { Request, Response, NextFunction } from 'express';
import { logger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';
import { HTTP_STATUS } from '../utils/httpStatus';

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
    statusCode: HTTP_STATUS.INTERNAL_SERVER_ERROR,
    path: req.path,
    method: req.method,
  }, 'Request error');

  res.status(HTTP_STATUS.INTERNAL_SERVER_ERROR).json(buildApiResponse(HTTP_STATUS.INTERNAL_SERVER_ERROR, INTERNAL_ERROR_CODE));
};

/**
 * 404 Not Found handler
 */
export const notFoundHandler = (_req: Request, res: Response): void => {
  res.status(HTTP_STATUS.NOT_FOUND).json(buildApiResponse(HTTP_STATUS.NOT_FOUND, 'NOT_FOUND'));
};
