/**
 * Chat Routes Tests
 * Tests for SSE chat streaming endpoint
 */

import request from 'supertest';
import express, { Express } from 'express';
import chatRouter from '../../routes/chat';
import * as ragServiceModule from '../../services/ragService';
import * as llmModule from '../../infra/llm';
import { RagError } from '../../types/rag';

// Mock modules
jest.mock('../../services/ragService');
jest.mock('../../infra/llm');
jest.mock('../../utils/logger', () => ({
  logger: {
    child: jest.fn(() => ({
      info: jest.fn(),
      debug: jest.fn(),
      error: jest.fn(),
      warn: jest.fn(),
    })),
    info: jest.fn(),
    debug: jest.fn(),
    error: jest.fn(),
    warn: jest.fn(),
  },
}));

describe('Chat Routes - POST /stream', () => {
  let app: Express;

  beforeEach(() => {
    app = express();
    app.use(express.json());
    app.use('/api/chat', chatRouter);
    jest.clearAllMocks();
  });

  describe('Validation', () => {
    it('should reject request without id', async () => {
      const response = await request(app)
        .post('/api/chat/stream')
        .send({
          question: 'What is the labor code?',
          history: [],
        });

      expect(response.status).toBe(400);
      expect(response.body.code).toBe('VALIDATION_ERROR');
    });

    it('should reject request without question', async () => {
      const response = await request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          history: [],
        });

      expect(response.status).toBe(400);
      expect(response.body.code).toBe('VALIDATION_ERROR');
    });

    it('should reject question that is too long', async () => {
      const longQuestion = 'a'.repeat(2001);
      const response = await request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          question: longQuestion,
        });

      expect(response.status).toBe(400);
      expect(response.body.code).toBe('VALIDATION_ERROR');
    });

    it('should reject empty question', async () => {
      const response = await request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          question: '',
        });

      expect(response.status).toBe(400);
      expect(response.body.code).toBe('VALIDATION_ERROR');
    });

    it('should accept valid request with optional history', async () => {
      const mockRagContext = {
        systemPrompt: 'System prompt',
        context: 'Context',
        documents: [],
        timing: { embeddingMs: 10, retrievalMs: 20 },
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockResolvedValue(mockRagContext);

      // Mock LLM stream
      async function* mockStream() {
        yield 'Hello ';
        yield 'world';
      }

      (llmModule.MammouthProvider as jest.Mock).mockImplementation(() => ({
        stream: jest.fn().mockReturnValue(mockStream()),
        getConfig: jest.fn().mockReturnValue({
          model: 'gpt-4.1',
          temperature: 0.7,
          maxTokens: 1000,
          timeoutMs: 30000,
          apiUrl: 'https://api.mammouth.ai',
        }),
      }));

      const response = await request(app)
        .post('/api/chat/stream')
        .set('Accept', 'text/event-stream')
        .send({
          id: 'req-123',
          question: 'What is the labor code?',
          history: [
            { role: 'user', content: 'Previous question' },
            { role: 'assistant', content: 'Previous answer' },
          ],
        });

      expect(response.status).toBe(200);
      expect(response.headers['content-type']).toContain('text/event-stream');
    });
  });

  describe('Successful streaming', () => {
    it('should stream multiple token events', async () => {
      const mockRagContext = {
        systemPrompt: 'System prompt',
        context: 'Context from documents',
        documents: [{ eli: 'eli1', chunk_id: 'chunk1', title: 'Doc', excerpt: 'Content' }],
        timing: { embeddingMs: 15, retrievalMs: 25 },
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockResolvedValue(mockRagContext);

      async function* mockStream() {
        yield 'Le ';
        yield 'code ';
        yield 'du ';
        yield 'travail';
      }

      (llmModule.MammouthProvider as jest.Mock).mockImplementation(() => ({
        stream: jest.fn().mockReturnValue(mockStream()),
        getConfig: jest.fn().mockReturnValue({
          model: 'gpt-4.1',
          temperature: 0.7,
          maxTokens: 1000,
          timeoutMs: 30000,
          apiUrl: 'https://api.mammouth.ai',
        }),
      }));

      const response = await request(app)
        .post('/api/chat/stream')
        .set('Accept', 'text/event-stream')
        .send({
          id: 'req-123',
          question: 'Parlez du code du travail',
        });

      expect(response.status).toBe(200);
      expect(response.text).toContain('type":"start"');
      expect(response.text).toContain('type":"token"');
      expect(response.text).toContain('Le');
      expect(response.text).toContain('code');
      expect(response.text).toContain('type":"end"');
      expect(response.text).toContain('fullText');
    });

    it('should include correct SSE headers', async () => {
      const mockRagContext = {
        systemPrompt: 'System',
        context: 'Context',
        documents: [],
        timing: { embeddingMs: 10, retrievalMs: 20 },
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockResolvedValue(mockRagContext);

      async function* mockStream() {
        yield 'Test';
      }

      (llmModule.MammouthProvider as jest.Mock).mockImplementation(() => ({
        stream: jest.fn().mockReturnValue(mockStream()),
        getConfig: jest.fn().mockReturnValue({
          model: 'gpt-4.1',
          temperature: 0.7,
          maxTokens: 1000,
          timeoutMs: 30000,
          apiUrl: 'https://api.mammouth.ai',
        }),
      }));

      const response = await request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          question: 'Question',
        });

      expect(response.headers['content-type']).toContain('text/event-stream');
      expect(response.headers['cache-control']).toBe('no-cache');
      expect(response.headers['connection']).toBe('keep-alive');
      expect(response.headers['x-accel-buffering']).toBe('no');
    });

    it('should include start event with correct metadata', (done) => {
      const mockRagContext = {
        systemPrompt: 'System',
        context: 'Context',
        documents: [],
        timing: { embeddingMs: 10, retrievalMs: 20 },
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockResolvedValue(mockRagContext);

      async function* mockStream() {
        yield 'Response';
      }

      (llmModule.MammouthProvider as jest.Mock).mockImplementation(() => ({
        stream: jest.fn().mockReturnValue(mockStream()),
        getConfig: jest.fn().mockReturnValue({
          model: 'gpt-4.1-nano',
          temperature: 0.7,
          maxTokens: 1000,
          timeoutMs: 30000,
          apiUrl: 'https://api.mammouth.ai',
        }),
      }));

      request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          question: 'Question',
        })
        .end((err, res) => {
          if (err) return done(err);

          const lines = res.text.split('\n\n');
          const startLine = lines.find((l) => l.includes('"type":"start"'));

          expect(startLine).toBeDefined();
          if (startLine) {
            const startEvent = JSON.parse(startLine.replace('data: ', ''));
            expect(startEvent.type).toBe('start');
            expect(startEvent.requestId).toBe('req-123');
            expect(startEvent.metadata.model).toBe('gpt-4.1-nano');
            expect(startEvent.metadata.topK).toBe(5);
          }

          done();
        });
    });

    it('should include end event with timing information', (done) => {
      const mockRagContext = {
        systemPrompt: 'System',
        context: 'Context',
        documents: [],
        timing: { embeddingMs: 45, retrievalMs: 89 },
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockResolvedValue(mockRagContext);

      async function* mockStream() {
        yield 'Final response';
      }

      (llmModule.MammouthProvider as jest.Mock).mockImplementation(() => ({
        stream: jest.fn().mockReturnValue(mockStream()),
        getConfig: jest.fn().mockReturnValue({
          model: 'gpt-4.1',
          temperature: 0.7,
          maxTokens: 1000,
          timeoutMs: 30000,
          apiUrl: 'https://api.mammouth.ai',
        }),
      }));

      request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          question: 'Question',
        })
        .end((err, res) => {
          if (err) return done(err);

          const lines = res.text.split('\n\n');
          const endLine = lines.find((l) => l.includes('"type":"end"'));

          expect(endLine).toBeDefined();
          if (endLine) {
            const endEvent = JSON.parse(endLine.replace('data: ', ''));
            expect(endEvent.type).toBe('end');
            expect(endEvent.fullText).toBe('Final response');
            expect(endEvent.timing.embeddingMs).toBe(45);
            expect(endEvent.timing.retrievalMs).toBe(89);
            expect(endEvent.timing.llmMs).toBeGreaterThanOrEqual(0);
          }

          done();
        });
    });
  });

  describe('Error handling', () => {
    it('should handle RAG pipeline embedding errors', async () => {
      const ragError: RagError = {
        stage: 'embedding',
        code: 'TIMEOUT',
        message: 'Embedding service timeout',
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockRejectedValue(ragError);

      const response = await request(app)
        .post('/api/chat/stream')
        .set('Accept', 'text/event-stream')
        .send({
          id: 'req-123',
          question: 'Question',
        });

      expect(response.status).toBe(200); // SSE always 200, error in event
      expect(response.text).toContain('"type":"error"');
      expect(response.text).toContain('TIMEOUT');
      expect(response.text).toContain('embedding');
    });

    it('should handle RAG pipeline retrieval errors', async () => {
      const ragError: RagError = {
        stage: 'retrieval',
        code: 'SEARCH_FAILED',
        message: 'Qdrant search failed',
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockRejectedValue(ragError);

      const response = await request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          question: 'Question',
        });

      expect(response.status).toBe(200);
      expect(response.text).toContain('"type":"error"');
      expect(response.text).toContain('SEARCH_FAILED');
      expect(response.text).toContain('retrieval');
    });

    it('should handle LLM stream errors gracefully', async () => {
      const mockRagContext = {
        systemPrompt: 'System',
        context: 'Context',
        documents: [],
        timing: { embeddingMs: 10, retrievalMs: 20 },
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockResolvedValue(mockRagContext);

      async function* mockStream() {
        yield 'Partial ';
        throw new Error('LLM service error');
      }

      (llmModule.MammouthProvider as jest.Mock).mockImplementation(() => ({
        stream: jest.fn().mockReturnValue(mockStream()),
        getConfig: jest.fn().mockReturnValue({
          model: 'gpt-4.1',
          temperature: 0.7,
          maxTokens: 1000,
          timeoutMs: 30000,
          apiUrl: 'https://api.mammouth.ai',
        }),
      }));

      const response = await request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          question: 'Question',
        });

      expect(response.status).toBe(200);
      expect(response.text).toContain('"type":"error"');
      expect(response.text).toContain('LLM_STREAM_ERROR');
      expect(response.text).toContain('LLM service error');
    });

    it('should send start event before RAG error', async () => {
      const ragError: RagError = {
        stage: 'embedding',
        code: 'TIMEOUT',
        message: 'Timeout',
      };

      (ragServiceModule.buildRagContext as jest.Mock).mockRejectedValue(ragError);

      const response = await request(app)
        .post('/api/chat/stream')
        .send({
          id: 'req-123',
          question: 'Question',
        });

      const lines = response.text.split('\n\n').filter((l) => l.trim());
      expect(lines[0]).toContain('"type":"start"');
      expect(lines[1]).toContain('"type":"error"');
    });
  });

  describe('GET /health', () => {
    it('should return health status', async () => {
      const response = await request(app).get('/api/chat/health');

      expect(response.status).toBe(200);
      expect(response.body.status).toBe('ok');
      expect(response.body.service).toBe('chat');
    });
  });
});
