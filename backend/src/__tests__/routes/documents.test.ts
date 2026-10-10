import express, { Express } from 'express';
import request from 'supertest';
import documentsRouter from '../../routes/documents';
import { readDocument } from '../../services/documentService';
import { errorHandler } from '../../middleware/errorHandler';
import { RagError } from '../../types/rag';

jest.mock('../../services/documentService', () => ({ readDocument: jest.fn() }));
jest.mock('../../utils/logger', () => {
  const silentLogger = { info: jest.fn(), debug: jest.fn(), warn: jest.fn(), error: jest.fn(), child: () => silentLogger };
  return { logger: silentLogger };
});

const DOCUMENT = { identifier: 'JURITEXT000048123456', title: 'Cour de cassation, …', content: 'LA COUR…' };

let app: Express;

beforeEach(() => {
  app = express();
  app.use('/api/v1/documents', documentsRouter);
  app.use(errorHandler);
});

describe('GET /api/v1/documents/:identifier', () => {
  it('answers the document in the response envelope', async () => {
    jest.mocked(readDocument).mockResolvedValue(DOCUMENT);

    const response = await request(app).get(`/api/v1/documents/${DOCUMENT.identifier}`);

    expect(response.status).toBe(200);
    expect(response.body).toMatchObject({ status: { code: 200, message: 'OK' }, data: DOCUMENT });
    expect(readDocument).toHaveBeenCalledWith(DOCUMENT.identifier);
  });

  it.each([
    [new RagError('request', 'DOCUMENT_NOT_FOUND', 'No document has the identifier X'), 404, 'DOCUMENT_NOT_FOUND'],
    [new RagError('retrieval', 'TIMEOUT', 'Failed to fetch a document from MongoDB: timeout'), 504, 'TIMEOUT'],
    [new RagError('retrieval', 'DB_FETCH_FAILED', 'Failed to fetch a document from MongoDB: reset'), 502, 'DB_FETCH_FAILED'],
  ])('answers a failure with its status and code only: %s', async (error, status, code) => {
    jest.mocked(readDocument).mockRejectedValue(error);

    const response = await request(app).get('/api/v1/documents/X');

    expect(response.status).toBe(status);
    expect(response.body.status).toEqual({ code: status, message: code });
    expect(JSON.stringify(response.body)).not.toContain(error.message);
  });
});
