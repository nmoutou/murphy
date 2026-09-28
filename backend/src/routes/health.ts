/**
 * Health Check Routes
 * Verifies availability of core services: TEI, Qdrant, MongoDB
 */

import express, { Request, Response } from 'express';
import { logger as rootLogger } from '../utils/logger';
import { getInfraClients } from '../infra/clients';
import { asyncHandler } from '../middleware/errorHandler';
import { buildApiResponse } from '../utils/response';
import { config } from '../config';
import { HTTP_STATUS } from '../utils/httpStatus';

const logger = rootLogger.child({ context: 'healthRoutes' });
const router = express.Router();

/**
 * Service health status
 */
interface ServiceHealth {
  status: 'ok' | 'down';
  message?: string;
}

type GlobalStatus = 'ok' | 'degraded' | 'down';

interface GlobalHealth {
  globalStatus: GlobalStatus;
  httpStatus: number;
  statusMsg: string;
}

const HEALTH_CHECK_TIMEOUT_MS = 3000;
const MIN_DOWN_FOR_GLOBAL_DOWN = 2;

/**
 * Generic HTTP service health check
 */
async function checkHttpService(name: string, url: string): Promise<ServiceHealth> {
  try {
    const response = await fetch(url, { method: 'GET', signal: AbortSignal.timeout(HEALTH_CHECK_TIMEOUT_MS) });

    if (response.ok) {
      logger.debug({ service: name, url }, `${name} health check OK`);
      return { status: 'ok' };
    }

    logger.warn({ service: name, url, status: response.status }, `${name} health check failed`);
    return { status: 'down', message: `HTTP ${response.status}` };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    logger.warn({ service: name, url, error: message }, `${name} health check error`);
    return { status: 'down', message };
  }
}

const checkTei = () =>
  checkHttpService('tei', `${config.embedding.serviceUrl}/health`);

const checkQdrant = () =>
  checkHttpService('qdrant', `${config.qdrant.url}/healthz`);

/**
 * Pings MongoDB, giving up after `HEALTH_CHECK_TIMEOUT_MS`
 */
async function pingMongoDB(): Promise<void> {
  const mongoDb = getInfraClients().mongo.getDb();
  let timeoutId: NodeJS.Timeout | undefined;
  const timeout = new Promise<never>((_, reject) => {
    timeoutId = setTimeout(() => reject(new Error('MongoDB ping timeout')), HEALTH_CHECK_TIMEOUT_MS);
  });

  try {
    await Promise.race([mongoDb.admin().ping(), timeout]);
  } finally {
    clearTimeout(timeoutId);
  }
}

async function checkMongoDB(): Promise<ServiceHealth> {
  try {
    await pingMongoDB();
    logger.debug({ service: 'mongodb' }, 'MongoDB health check OK');
    return { status: 'ok' };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    logger.warn({ service: 'mongodb', error: message }, 'MongoDB health check error');
    return { status: 'down', message };
  }
}

async function measureLatency(check: () => Promise<ServiceHealth>): Promise<ServiceHealth & { latencyMs: number }> {
  const start = Date.now();
  const health = await check();
  return { ...health, latencyMs: Date.now() - start };
}

function resolveGlobalHealth(services: ServiceHealth[]): GlobalHealth {
  const downCount = services.filter((service) => service.status === 'down').length;
  if (downCount === 0) return { globalStatus: 'ok', httpStatus: HTTP_STATUS.OK, statusMsg: 'OK' };

  const globalStatus = downCount >= MIN_DOWN_FOR_GLOBAL_DOWN ? 'down' : 'degraded';
  return { globalStatus, httpStatus: HTTP_STATUS.SERVICE_UNAVAILABLE, statusMsg: 'UPSTREAM_UNAVAILABLE' };
}

/**
 * GET /api/v1/health (and its alias /api/v1/health/services)
 * Per-service status and latency. "ok" = all up, "degraded" = 1 down, "down" = 2+ down
 */
router.get(
  ['/', '/services'],
  asyncHandler(async (_req: Request, res: Response) => {
    const [tei, qdrant, mongodb] = await Promise.all([
      measureLatency(checkTei),
      measureLatency(checkQdrant),
      measureLatency(checkMongoDB),
    ]);
    const { globalStatus, httpStatus, statusMsg } = resolveGlobalHealth([tei, qdrant, mongodb]);
    res.status(httpStatus).json(
      buildApiResponse(httpStatus, statusMsg, { status: globalStatus, services: { tei, qdrant, mongodb } })
    );
  })
);

export default router;
