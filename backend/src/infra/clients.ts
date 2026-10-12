/** Créés une fois au démarrage, avant l'écoute, puis partagés par toutes les requêtes. */

import type { AppConfig } from '../config';
import type { LlmClient } from './llm';
import { EmbeddingClient } from './embedding';
import { createLlmClient } from './llm';
import { MongoDbClient } from './mongodb';
import { OpenSearchClient } from './opensearch';

export interface InfraClients {
  readonly mongo: MongoDbClient;
  readonly opensearch: OpenSearchClient;
  readonly embedding: EmbeddingClient;
  readonly llm: LlmClient;
}

let clients: InfraClients | undefined;

/**
 * @throws si MongoDB ou OpenSearch est injoignable, ou l'index absent : mieux vaut
 * arrêter le démarrage qu'échouer à la première question. Le LLM n'est pas sondé : une
 * panne du fournisseur ne doit pas empêcher la recherche de redémarrer.
 */
export const initInfraClients = async (config: AppConfig): Promise<void> => {
  const mongo = await MongoDbClient.connect(config.mongo);
  const opensearch = new OpenSearchClient({ opensearch: config.opensearch, pagination: config.pagination });
  await opensearch.prepareSearch();

  clients = { mongo, opensearch, embedding: new EmbeddingClient(config.embedding), llm: createLlmClient(config.llm) };
};

export const getInfraClients = (): InfraClients => {
  if (!clients) throw new Error('Infrastructure clients not initialized: call initInfraClients() at boot');
  return clients;
};

export const closeInfraClients = async (): Promise<void> => {
  await clients?.mongo.close();
  clients = undefined;
};
