/**
 * Health Check Routes
 * Verifies availability of core services: TEI, Qdrant, MongoDB
 */

import express, { Request, Response } from 'express';
import { logger as rootLogger } from '../utils/logger';
import { getMongoDb } from '../infra/mongodb';
import { asyncHandler } from '../middleware/errorHandler';
import { buildApiResponse } from '../utils/response';

const logger = rootLogger.child({ context: 'healthRoutes' });
const router = express.Router();

/**
 * Service health status
 */
interface ServiceHealth {
  status: 'ok' | 'down';
  message?: string;
}

/**
 * Generic HTTP service health check
 */
async function checkHttpService(name: string, url: string, timeoutMs = 3000): Promise<ServiceHealth> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(url, { method: 'GET', signal: controller.signal });
    clearTimeout(timeoutId);

    if (response.ok) {
      logger.debug({ service: name, url }, `${name} health check OK`);
      return { status: 'ok' };
    }

    logger.warn({ service: name, url, status: response.status }, `${name} health check failed`);
    return { status: 'down', message: `HTTP ${response.status}` };
  } catch (error) {
    clearTimeout(timeoutId);
    const message = error instanceof Error ? error.message : 'Unknown error';
    logger.warn({ service: name, url, error: message }, `${name} health check error`);
    return { status: 'down', message };
  }
}

const checkTei = () =>
  checkHttpService('tei', `${process.env.EMBEDDING_SERVICE_URL || 'http://embedding-service:80'}/health`);

const checkQdrant = () =>
  checkHttpService('qdrant', `${process.env.QDRANT_URL || 'http://qdrant:6333'}/healthz`);

/**
 * Check MongoDB health
 * Attempts admin ping operation
 */
async function checkMongoDB(): Promise<ServiceHealth> {
  const timeoutMs = 3000;

  try {
    const mongoDb = await getMongoDb();

    // Use Promise.race to enforce timeout
    await Promise.race([
      mongoDb.admin().ping(),
      new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error('MongoDB ping timeout')), timeoutMs)
      ),
    ]);

    logger.debug({ service: 'mongodb' }, 'MongoDB health check OK');
    return { status: 'ok' };
  } catch (error) {
    const message = error instanceof Error ? error.message : 'Unknown error';
    logger.warn({ service: 'mongodb', error: message }, 'MongoDB health check error');
    return { status: 'down', message };
  }
}

async function withLatency<T>(fn: () => Promise<T>): Promise<T & { latencyMs: number }> {
  const start = Date.now();
  const result = await fn();
  return { ...result, latencyMs: Date.now() - start };
}

function resolveGlobalHealth(services: ServiceHealth[]) {
  const downCount = services.filter((s) => s.status === 'down').length;
  const globalStatus = downCount === 0 ? 'ok' : downCount >= 2 ? 'down' : 'degraded';
  const httpStatus = globalStatus === 'ok' ? 200 : 503;
  const statusMsg = globalStatus === 'ok' ? 'OK' : 'UPSTREAM_UNAVAILABLE';
  return { globalStatus, httpStatus, statusMsg };
}

/**
 * GET /api/v1/health
 * Status logic: "ok" = all up, "degraded" = 1 down, "down" = 2+ down
 */
router.get(
  '/',
  asyncHandler(async (_req: Request, res: Response) => {
    const [tei, qdrant, mongodb] = await Promise.all([checkTei(), checkQdrant(), checkMongoDB()]);
    const { globalStatus, httpStatus, statusMsg } = resolveGlobalHealth([tei, qdrant, mongodb]);
    res.status(httpStatus).json(
      buildApiResponse(httpStatus, statusMsg, { status: globalStatus, services: { tei, qdrant, mongodb } })
    );
  })
);

/**
 * GET /api/v1/health/services
 * Same as / with measured latency per service
 */
router.get(
  '/services',
  asyncHandler(async (_req: Request, res: Response) => {
    const [tei, qdrant, mongodb] = await Promise.all([
      withLatency(checkTei),
      withLatency(checkQdrant),
      withLatency(checkMongoDB),
    ]);
    const { globalStatus, httpStatus, statusMsg } = resolveGlobalHealth([tei, qdrant, mongodb]);
    res.status(httpStatus).json(
      buildApiResponse(httpStatus, statusMsg, { status: globalStatus, services: { tei, qdrant, mongodb } })
    );
  })
);

export default router;
