/**
 * Error Handler Tests
 * `asyncHandler`, `errorHandler` and `notFoundHandler`, mounted on a real Express app
 */

import express, { Express } from 'express';
import request from 'supertest';
import { asyncHandler, errorHandler, notFoundHandler } from '../../middleware/errorHandler';
import { logger } from '../../utils/logger';
import { MAX_REQUEST_BODY_BYTES } from '../../utils/requestLimits';

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
  app.get('/status-without-expose', () => {
    throw Object.assign(new Error('Internal failure carrying a status'), { status: 404 });
  });
  app.post('/echo', express.json({ limit: MAX_REQUEST_BODY_BYTES }), (req, res) => {
    res.json(req.body);
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

  it('keeps an internal error carrying a status without `expose` a 500', async () => {
    const response = await request(app).get('/status-without-expose');

    expect(response.status).toBe(500);
    expect(response.body.status).toEqual({ code: 500, message: 'INTERNAL_ERROR' });
  });
});

describe('errorHandler, request body errors', () => {
  it('answers a malformed JSON body with a 400 INVALID_JSON, logged as a warning', async () => {
    const response = await request(app)
      .post('/echo')
      .set('Content-Type', 'application/json')
      .send('{"messages":');

    expect(response.status).toBe(400);
    expect(response.body.status).toEqual({ code: 400, message: 'INVALID_JSON' });
    expect(logger.warn).toHaveBeenCalled();
    expect(logger.error).not.toHaveBeenCalled();
  });

  it('answers a body over the size limit with a 413 PAYLOAD_TOO_LARGE', async () => {
    const oversizedBody = JSON.stringify('x'.repeat(MAX_REQUEST_BODY_BYTES + 1));

    const response = await request(app)
      .post('/echo')
      .set('Content-Type', 'application/json')
      .send(oversizedBody);

    expect(response.status).toBe(413);
    expect(response.body.status).toEqual({ code: 413, message: 'PAYLOAD_TOO_LARGE' });
  });
});

describe('notFoundHandler', () => {
  it('answers an unknown route with a 404 NOT_FOUND', async () => {
    const response = await request(app).get('/nowhere');

    expect(response.status).toBe(404);
    expect(response.body.status).toEqual({ code: 404, message: 'NOT_FOUND' });
  });
});
