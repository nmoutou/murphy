/**
 * Stream Rate Limiter
 * Dedicated rate limiter for the /api/chat/stream endpoint
 * More restrictive than the global rate limiter to protect against abuse
 */

import rateLimit from 'express-rate-limit';
import { Request, Response } from 'express';
import { logger } from '../utils/logger';
import { buildApiResponse } from '../utils/response';

/**
 * Create a rate limiter specifically for SSE streaming endpoint
 * Default: 10 requests per minute per IP
 * Configurable via environment variables
 */
export const streamRateLimiter = rateLimit({
  windowMs: parseInt(process.env.STREAM_RATE_LIMIT_WINDOW_MS || '60000', 10), // 1 minute
  max: parseInt(process.env.STREAM_RATE_LIMIT_MAX || '10', 10), // 10 requests max
  
  // Custom key generator: respect X-Forwarded-For for proxy scenarios
  keyGenerator: (req: Request) => {
    // Check for X-Forwarded-For header (used by reverse proxies)
    const forwardedFor = req.headers['x-forwarded-for'];
    if (forwardedFor) {
      const ips = Array.isArray(forwardedFor) ? forwardedFor[0] : forwardedFor.split(',')[0];
      return ips.trim();
    }
    // Fallback to socket remote address
    return req.socket.remoteAddress || 'unknown';
  },

  // Custom handler for rate limit exceeded
  handler: (req: Request, res: Response, _next) => {
    const clientIp = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
    logger.warn(
      { ip: clientIp, endpoint: req.path },
      'Stream rate limit exceeded'
    );

    res.status(429).json(buildApiResponse(429, 'STREAM_RATE_LIMIT_EXCEEDED'));
  },

  // Standard headers
  standardHeaders: true,
  legacyHeaders: false,

  // Skip health check endpoint if needed
  skip: (req: Request) => {
    // Don't rate limit health checks if configured
    const skipHealthCheck = process.env.STREAM_RATE_LIMIT_SKIP_HEALTH === 'true';
    return skipHealthCheck && req.path === '/health';
  },
});
