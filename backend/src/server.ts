import http from 'http';
import app from './app';
import { logger } from './utils/logger';
import { config, environmentReport } from './config';
import { initInfraClients, closeInfraClients } from './infra/clients';
import { attachChatWebSocket } from './routes/chatWebSocket';
import { checkEnvironment } from './utils/configWarnings';

/** Passé ce délai, un arrêt qui attend encore des connexions est forcé */
const FORCED_SHUTDOWN_DELAY_MS = 10_000;

const server = http.createServer(app);

attachChatWebSocket({ server, allowedOrigins: config.http.corsOrigins });

const start = async () => {
  checkEnvironment(environmentReport);
  logger.info(`Environment: ${config.server.nodeEnv}`);

  await initInfraClients(config);
  logger.info('All infrastructure initialized successfully');

  await new Promise<void>((resolve) => server.listen(config.server.port, resolve));
  logger.info(`Server started on http://localhost:${config.server.port}`);
};

start().catch((error) => {
  logger.error({ err: error }, 'Failed to start server');
  process.exit(1);
});

const gracefulShutdown = async (signal: string) => {
  logger.info(`${signal} signal received: closing HTTP server`);

  server.close(async (err) => {
    if (err) {
      logger.error({ err }, 'Error during server shutdown');
      process.exit(1);
    }

    logger.info('HTTP server closed');

    await closeInfraClients();

    logger.info('Graceful shutdown completed');
    process.exit(0);
  });

  setTimeout(() => {
    logger.error('Forced shutdown after timeout');
    process.exit(1);
  }, FORCED_SHUTDOWN_DELAY_MS);
};

process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));
process.on('SIGINT', () => gracefulShutdown('SIGINT'));

process.on('uncaughtException', (error: Error) => {
  logger.error({ err: error }, 'Uncaught exception');
  gracefulShutdown('UNCAUGHT_EXCEPTION');
});

process.on('unhandledRejection', (reason: unknown) => {
  logger.error({ err: reason }, 'Unhandled rejection');
  gracefulShutdown('UNHANDLED_REJECTION');
});
