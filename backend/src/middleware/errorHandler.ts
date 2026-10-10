import { Request, Response, NextFunction } from 'express';
import { logger as rootLogger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';
import { HTTP_STATUS } from '../utils/httpStatus';
import { toErrorResponse } from '../utils/errorResponse';

const logger = rootLogger.child({ context: 'errorHandler' });

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
 * Une erreur du client marquée `expose` (JSON malformé, trop gros…) garde son 4xx ; une
 * `RagError` prend le statut de son code ; toute autre erreur est un 500. Un 4xx n'est
 * qu'un avertissement. Le message brut n'atteint jamais le client.
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

  const { status, code } = toErrorResponse(error);
  const details = { err: error, code, statusCode: status, path: req.path, method: req.method };
  if (isClientError(status)) logger.warn(details, 'Request refused');
  else logger.error(details, 'Request error');

  res.status(status).json(buildApiResponse(status, code));
};

export const notFoundHandler = (_req: Request, res: Response): void => {
  res.status(HTTP_STATUS.NOT_FOUND).json(buildApiResponse(HTTP_STATUS.NOT_FOUND, 'NOT_FOUND'));
};
