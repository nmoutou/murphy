/**
 * MongoDB Client
 * Connected at creation (`MongoDbClient.connect`), closed at shutdown
 */

import { MongoClient, Db, MongoClientOptions } from 'mongodb';
import type { MongoConfig } from '../config';
import type { DocumentKey, RagFailure, StoredDocument } from '../types/rag';
import { logger } from '../utils/logger';
import { contractViolation, serializeDocumentKey, toRagError } from '../types/rag';

const MONGO_MAX_POOL_SIZE = 10;
/** Written by the ingestion, one whole document per `(identifier, owner_id)` (ADR-039 §2) */
const DOCUMENTS_COLLECTION = 'documents';
const DOCUMENT_PROJECTION = { _id: 0, identifier: 1, owner_id: 1, title: 1, content: 1 };
const DOCUMENT_FETCH_FAILURE: RagFailure = {
  stage: 'retrieval',
  code: 'DB_FETCH_FAILED',
  operation: 'fetch parent documents from MongoDB',
};

const hideCredentials = (uri: string): string => uri.replace(/\/\/[^@]*@/, '//<credentials>@');

/** A `documents` record as MongoDB returns it: external data, checked before use */
type DocumentRecord = Readonly<Record<string, unknown>>;

const distinctKeys = (keys: readonly DocumentKey[]): DocumentKey[] => [
  ...new Map(keys.map((key) => [serializeDocumentKey(key), key])).values(),
];

/**
 * @throws RagError `CONTRACT_VIOLATION` when a field of the contract is not a string
 */
const toStoredDocument = (record: DocumentRecord): StoredDocument => {
  const { identifier, owner_id: ownerId, title, content } = record;
  const isValid =
    typeof identifier === 'string' &&
    typeof ownerId === 'string' &&
    typeof title === 'string' &&
    typeof content === 'string';
  if (!isValid) {
    throw contractViolation(`MongoDB document ${String(identifier)} lacks identifier, owner_id, title or content`);
  }
  return { identifier, ownerId, title, content };
};

export class MongoDbClient {
  private constructor(
    private readonly client: MongoClient,
    private readonly db: Db,
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
      return new MongoDbClient(client, db);
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
   * Reads the parent documents of the retrieved chunks, by their indexed key
   * @throws RagError with stage='retrieval'
   */
  async fetchParentDocuments(keys: readonly DocumentKey[]): Promise<StoredDocument[]> {
    const startTime = Date.now();
    const distinct = distinctKeys(keys);
    logger.info({ documentCount: distinct.length }, 'Fetching parent documents from MongoDB');

    let records: DocumentRecord[];
    try {
      records = await this.db
        .collection(DOCUMENTS_COLLECTION)
        .find({ $or: distinct.map(({ identifier, ownerId }) => ({ identifier, owner_id: ownerId })) })
        .project<DocumentRecord>(DOCUMENT_PROJECTION)
        .toArray();
    } catch (error) {
      const ragError = toRagError(DOCUMENT_FETCH_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }

    logger.info(
      { fetched: records.length, requested: distinct.length, durationMs: Date.now() - startTime },
      'Parent documents fetched from MongoDB'
    );
    return records.map(toStoredDocument);
  }
}
