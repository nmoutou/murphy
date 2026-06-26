import dotenv from 'dotenv';
import http from 'http';
import { WebSocketServer } from 'ws';
import app from './app';
import logger from './utils/logger';
import { initMongoClient, closeMongoClient } from './infra/mongodb';
import { registerChatWebSocket } from './routes/chatWebSocket';
import { checkEnvironment } from './utils/configWarnings';

dotenv.config();

const PORT = process.env.PORT || 5000;

const server = http.createServer(app);

const wss = new WebSocketServer({ server, path: '/api/v1/chat/ws' });
registerChatWebSocket(wss);

async function start() {
  checkEnvironment();
  logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);

  await initMongoClient();
  logger.info('All infrastructure initialized successfully');

  await new Promise<void>((resolve) => server.listen(PORT, resolve));
  logger.info(`Server started on http://localhost:${PORT}`);
}

start().catch((error) => {
  logger.error({ err: error }, 'Failed to start server');
  process.exit(1);
});

/**
 * Graceful shutdown handler
 */
const gracefulShutdown = async (signal: string) => {
  logger.info(`${signal} signal received: closing HTTP server`);

  server.close(async (err) => {
    if (err) {
      logger.error({ err }, 'Error during server shutdown');
      process.exit(1);
    }

    logger.info('HTTP server closed');

    try {
      await closeMongoClient();
    } catch (error) {
      logger.error({ err: error }, 'Error closing MongoDB connection');
    }

    logger.info('Graceful shutdown completed');
    process.exit(0);
  });

  // Force shutdown after 10 seconds
  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, 10000);
};

// Handle shutdown signals
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

// Handle uncaught errors
process.on('uncaughtException', (error: Error) => {
  logger.error({ err: error }, 'Uncaught exception');
  gracefulShutdown('UNCAUGHT_EXCEPTION');
});

process.on('unhandledRejection', (reason: unknown) => {
  logger.error({ err: reason }, 'Unhandled rejection');
  gracefulShutdown('UNHANDLED_REJECTION');
});
