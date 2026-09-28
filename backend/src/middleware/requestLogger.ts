import pinoHttp from 'pino-http';
import { logger } from '../utils/logger';
import { HTTP_STATUS } from '../utils/httpStatus';

/**
 * HTTP request logging middleware using Pino
 * Logs all incoming requests and responses
 */
export const requestLogger = pinoHttp({
  logger,
  
  // Custom log message
  customLogLevel: function (_req, res, _err) {
    if (res.statusCode >= HTTP_STATUS.INTERNAL_SERVER_ERROR) return 'error';
    if (res.statusCode >= HTTP_STATUS.BAD_REQUEST) return 'warn';
    return 'info';
  },

  // Custom request logging
  customSuccessMessage: function (req, _res) {
    return `${req.method} ${req.url} completed`;
  },

  customErrorMessage: function (req, _res, err) {
    return `${req.method} ${req.url} failed: ${err.message}`;
  },

  // Custom attributes to log
  customAttributeKeys: {
    req: 'request',
    res: 'response',
    err: 'error',
    responseTime: 'duration',
  },

  // Serialize request and response
  serializers: {
    req: (req) => ({
      method: req.method,
      url: req.url,
      path: req.path,
      parameters: req.params,
      query: req.query,
      headers: {
        host: req.headers.host,
        userAgent: req.headers['user-agent'],
      },
    }),
    res: (res) => ({
      statusCode: res.statusCode,
    }),
  },
});
