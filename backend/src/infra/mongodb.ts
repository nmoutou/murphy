/**
 * MongoDB Client
 * Manages connection lifecycle and document fetching
 */

import { MongoClient, Db, MongoClientOptions } from 'mongodb';
import { logger } from '../utils/logger';
import { RagError, Document } from '../types/rag';

export class MongoDbClient {
  private client: MongoClient | null = null;
  private db: Db | null = null;

  async connect(): Promise<void> {
    if (this.client) {
      logger.info('MongoDB client already initialized');
      return;
    }

    const startTime = Date.now();

    try {
      const mongoUri = process.env.MONGODB_URI || '';
      const timeoutMs = parseInt(process.env.MONGODB_TIMEOUT || '10000', 10);

      const options: MongoClientOptions = {
        serverSelectionTimeoutMS: timeoutMs,
        connectTimeoutMS: timeoutMs,
        socketTimeoutMS: timeoutMs,
        retryWrites: true,
        maxPoolSize: 10,
      };

      const sanitizedUri = mongoUri.replace(/\/\/[^@]*@/, '//<credentials>@');
      logger.info({ mongoUri: sanitizedUri, timeoutMs }, 'Connecting to MongoDB');

      this.client = new MongoClient(mongoUri, options);
      await this.client.connect();

      const database = process.env.MONGODB_DATABASE || 'LEGIFRANCE';
      this.db = this.client.db(database);

      await this.db.admin().ping();

      const duration = Date.now() - startTime;
      logger.info({ durationMs: duration, database }, 'MongoDB connected successfully');
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      logger.error({ errorMessage, durationMs: duration }, 'Failed to initialize MongoDB connection');

      this.client = null;
      this.db = null;

      throw error;
    }
  }

  getClient(): MongoClient {
    if (!this.client) {
      throw new Error('MongoDB client not initialized. Call connect() first.');
    }
    return this.client;
  }

  getDb(): Db {
    if (!this.db) {
      throw new Error('MongoDB database not initialized. Call connect() first.');
    }
    return this.db;
  }

  async close(): Promise<void> {
    if (!this.client) return;

    try {
      logger.info('Closing MongoDB connection');
      await this.client.close();
      this.client = null;
      this.db = null;
      logger.info('MongoDB connection closed');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : String(error);
      logger.error({ errorMessage }, 'Error closing MongoDB connection');
    }
  }

  async fetchDocuments(chunkIds: string[]): Promise<Document[]> {
    const startTime = Date.now();

    try {
      if (!this.db) throw new Error('MongoDB not initialized');
      if (!chunkIds || chunkIds.length === 0) return [];

      logger.info({ chunkCount: chunkIds.length }, 'Fetching documents from MongoDB');

      const collection = this.db.collection(process.env.MONGODB_COLLECTION || 'chunks');

      const documents = await collection
        .find({ chunkId: { $in: chunkIds } })
        .project({ chunkId: 1, content: 1, type: 1, title: 1 })
        .toArray();

      const duration = Date.now() - startTime;
      logger.info(
        { docCount: documents.length, requested: chunkIds.length, durationMs: duration },
        'Documents fetched from MongoDB'
      );

      return documents as Document[];
    } catch (error) {
      const duration = Date.now() - startTime;
      const errorMessage = error instanceof Error ? error.message : String(error);

      logger.error(
        { errorMessage, errorType: (error as any)?.name, durationMs: duration },
        'Failed to fetch documents from MongoDB'
      );

      throw new RagError(
        'retrieval',
        errorMessage.includes('timeout') ? 'TIMEOUT' : 'DB_FETCH_FAILED',
        `Failed to fetch documents from MongoDB: ${errorMessage}`,
      );
    }
  }

  async getDocumentCount(): Promise<number> {
    try {
      if (!this.db) throw new Error('MongoDB not initialized');
      const collection = this.db.collection(process.env.MONGODB_COLLECTION || 'chunks');
      return await collection.countDocuments();
    } catch (error) {
      logger.warn('Failed to get document count for health check');
      return 0;
    }
  }
}

// ---------------------------------------------------------------------------
// Singleton instance — shared across the application
// ---------------------------------------------------------------------------
export const mongoDbClient = new MongoDbClient();

// Backward-compatible function exports delegating to the singleton
export const initMongoClient  = ()      => mongoDbClient.connect();
export const closeMongoClient = ()      => mongoDbClient.close();
export const getMongoClient   = async () => mongoDbClient.getClient();
export const getMongoDb       = async () => mongoDbClient.getDb();
export const fetchDocuments   = (elis: string[]) => mongoDbClient.fetchDocuments(elis);
export const getDocumentCount = ()      => mongoDbClient.getDocumentCount();
