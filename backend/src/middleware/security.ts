import helmet from 'helmet';
import { Request, Response } from 'express';
import rateLimit from 'express-rate-limit';
import cors from 'cors';
import { buildApiResponse } from '../utils/response';
import { config } from '../config';
import { HTTP_STATUS } from '../utils/httpStatus';


export const helm = helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", 'data:', 'https:'],
    },
  },
  crossOriginEmbedderPolicy: false,
});

export const limiter = rateLimit({
  windowMs: config.http.rateLimit.windowMs,
  limit: config.http.rateLimit.limit,
  handler: (_req: Request, res: Response) => {
    res.status(HTTP_STATUS.TOO_MANY_REQUESTS).json(buildApiResponse(HTTP_STATUS.TOO_MANY_REQUESTS, 'RATE_LIMIT_EXCEEDED'));
  },
  standardHeaders: true,
  legacyHeaders: false,
});

export const originParser = cors({
  origin: config.http.corsOrigins === false ? false : [...config.http.corsOrigins],
  credentials: true,
});
