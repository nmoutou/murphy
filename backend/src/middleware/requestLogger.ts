import pinoHttp from 'pino-http';
import { logger } from '../utils/logger';
import { HTTP_STATUS } from '../utils/httpStatus';

export const requestLogger = pinoHttp({
  logger,
  
  customLogLevel: function (_req, res, _err) {
    if (res.statusCode >= HTTP_STATUS.INTERNAL_SERVER_ERROR) return 'error';
    if (res.statusCode >= HTTP_STATUS.BAD_REQUEST) return 'warn';
    return 'info';
  },

  customSuccessMessage: function (req, _res) {
    return `${req.method} ${req.url} completed`;
  },

  customErrorMessage: function (req, _res, err) {
    return `${req.method} ${req.url} failed: ${err.message}`;
  },

  customAttributeKeys: {
    req: 'request',
    res: 'response',
    err: 'error',
    responseTime: 'duration',
  },

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
