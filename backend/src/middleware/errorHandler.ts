import { Request, Response, NextFunction } from 'express';
import logger from '../utils/logger';
import { buildApiResponse } from '../utils/response';

/**
 * Custom error class with HTTP status code
 */
export class AppError extends Error {
  public readonly statusCode: number;
  public readonly code: string;
  public readonly isOperational: boolean;

  constructor(
    message: string,
    statusCode: number = 500,
    code: string = 'INTERNAL_ERROR',
    isOperational: boolean = true
  ) {
    super(message);
    this.statusCode = statusCode;
    this.code = code;
    this.isOperational = isOperational;
    
    Object.setPrototypeOf(this, AppError.prototype);
    Error.captureStackTrace(this, this.constructor);
  }
}

/**
 * Async route wrapper to catch errors
 */
export const asyncHandler = (
  fn: (req: Request, res: Response, next: NextFunction) => Promise<any>
) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

/**
 * Global error handler middleware
 */
export const errorHandler = (
  error: Error | AppError,
  req: Request,
  res: Response,
  _next: NextFunction
): void => {
  const statusCode = error instanceof AppError ? error.statusCode : 500;
  const code = error instanceof AppError ? error.code : 'INTERNAL_ERROR';
  const isOperational = error instanceof AppError ? error.isOperational : false;

  // Log error with Pino
  logger.error({
    err: error,
    code,
    statusCode,
    path: req.path,
    method: req.method,
    isOperational,
  }, 'Request error');

  res.status(statusCode).json(buildApiResponse(statusCode, code));
};

/**
 * 404 Not Found handler
 */
export const notFoundHandler = (_req: Request, res: Response): void => {
  res.status(404).json(buildApiResponse(404, 'NOT_FOUND'));
};
