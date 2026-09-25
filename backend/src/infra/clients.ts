/**
 * Infrastructure Clients
 * Created once at boot by `initInfraClients`, before the server listens, then
 * shared by every request through `getInfraClients`.
 */

import type { AppConfig } from '../config';
import { EmbeddingClient } from './embedding';
import { LLMProvider } from './llm';
import { MongoDbClient } from './mongodb';
import { QdrantVectorClient } from './qdrant';
import { resolveCollection } from './collectionPointer';

export interface InfraClients {
  readonly mongo: MongoDbClient;
  readonly qdrant: QdrantVectorClient;
  readonly embedding: EmbeddingClient;
  readonly llm: LLMProvider;
}

let clients: InfraClients | undefined;

/**
 * Connects MongoDB, resolves the Qdrant collection to serve, then builds the
 * other clients.
 * @throws when MongoDB is unreachable or the resolved collection does not exist:
 * the boot must stop rather than fail on the first question
 */
export const initInfraClients = async (config: AppConfig): Promise<void> => {
  const mongo = await MongoDbClient.connect(config.mongo);
  // The collection name is a fingerprint of the ingestion config: it is read from
  // the pointer published by the last `ok` run, never guessed
  const collection = await resolveCollection({
    mongoClient: mongo.getClient(),
    metaDatabase: config.mongo.metaDatabase,
    qdrantUrl: config.qdrant.url,
    fallbackCollection: config.qdrant.fallbackCollection,
  });

  clients = {
    mongo,
    qdrant: new QdrantVectorClient({ url: config.qdrant.url, collection, minScore: config.retrieval.minScore }),
    embedding: new EmbeddingClient(config.embedding),
    llm: new LLMProvider(config.llm),
  };
};

/**
 * @throws Error when called before `initInfraClients`
 */
export const getInfraClients = (): InfraClients => {
  if (!clients) throw new Error('Infrastructure clients not initialized: call initInfraClients() at boot');
  return clients;
};

export const closeInfraClients = async (): Promise<void> => {
  await clients?.mongo.close();
  clients = undefined;
};
