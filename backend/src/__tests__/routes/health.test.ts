/**
 * Health Routes Tests
 * Global status derived from the TEI, Qdrant and MongoDB checks, over a mocked `fetch` and ping
 */

import express, { Express } from 'express';
import request from 'supertest';
import healthRouter from '../../routes/health';

const mockPing = jest.fn();

jest.mock('../../infra/clients', () => ({
  getInfraClients: () => ({ mongo: { getDb: () => ({ admin: () => ({ ping: mockPing }) }) } }),
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const HTTP_OK = 200;
const HTTP_SERVER_ERROR = 500;
const HTTP_SERVICE_UNAVAILABLE = 503;

/** Answers the TEI (`/health`) and Qdrant (`/healthz`) checks with the given HTTP statuses */
const mockHttpServices = (teiStatus: number, qdrantStatus: number): void => {
  jest.spyOn(global, 'fetch').mockImplementation(async (url) => {
    const status = String(url).endsWith('/healthz') ? qdrantStatus : teiStatus;
    return new Response(null, { status });
  });
};

let app: Express;

beforeEach(() => {
  app = express();
  app.use('/api/v1/health', healthRouter);
  mockPing.mockResolvedValue({ ok: 1 });
});

describe('GET /api/v1/health', () => {
  it('reports ok with the latency of each service when all are up', async () => {
    mockHttpServices(HTTP_OK, HTTP_OK);

    const response = await request(app).get('/api/v1/health');

    expect(response.status).toBe(HTTP_OK);
    expect(response.body.data.status).toBe('ok');
    for (const service of ['tei', 'qdrant', 'mongodb']) {
      expect(response.body.data.services[service]).toEqual({ status: 'ok', latencyMs: expect.any(Number) });
    }
  });

  it('reports degraded with a 503 when one service is down', async () => {
    mockHttpServices(HTTP_SERVER_ERROR, HTTP_OK);

    const response = await request(app).get('/api/v1/health');

    expect(response.status).toBe(HTTP_SERVICE_UNAVAILABLE);
    expect(response.body.status.message).toBe('UPSTREAM_UNAVAILABLE');
    expect(response.body.data.status).toBe('degraded');
    expect(response.body.data.services.tei).toMatchObject({ status: 'down', message: 'HTTP 500' });
  });

  it('reports down when two services are down', async () => {
    jest.spyOn(global, 'fetch').mockRejectedValue(new Error('connect ECONNREFUSED'));
    mockPing.mockRejectedValue(new Error('MongoDB unreachable'));

    const response = await request(app).get('/api/v1/health');

    expect(response.status).toBe(HTTP_SERVICE_UNAVAILABLE);
    expect(response.body.data.status).toBe('down');
    expect(response.body.data.services.mongodb).toMatchObject({ status: 'down', message: 'MongoDB unreachable' });
  });
});

describe('GET /api/v1/health/services', () => {
  it('answers like /', async () => {
    mockHttpServices(HTTP_OK, HTTP_OK);

    const response = await request(app).get('/api/v1/health/services');

    expect(response.status).toBe(HTTP_OK);
    expect(Object.keys(response.body.data.services)).toEqual(['tei', 'qdrant', 'mongodb']);
  });
});
