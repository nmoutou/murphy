import express, { Express } from 'express';
import request from 'supertest';
import searchRouter from '../../routes/search';
import { searchDocuments } from '../../services/searchService';
import { errorHandler } from '../../middleware/errorHandler';
import { RagError } from '../../types/rag';

jest.mock('../../services/searchService', () => ({ searchDocuments: jest.fn() }));
jest.mock('../../middleware/searchRateLimiter', () => ({
  searchRateLimiter: (_req: unknown, _res: unknown, next: () => void) => next(),
}));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const QUESTION = 'article L1234-5 licenciement';
const PAGE = { page: 2, pageCount: 10, pageSize: 10, pageSizes: [10, 25, 50], contextBudget: 100_000, results: [] };

let app: Express;

beforeEach(() => {
  app = express();
  app.use(express.json());
  app.use('/api/v1/search', searchRouter);
  app.use(errorHandler);
});

describe('POST /api/v1/search, validation', () => {
  it.each([
    ['no question', {}, 'question'],
    ['a blank question', { question: '   ' }, 'question'],
    ['a page below 1', { question: QUESTION, page: 0 }, 'page'],
    ['a fractional page', { question: QUESTION, page: 1.5 }, 'page'],
    ['a page size outside the allowed ones', { question: QUESTION, pageSize: 30 }, 'pageSize'],
    ['a page size that is not a number', { question: QUESTION, pageSize: '25' }, 'pageSize'],
    ['a body that is not an object', [QUESTION], 'body'],
  ])('rejects %s with a 400 naming the field', async (_case, body, field) => {
    const response = await request(app).post('/api/v1/search').send(body);

    expect(response.status).toBe(400);
    expect(response.body.status.message).toBe('VALIDATION_ERROR');
    expect(response.body.errors).toEqual([expect.objectContaining({ field })]);
    expect(searchDocuments).not.toHaveBeenCalled();
  });

  it('names the allowed page sizes', async () => {
    const response = await request(app).post('/api/v1/search').send({ question: QUESTION, pageSize: 30 });

    expect(response.body.errors).toEqual([{ field: 'pageSize', message: 'must be one of 10, 25, 50' }]);
  });

  it('never echoes the question in a validation error', async () => {
    const response = await request(app).post('/api/v1/search').send({ question: QUESTION, page: 'deux' });

    expect(JSON.stringify(response.body)).not.toContain(QUESTION);
  });
});

describe('POST /api/v1/search', () => {
  it('answers the page in the response envelope', async () => {
    jest.mocked(searchDocuments).mockResolvedValue(PAGE);

    const response = await request(app).post('/api/v1/search').send({ question: QUESTION, page: 2, pageSize: 25 });

    expect(response.status).toBe(200);
    expect(response.body).toMatchObject({ status: { code: 200, message: 'OK' }, data: PAGE });
    expect(searchDocuments).toHaveBeenCalledWith({ question: QUESTION, page: 2, pageSize: 25 });
  });

  it('asks for the first page at the first allowed size when neither is given', async () => {
    jest.mocked(searchDocuments).mockResolvedValue({ ...PAGE, page: 1 });

    await request(app).post('/api/v1/search').send({ question: QUESTION });

    expect(searchDocuments).toHaveBeenCalledWith({ question: QUESTION, page: 1, pageSize: 10 });
  });

  it.each([
    [new RagError('request', 'PAGE_OUT_OF_RANGE', 'Page 11'), 400, 'PAGE_OUT_OF_RANGE'],
    [new RagError('embedding', 'TIMEOUT', 'Failed to generate embeddings: timeout'), 504, 'TIMEOUT'],
    [new RagError('retrieval', 'SEARCH_FAILED', 'Failed to search OpenSearch: ECONNREFUSED'), 502, 'SEARCH_FAILED'],
    [new Error('boom'), 500, 'INTERNAL'],
  ])('answers a failure with its status and code only: %s', async (error, status, code) => {
    jest.mocked(searchDocuments).mockRejectedValue(error);

    const response = await request(app).post('/api/v1/search').send({ question: QUESTION });

    expect(response.status).toBe(status);
    expect(response.body.status).toEqual({ code: status, message: code });
    expect(response.body.data).toBeUndefined();
    expect(JSON.stringify(response.body)).not.toContain(error.message);
  });
});
