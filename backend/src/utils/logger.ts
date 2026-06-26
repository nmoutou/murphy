import pino from 'pino';

const isDevelopment = process.env.NODE_ENV !== 'production';

/**
 * Pino logger configuration
 * Development: pretty print with colors
 * Production: JSON format for log aggregation
 */
export const logger = pino({
  level: process.env.LOG_LEVEL || (isDevelopment ? 'debug' : 'info'),
  
  // Pretty print in development
  transport: isDevelopment
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
    env: process.env.NODE_ENV || 'development',
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

/**
 * Create child logger with additional context
 */
export const createLogger = (context: Record<string, any>) => {
  return logger.child(context);
};

export default logger;
