/**
 * MongoDB Client
 * Connected at creation (`MongoDbClient.connect`), closed at shutdown
 */

import { MongoClient, Db, MongoClientOptions } from 'mongodb';
import type { MongoConfig } from '../config';
import type { Document, RagFailure } from '../types/rag';
import { logger } from '../utils/logger';
import { toRagError } from '../types/rag';

const MONGO_MAX_POOL_SIZE = 10;
const CHUNK_PROJECTION = { chunkId: 1, content: 1, type: 1, title: 1 };
const DOCUMENT_FETCH_FAILURE: RagFailure = {
  stage: 'retrieval',
  code: 'DB_FETCH_FAILED',
  operation: 'fetch documents from MongoDB',
};

const hideCredentials = (uri: string): string => uri.replace(/\/\/[^@]*@/, '//<credentials>@');

export class MongoDbClient {
  private constructor(
    private readonly client: MongoClient,
    private readonly db: Db,
    private readonly collectionName: string,
  ) {}

  /**
   * Connects, then pings the database so that a wrong URI fails at boot
   * @throws the driver error when MongoDB cannot be reached
   */
  static async connect(settings: MongoConfig): Promise<MongoDbClient> {
    const startTime = Date.now();
    const options: MongoClientOptions = {
      serverSelectionTimeoutMS: settings.timeoutMs,
      connectTimeoutMS: settings.timeoutMs,
      socketTimeoutMS: settings.timeoutMs,
      retryWrites: true,
      maxPoolSize: MONGO_MAX_POOL_SIZE,
    };
    logger.info({ mongoUri: hideCredentials(settings.uri), timeoutMs: settings.timeoutMs }, 'Connecting to MongoDB');

    try {
      const client = await new MongoClient(settings.uri, options).connect();
      const db = client.db(settings.database);
      await db.admin().ping();
      logger.info({ durationMs: Date.now() - startTime, database: settings.database }, 'MongoDB connected successfully');
      return new MongoDbClient(client, db, settings.collection);
    } catch (error) {
      logger.error({ err: error, durationMs: Date.now() - startTime }, 'Failed to initialize MongoDB connection');
      throw error;
    }
  }

  /** The driver client, to reach another database than the data one (the meta database) */
  getClient(): MongoClient {
    return this.client;
  }

  getDb(): Db {
    return this.db;
  }

  async close(): Promise<void> {
    logger.info('Closing MongoDB connection');
    try {
      await this.client.close();
      logger.info('MongoDB connection closed');
    } catch (error) {
      logger.error({ err: error }, 'Error closing MongoDB connection');
    }
  }

  /**
   * @throws RagError with stage='retrieval'
   */
  async fetchDocuments(chunkIds: string[]): Promise<Document[]> {
    const startTime = Date.now();
    logger.info({ chunkCount: chunkIds.length }, 'Fetching documents from MongoDB');

    try {
      const documents = await this.db
        .collection<Document>(this.collectionName)
        .find({ chunkId: { $in: chunkIds } })
        .project<Document>(CHUNK_PROJECTION)
        .toArray();

      logger.info(
        { docCount: documents.length, requested: chunkIds.length, durationMs: Date.now() - startTime },
        'Documents fetched from MongoDB'
      );
      return documents;
    } catch (error) {
      const ragError = toRagError(DOCUMENT_FETCH_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }
  }
}
