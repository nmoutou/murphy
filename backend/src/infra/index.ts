/**
 * Infrastructure Barrel Export
 * Re-exports all infra clients, utilities, and shared singletons
 */

export { EmbeddingClient } from './embedding';
export { QdrantVectorClient } from './qdrant';
export {
  MongoDbClient,
  mongoDbClient,
  initMongoClient,
  getMongoClient,
  getMongoDb,
  closeMongoClient,
  fetchDocuments,
  getDocumentCount,
} from './mongodb';
export { LLMProvider } from './llm';

// Shared singletons — lazy, instantiated on first access, reused across requests
import { EmbeddingClient } from './embedding';
import { QdrantVectorClient } from './qdrant';
import { LLMProvider } from './llm';

let _embeddingClient: EmbeddingClient | null = null;
let _qdrantClient: QdrantVectorClient | null = null;
let _llmProvider: LLMProvider | null = null;

export const embeddingClient: EmbeddingClient = new Proxy({} as EmbeddingClient, {
  get(_target, prop) {
    if (!_embeddingClient) _embeddingClient = new EmbeddingClient();
    return (_embeddingClient as any)[prop];
  },
});

export const qdrantClient: QdrantVectorClient = new Proxy({} as QdrantVectorClient, {
  get(_target, prop) {
    if (!_qdrantClient) _qdrantClient = new QdrantVectorClient();
    return (_qdrantClient as any)[prop];
  },
});

export const llmProvider: LLMProvider = new Proxy({} as LLMProvider, {
  get(_target, prop) {
    if (!_llmProvider) _llmProvider = new LLMProvider();
    return (_llmProvider as any)[prop];
  },
});
