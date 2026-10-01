import { Request, Response, NextFunction } from 'express';
import { logger as rootLogger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';
import { HTTP_STATUS } from '../utils/httpStatus';

const logger = rootLogger.child({ context: 'errorHandler' });

const INTERNAL_ERROR_CODE = 'INTERNAL_ERROR';
const DEFAULT_BODY_ERROR_CODE = 'INVALID_REQUEST_BODY';

/** `type` d'erreur de body-parser → code renvoyé au client */
const BODY_ERROR_CODES: Readonly<Record<string, string>> = {
  'entity.parse.failed': 'INVALID_JSON',
  'entity.too.large': 'PAYLOAD_TOO_LARGE',
};

/** Erreur `http-errors` destinée au client (celles de body-parser) */
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

export const asyncHandler = (
  fn: (req: Request, res: Response, next: NextFunction) => Promise<void>
) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};

/**
 * Une erreur du client marquée `expose` (JSON malformé, trop gros…) garde son 4xx et
 * n'est qu'un avertissement ; toute autre erreur est un 500. Le message brut n'atteint
 * jamais le client.
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

export const notFoundHandler = (_req: Request, res: Response): void => {
  res.status(HTTP_STATUS.NOT_FOUND).json(buildApiResponse(HTTP_STATUS.NOT_FOUND, 'NOT_FOUND'));
};
