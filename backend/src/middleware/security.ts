import helmet from 'helmet';
import { Request, Response } from 'express';
import rateLimit from 'express-rate-limit';
import { buildApiResponse } from '../utils/response';
import cors from 'cors';

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
})

// Rate limiting: configurable via RATE_LIMIT_WINDOW_MS / RATE_LIMIT_MAX
export const limiter = rateLimit({
  windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS || '900000', 10),
  max: parseInt(process.env.RATE_LIMIT_MAX || '100', 10),
  handler: (_req: Request, res: Response) => {
    res.status(429).json(buildApiResponse(429, 'RATE_LIMIT_EXCEEDED'));
  },
  standardHeaders: true,
  legacyHeaders: false,
});


export const originParser = cors({
  origin: process.env.CORS_ORIGIN ? process.env.CORS_ORIGIN.split(',') : false,
  credentials: true,
})