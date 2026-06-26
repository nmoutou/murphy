/**
 * RAG Service Tests
 * Tests for buildRagContext and pipeline orchestration
 */

import { buildRagContext } from '../../services/ragService';
import * as embeddingModule from '../../infra/embedding';
import * as qdrantModule from '../../infra/qdrant';
import * as mongodbModule from '../../infra/mongodb';
import { RagError } from '../../types/rag';

// Mock modules
jest.mock('../../infra/embedding');
jest.mock('../../infra/qdrant');
jest.mock('../../infra/mongodb');
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

describe('RAG Service - buildRagContext', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Successful pipeline execution', () => {
    it('should build RAG context successfully with documents', async () => {
      const mockEmbedding = Array(768).fill(0.5);
      const mockDocuments = [
        {
          eli: 'eli123',
          chunk_id: 'chunk1',
          title: 'Test Document',
          excerpt: 'This is a test document.',
        },
      ];
      const mockSearchResults = [
        {
          id: '1',
          similarity: 0.95,
          payload: { eli: 'eli123', chunk_id: 'chunk1' },
        },
      ];

      // Setup mocks
      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => ({
        searchVectors: jest.fn().mockResolvedValue(mockSearchResults),
      }));

      (mongodbModule.fetchDocuments as jest.Mock).mockResolvedValue(mockDocuments);

      // Execute
      const result = await buildRagContext('What is the labor code?');

      // Assert
      expect(result).toBeDefined();
      expect(result.systemPrompt).toBeDefined();
      expect(result.context).toContain('Test Document');
      expect(result.documents).toEqual(mockDocuments);
      expect(result.timing.embeddingMs).toBeGreaterThanOrEqual(0);
      expect(result.timing.retrievalMs).toBeGreaterThanOrEqual(0);
    });

    it('should return default system prompt when not configured', async () => {
      process.env.SYSTEM_PROMPT = '';
      const mockEmbedding = Array(768).fill(0.5);
      const mockSearchResults: any[] = [];
      const mockDocuments: any[] = [];

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => ({
        searchVectors: jest.fn().mockResolvedValue(mockSearchResults),
      }));

      (mongodbModule.fetchDocuments as jest.Mock).mockResolvedValue(mockDocuments);

      const result = await buildRagContext('Test question');

      expect(result.systemPrompt).toContain('assistant juridique');
    });

    it('should handle empty search results gracefully', async () => {
      const mockEmbedding = Array(768).fill(0.5);
      const mockSearchResults: any[] = [];
      const mockDocuments: Array<any> = [];

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => ({
        searchVectors: jest.fn().mockResolvedValue(mockSearchResults),
      }));

      (mongodbModule.fetchDocuments as jest.Mock).mockResolvedValue(mockDocuments);

      const result = await buildRagContext('No matching documents?');

      expect(result.documents).toEqual([]);
      expect(result.context).toContain('No relevant documents');
    });

    it('should respect custom config (topK, systemPrompt)', async () => {
      const mockEmbedding = Array(768).fill(0.5);
      const customSystemPrompt = 'Custom prompt';
      const mockSearchResults = [
        {
          id: '1',
          similarity: 0.9,
          payload: { eli: 'eli1' },
        },
      ];
      const mockDocuments: Array<any> = [];

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      const mockQdrantClient = {
        searchVectors: jest.fn().mockResolvedValue(mockSearchResults),
      };
      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => mockQdrantClient);
      (mongodbModule.fetchDocuments as jest.Mock).mockResolvedValue(mockDocuments);

      const result = await buildRagContext('Question', {
        topK: 3,
        systemPrompt: customSystemPrompt,
      });

      expect(result.systemPrompt).toBe(customSystemPrompt);
      expect(mockQdrantClient.searchVectors).toHaveBeenCalledWith(mockEmbedding, 3);
    });
  });

  describe('Error handling', () => {
    it('should propagate embedding errors (RagError with stage=embedding)', async () => {
      const embeddingError: RagError = {
        stage: 'embedding',
        code: 'TIMEOUT',
        message: 'Embedding service timeout',
      };

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockRejectedValue(embeddingError),
      }));

      await expect(buildRagContext('Question')).rejects.toEqual(embeddingError);
    });

    it('should propagate retrieval errors (RagError with stage=retrieval)', async () => {
      const mockEmbedding = Array(768).fill(0.5);
      const retrievalError: RagError = {
        stage: 'retrieval',
        code: 'SEARCH_FAILED',
        message: 'Qdrant search failed',
      };

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => ({
        searchVectors: jest.fn().mockRejectedValue(retrievalError),
      }));

      await expect(buildRagContext('Question')).rejects.toEqual(retrievalError);
    });

    it('should propagate MongoDB fetch errors (RagError with stage=retrieval)', async () => {
      const mockEmbedding = Array(768).fill(0.5);
      const mockSearchResults = [
        {
          id: '1',
          similarity: 0.9,
          payload: { eli: 'eli1' },
        },
      ];
      const mongoError: RagError = {
        stage: 'retrieval',
        code: 'DB_FETCH_FAILED',
        message: 'Failed to fetch documents',
      };

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => ({
        searchVectors: jest.fn().mockResolvedValue(mockSearchResults),
      }));

      (mongodbModule.fetchDocuments as jest.Mock).mockRejectedValue(mongoError);

      await expect(buildRagContext('Question')).rejects.toEqual(mongoError);
    });
  });

  describe('Context string building', () => {
    it('should format multiple documents correctly', async () => {
      const mockEmbedding = Array(768).fill(0.5);
      const mockDocuments: Array<any> = [
        {
          eli: 'eli1',
          chunk_id: 'chunk1',
          title: 'Article 1',
          excerpt: 'First article content',
        },
        {
          eli: 'eli2',
          chunk_id: 'chunk2',
          title: 'Article 2',
          excerpt: 'Second article content',
        },
      ];
      const mockSearchResults = [
        { id: '1', similarity: 0.95, payload: { eli: 'eli1' } },
        { id: '2', similarity: 0.90, payload: { eli: 'eli2' } },
      ];

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => ({
        searchVectors: jest.fn().mockResolvedValue(mockSearchResults),
      }));

      (mongodbModule.fetchDocuments as jest.Mock).mockResolvedValue(mockDocuments);

      const result = await buildRagContext('Question');

      expect(result.context).toContain('[1]');
      expect(result.context).toContain('Article 1');
      expect(result.context).toContain('[2]');
      expect(result.context).toContain('Article 2');
    });

    it('should handle documents without titles or excerpts', async () => {
      const mockEmbedding = Array(768).fill(0.5);
      const mockDocuments: Array<any> = [
        {
          eli: 'eli1',
          chunk_id: 'chunk1',
        },
      ];
      const mockSearchResults = [
        { id: '1', similarity: 0.95, payload: { eli: 'eli1' } },
      ];

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => ({
        searchVectors: jest.fn().mockResolvedValue(mockSearchResults),
      }));

      (mongodbModule.fetchDocuments as jest.Mock).mockResolvedValue(mockDocuments);

      const result = await buildRagContext('Question');

      expect(result.context).toContain('Document 1');
      expect(result.context).toContain('No content available');
    });
  });

  describe('Timing metrics', () => {
    it('should capture timing for all stages', async () => {
      const mockEmbedding = Array(768).fill(0.5);
      const mockSearchResults = [
        { id: '1', similarity: 0.95, payload: { eli: 'eli1' } },
      ];
      const mockDocuments = [
        { eli: 'eli1', chunk_id: 'chunk1', title: 'Doc', excerpt: 'Content' },
      ];

      (embeddingModule.EmbeddingClient as jest.Mock).mockImplementation(() => ({
        embedText: jest.fn().mockResolvedValue(mockEmbedding),
      }));

      (qdrantModule.QdrantVectorClient as jest.Mock).mockImplementation(() => ({
        searchVectors: jest.fn().mockResolvedValue(mockSearchResults),
      }));

      (mongodbModule.fetchDocuments as jest.Mock).mockResolvedValue(mockDocuments);

      const result = await buildRagContext('Question');

      expect(result.timing.embeddingMs).toBeGreaterThanOrEqual(0);
      expect(result.timing.retrievalMs).toBeGreaterThanOrEqual(0);
      expect(typeof result.timing.embeddingMs).toBe('number');
      expect(typeof result.timing.retrievalMs).toBe('number');
    });
  });
});
