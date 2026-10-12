import { MongoClient, Db, MongoClientOptions } from 'mongodb';
import type { MongoConfig } from '../config';
import type { RagFailure, StoredDocument } from '../types/rag';
import type { ExplainedDocument } from '../types/explanation';
import type { DocumentRecord } from './documentRecords';
import { logger as rootLogger } from '../utils/logger';
import { RagError, toRagError } from '../types/rag';
import { toExplainedDocument, toExplainedProjection, toSearchedDocument, toStoredDocument } from './documentRecords';

const logger = rootLogger.child({ context: 'mongodb' });

const MONGO_MAX_POOL_SIZE = 10;
/** Écrite par l'ingestion : un document entier par `identifier` (ADR-015) */
const DOCUMENTS_COLLECTION = 'documents';
const DOCUMENT_PROJECTION = { _id: 0, identifier: 1, title: 1, content: 1, content_length: 1 };
const SEARCH_DOCUMENT_PROJECTION = { ...DOCUMENT_PROJECTION, 'metadata.statut': 1 };
const DOCUMENT_FETCH_FAILURE: RagFailure = {
  stage: 'retrieval',
  code: 'DB_FETCH_FAILED',
  operation: 'fetch parent documents from MongoDB',
};
const SINGLE_DOCUMENT_FETCH_FAILURE: RagFailure = { ...DOCUMENT_FETCH_FAILURE, operation: 'fetch a document from MongoDB' };
const EXPLAINED_DOCUMENTS_FETCH_FAILURE: RagFailure = { ...DOCUMENT_FETCH_FAILURE, operation: 'fetch the selected documents from MongoDB' };

const hideCredentials = (uri: string): string => uri.replace(/\/\/[^@]*@/, '//<credentials>@');

export class MongoDbClient {
  private constructor(
    private readonly client: MongoClient,
    private readonly db: Db,
  ) {}

  /**
   * Le ping fait échouer une URI fausse dès le démarrage
   * @throws l'erreur du driver si MongoDB est injoignable
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

  /** @throws RagError d'étape `retrieval` */
  async fetchParentDocuments(identifiers: readonly string[]): Promise<StoredDocument[]> {
    const startTime = Date.now();
    const distinct = [...new Set(identifiers)];
    logger.info({ documentCount: distinct.length }, 'Fetching parent documents from MongoDB');

    let records: DocumentRecord[];
    try {
      records = await this.db
        .collection(DOCUMENTS_COLLECTION)
        .find({ identifier: { $in: distinct } })
        .project<DocumentRecord>(SEARCH_DOCUMENT_PROJECTION)
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
    return records.map(toSearchedDocument);
  }

  /**
   * @returns `undefined` si aucun document ne porte cet identifiant
   * @throws RagError d'étape `retrieval`
   */
  async fetchDocument(identifier: string): Promise<StoredDocument | undefined> {
    const startTime = Date.now();
    let record: DocumentRecord | null;
    try {
      record = await this.db
        .collection(DOCUMENTS_COLLECTION)
        .findOne<DocumentRecord>({ identifier }, { projection: DOCUMENT_PROJECTION });
    } catch (error) {
      const ragError = toRagError(SINGLE_DOCUMENT_FETCH_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }

    logger.info({ identifier, isFound: record !== null, durationMs: Date.now() - startTime }, 'Document fetched from MongoDB');
    return record ? toStoredDocument(record) : undefined;
  }

  /**
   * Les documents d'une sélection, dans son ordre, avec les seules métadonnées nommées
   * @throws RagError `DOCUMENT_NOT_FOUND` s'il en manque un, ou d'étape `retrieval`
   */
  async fetchExplainedDocuments(
    identifiers: readonly string[],
    metadataKeys: readonly string[],
  ): Promise<ExplainedDocument[]> {
    const startTime = Date.now();
    let records: DocumentRecord[];
    try {
      records = await this.db
        .collection(DOCUMENTS_COLLECTION)
        .find({ identifier: { $in: [...identifiers] } })
        .project<DocumentRecord>(toExplainedProjection(metadataKeys))
        .toArray();
    } catch (error) {
      const ragError = toRagError(EXPLAINED_DOCUMENTS_FETCH_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }

    logger.info({ fetched: records.length, requested: identifiers.length, durationMs: Date.now() - startTime }, 'Selected documents fetched from MongoDB');
    const byIdentifier = new Map(records.map((record) => [record.identifier, record]));
    return identifiers.map((identifier) => {
      const record = byIdentifier.get(identifier);
      if (!record) throw new RagError('request', 'DOCUMENT_NOT_FOUND', `No document has the identifier ${identifier}`);
      return toExplainedDocument(record);
    });
  }
}
