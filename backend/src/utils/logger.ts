import pino from 'pino';
import { config } from '../config';

/**
 * Pino logger configuration
 * Development: pretty print with colors
 * Production: JSON format for log aggregation
 */
export const logger = pino({
  level: config.server.logLevel,
  
  // Pretty print in development
  transport: !config.server.isProduction
    ? {
        target: 'pino-pretty',
        options: {
          colorize: true,
          translateTime: 'SYS:standard',
          ignore: 'pid,hostname',
        },
      }
    : undefined,

  // Base fields
  base: {
    env: config.server.nodeEnv,
  },

  // Timestamp format
  timestamp: pino.stdTimeFunctions.isoTime,

  // Error serialization
  serializers: {
    err: pino.stdSerializers.err,
    req: pino.stdSerializers.req,
    res: pino.stdSerializers.res,
  },
});
