import { Client } from '@opensearch-project/opensearch';
import type { OpenSearchConfig, PaginationConfig } from '../config';
import type { EmbeddingVector, RagFailure, SearchHit } from '../types/rag';
import { logger as rootLogger } from '../utils/logger';
import { toRagError } from '../types/rag';
import { buildHybridQuery } from './hybridQuery';
import { toSearchHit } from './searchHits';

const logger = rootLogger.child({ context: 'opensearch' });

const INGESTION_COMMAND = 'kedro run';
/** Écrit par le backend au boot, l'ingestion n'en sait rien (ADR-028 §6) */
const RRF_PIPELINE = 'murphy-rrf';
const RRF_PIPELINE_BODY = {
  phase_results_processors: [{ 'score-ranker-processor': { combination: { technique: 'rrf' as const } } }],
};

const SEARCH_FAILURE: RagFailure = { stage: 'retrieval', code: 'SEARCH_FAILED', operation: 'search OpenSearch' };

export interface OpenSearchClientOptions {
  readonly opensearch: OpenSearchConfig;
  readonly pagination: PaginationConfig;
}

export class OpenSearchClient {
  private readonly client: Client;

  constructor(private readonly options: OpenSearchClientOptions) {
    // Aucune relance : le serving échoue vite (ADR-010)
    this.client = new Client({ node: options.opensearch.url, requestTimeout: options.opensearch.timeoutMs, maxRetries: 0 });
  }

  /**
   * Vérifie l'index, puis écrit le pipeline RRF : une écriture idempotente
   * @throws si OpenSearch est injoignable ou l'index absent
   */
  async prepareSearch(): Promise<void> {
    await this.assertIndexExists();
    await this.client.searchPipeline.put({ id: RRF_PIPELINE, body: RRF_PIPELINE_BODY });
    logger.info({ pipeline: RRF_PIPELINE }, 'OpenSearch RRF search pipeline written');
  }

  private async assertIndexExists(): Promise<void> {
    const { url, index } = this.options.opensearch;
    const { body: exists } = await this.client.indices.exists({ index }).catch((error: unknown) => {
      throw new Error(`OpenSearch unreachable (${url}): cannot check the index "${index}". Cause: ${String(error)}`);
    });
    if (!exists) {
      throw new Error(
        `The OpenSearch index "${index}" (OPENSEARCH_INDEX) does not exist. Run the ingestion: ${INGESTION_COMMAND}.`
      );
    }
    logger.info({ index }, 'OpenSearch index found');
  }

  /**
   * Une page des documents classés, `PAGINATION_SIZE` documents à partir du rang `from`
   * @throws RagError d'étape `retrieval`, ou `CONTRACT_VIOLATION` sur un document invalide
   */
  async search(question: string, vector: EmbeddingVector, from: number): Promise<SearchHit[]> {
    const startTime = Date.now();
    const { index } = this.options.opensearch;
    const { size, depth } = this.options.pagination;
    logger.info({ vectorDim: vector.length, from, size, depth, index }, 'OpenSearch search started');

    let hits: unknown[];
    try {
      const response = await this.client.search({
        index,
        search_pipeline: RRF_PIPELINE,
        body: buildHybridQuery({ question, vector, from, size, depth }),
      });
      hits = response.body.hits.hits;
    } catch (error) {
      const ragError = toRagError(SEARCH_FAILURE, error);
      logger.error({ err: error, durationMs: Date.now() - startTime }, ragError.message);
      throw ragError;
    }

    // Hors du `try` : une violation de contrat n'est pas une recherche échouée
    const searchHits = hits.map(toSearchHit);
    logger.info({ resultCount: searchHits.length, durationMs: Date.now() - startTime }, 'OpenSearch search completed');
    return searchHits;
  }
}
