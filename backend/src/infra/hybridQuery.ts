/**
 * La requête hybride à quatre sous-requêtes, fusionnées par RRF (ADR-028 §6, ADR-029).
 * Décrite et mesurée dans `docs/technical/data/reference/index-opensearch.md` : les deux
 * doivent rester identiques.
 */

import type { API, Types } from '@opensearch-project/opensearch';
import type { EmbeddingVector } from '../types/rag';

type QueryContainer = Types.Common_QueryDsl.QueryContainer;

export const LEXICAL_INNER_HITS = 'lexical';
export const VECTOR_INNER_HITS = 'vectoriel';

/** `index.max_inner_result_window` par défaut (ADR-028 §7) */
const MAX_LEXICAL_PASSAGES = 100;
const PASSAGES_PATH = 'passages';
const PASSAGE_REF_FIELDS = ['passages.chunk_id', 'passages.char_start', 'passages.char_end'];
const DOCUMENT_FIELDS = ['identifier', 'document_type', 'nature'];
const LEXICAL_PASSAGE_FIELDS = ['passages.text', 'passages.text.ref'];
const LEXICAL_DOCUMENT_FIELDS = [
  'title.texte',
  'title.ref',
  'parent_text_title',
  'parent_text_title.ref',
  'metadata.*.texte',
  'metadata.*.ref',
];
const REFERENCE_DOCUMENT_FIELDS = ['title.ref', 'parent_text_title.ref', 'metadata.*.ref'];

export interface HybridQueryInput {
  readonly question: string;
  readonly vector: EmbeddingVector;
  /** Rang du premier document de la page, dans le classement fusionné */
  readonly from: number;
  /** Documents de la page */
  readonly size: number;
  /** Documents classés par chaque sous-requête, et `k` de chaque kNN */
  readonly depth: number;
}

const matchingPassages = (query: QueryContainer, innerHits?: Types.Core_Search.InnerHits): QueryContainer => ({
  nested: { path: PASSAGES_PATH, score_mode: 'max', query, ...(innerHits && { inner_hits: innerHits }) },
});

const lexicalQuery = (question: string): QueryContainer => ({
  bool: {
    should: [
      matchingPassages(
        { multi_match: { query: question, fields: LEXICAL_PASSAGE_FIELDS } },
        { name: LEXICAL_INNER_HITS, size: MAX_LEXICAL_PASSAGES, _source: PASSAGE_REF_FIELDS }
      ),
      { multi_match: { query: question, fields: LEXICAL_DOCUMENT_FIELDS } },
    ],
  },
});

/** Une question sans référence n'y produit aucun jeton : la liste est vide */
const referencesQuery = (question: string): QueryContainer => ({
  bool: {
    should: [
      matchingPassages({ match: { 'passages.text.ref': { query: question } } }),
      { multi_match: { query: question, fields: REFERENCE_DOCUMENT_FIELDS } },
    ],
  },
});

/** Dans un `nested`, `k` compte des documents, pas des passages */
const passageVectorQuery = (vector: EmbeddingVector, depth: number): QueryContainer =>
  matchingPassages(
    { knn: { 'passages.embedding': { vector, k: depth, expand_nested_docs: true } } },
    { name: VECTOR_INNER_HITS, _source: PASSAGE_REF_FIELDS }
  );

/** Seuls les documents sans passage ont un vecteur de titre (ADR-029 §2) */
const titleVectorQuery = (vector: EmbeddingVector, depth: number): QueryContainer => ({
  knn: { title_embedding: { vector, k: depth } },
});

export const buildHybridQuery = ({ question, vector, from, size, depth }: HybridQueryInput): API.Search_RequestBody => ({
  from,
  size,
  _source: { includes: DOCUMENT_FIELDS },
  query: {
    hybrid: {
      pagination_depth: depth,
      queries: [
        lexicalQuery(question),
        referencesQuery(question),
        passageVectorQuery(vector, depth),
        titleVectorQuery(vector, depth),
      ],
    },
  },
});
