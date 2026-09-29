import { Request, Response, NextFunction } from 'express';
import { logger as rootLogger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';
import { HTTP_STATUS } from '../utils/httpStatus';

const logger = rootLogger.child({ context: 'errorHandler' });

const INTERNAL_ERROR_CODE = 'INTERNAL_ERROR';
const DEFAULT_BODY_ERROR_CODE = 'INVALID_REQUEST_BODY';

/** body-parser error `type` → the code answered to the client */
const BODY_ERROR_CODES: Readonly<Record<string, string>> = {
  'entity.parse.failed': 'INVALID_JSON',
  'entity.too.large': 'PAYLOAD_TOO_LARGE',
};

/** An `http-errors` error meant for the client (body-parser's): a 4xx `status` and `expose` */
interface ClientRequestError extends Error {
  readonly status: number;
  readonly expose: true;
  readonly type?: string;
}

const isClientError = (status: unknown): status is number =>
  typeof status === 'number'
  && status >= HTTP_STATUS.BAD_REQUEST
  && status < HTTP_STATUS.INTERNAL_SERVER_ERROR;

const isClientRequestError = (error: Error): error is ClientRequestError =>
  'status' in error && isClientError(error.status)
  && 'expose' in error && error.expose === true;

const sendClientRequestError = (error: ClientRequestError, req: Request, res: Response): void => {
  const code = (error.type && BODY_ERROR_CODES[error.type]) || DEFAULT_BODY_ERROR_CODE;
  logger.warn({
    err: error,
    type: error.type,
    code,
    statusCode: error.status,
    path: req.path,
    method: req.method,
  }, 'Invalid request body');

  res.status(error.status).json(buildApiResponse(error.status, code));
};

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
 * Global error handler middleware. An error the client caused and `http-errors` marks
 * `expose` (the JSON body parser's: malformed, too large…) keeps its 4xx status and is a
 * warning; any other error is an unexpected 500. The raw message never reaches the client.
 */
export const errorHandler = (
  error: Error,
  req: Request,
  res: Response,
  _next: NextFunction
): void => {
  if (isClientRequestError(error)) {
    sendClientRequestError(error, req, res);
    return;
  }

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
