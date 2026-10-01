/** Créés une fois au démarrage, avant l'écoute, puis partagés par toutes les requêtes. */

import type { AppConfig } from '../config';
import { EmbeddingClient } from './embedding';
import { LLMProvider } from './llm';
import { MongoDbClient } from './mongodb';
import { QdrantVectorClient } from './qdrant';

export interface InfraClients {
  readonly mongo: MongoDbClient;
  readonly qdrant: QdrantVectorClient;
  readonly embedding: EmbeddingClient;
  readonly llm: LLMProvider;
}

let clients: InfraClients | undefined;

/**
 * @throws si MongoDB est injoignable ou la collection Qdrant absente : mieux vaut
 * arrêter le démarrage qu'échouer à la première question
 */
export const initInfraClients = async (config: AppConfig): Promise<void> => {
  const mongo = await MongoDbClient.connect(config.mongo);
  const qdrant = new QdrantVectorClient({ ...config.qdrant, minScore: config.retrieval.minScore });
  await qdrant.assertCollectionExists();

  clients = {
    mongo,
    qdrant,
    embedding: new EmbeddingClient(config.embedding),
    llm: new LLMProvider(config.llm),
  };
};

export const getInfraClients = (): InfraClients => {
  if (!clients) throw new Error('Infrastructure clients not initialized: call initInfraClients() at boot');
  return clients;
};

export const closeInfraClients = async (): Promise<void> => {
  await clients?.mongo.close();
  clients = undefined;
};
