/**
 * Error Handler Tests
 * `asyncHandler`, `errorHandler` and `notFoundHandler`, mounted on a real Express app
 */

import express, { Express } from 'express';
import request from 'supertest';
import { asyncHandler, errorHandler, notFoundHandler } from '../../middleware/errorHandler';

jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

let app: Express;

beforeEach(() => {
  app = express();
  app.get('/ok', asyncHandler(async (_req, res) => {
    res.json({ isOk: true });
  }));
  app.get('/async-failure', asyncHandler(async () => {
    throw new Error('Async failure');
  }));
  app.get('/sync-failure', () => {
    throw new Error('Sync failure');
  });
  app.use(notFoundHandler);
  app.use(errorHandler);
});

describe('asyncHandler', () => {
  it('lets a successful handler answer', async () => {
    const response = await request(app).get('/ok');

    expect(response.status).toBe(200);
    expect(response.body).toEqual({ isOk: true });
  });

  it('forwards a rejected promise to the error handler', async () => {
    const response = await request(app).get('/async-failure');

    expect(response.status).toBe(500);
    expect(response.body.status).toEqual({ code: 500, message: 'INTERNAL_ERROR' });
  });
});

describe('errorHandler', () => {
  it('answers any thrown error with a 500 INTERNAL_ERROR', async () => {
    const response = await request(app).get('/sync-failure');

    expect(response.status).toBe(500);
    expect(response.body.status).toEqual({ code: 500, message: 'INTERNAL_ERROR' });
  });
});

describe('notFoundHandler', () => {
  it('answers an unknown route with a 404 NOT_FOUND', async () => {
    const response = await request(app).get('/nowhere');

    expect(response.status).toBe(404);
    expect(response.body.status).toEqual({ code: 404, message: 'NOT_FOUND' });
  });
});
