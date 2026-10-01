import type { ChatError, ChatErrorStage } from '@murphy/contract/errors';
import type { DocumentType } from '@murphy/contract/messages';

/** `request` = l'extraction de la question, première étape du pipeline */
export type RagStage = Exclude<ChatErrorStage, 'internal'>;

export class RagError extends Error {
  constructor(
    public readonly stage: RagStage,
    public readonly code: string,
    message: string,
  ) {
    super(message);
    this.name = 'RagError';
    Object.setPrototypeOf(this, RagError.prototype);
  }
}

/** Comment échoue un appel d'infrastructure, hors timeout */
export interface RagFailure {
  readonly stage: RagStage;
  readonly code: string;
  /** Complète « Failed to … », par ex. `generate embeddings` */
  readonly operation: string;
}

const TIMEOUT_CODE = 'TIMEOUT';
/**
 * `TimeoutError` (`AbortSignal.timeout`), `QdrantClientTimeoutError`,
 * `MongoNetworkTimeoutError`, `MongoOperationTimeoutError`
 */
const TIMEOUT_ERROR_NAME_SUFFIX = 'TimeoutError';

/**
 * Pas d'`instanceof Error` : une `DOMException` d'un autre realm (le bac à sable de
 * Jest) porte ces champs sans passer ce test.
 */
const readErrorField = (error: unknown, field: 'name' | 'message'): string | undefined => {
  if (typeof error !== 'object' || error === null) return undefined;
  const value: unknown = Reflect.get(error, field);
  return typeof value === 'string' ? value : undefined;
};

/** Code `TIMEOUT` si le type de l'erreur l'indique, sinon celui de `failure` */
export const toRagError = (failure: RagFailure, error: unknown): RagError => {
  const isTimeout = readErrorField(error, 'name')?.endsWith(TIMEOUT_ERROR_NAME_SUFFIX) ?? false;
  const cause = readErrorField(error, 'message') ?? String(error);
  return new RagError(failure.stage, isTimeout ? TIMEOUT_CODE : failure.code, `Failed to ${failure.operation}: ${cause}`);
};

const INTERNAL_CHAT_ERROR: ChatError = { stage: 'internal', code: 'INTERNAL' };

/**
 * Ce que le client apprend d'un échec (ADR-041) : étape et code d'une `RagError`, rien
 * d'une autre erreur. Le message reste dans les logs.
 */
export const toChatError = (error: unknown): ChatError =>
  error instanceof RagError ? { stage: error.stage, code: error.code } : INTERNAL_CHAT_ERROR;

const CONTRACT_VIOLATION_CODE = 'CONTRACT_VIOLATION';

/**
 * Les bases ne respectent pas le contrat de service (ADR-039). Jamais ignoré en silence :
 * un mauvais passage dans le contexte du LLM est pire qu'une erreur visible.
 */
export const contractViolation = (message: string): RagError =>
  new RagError('retrieval', CONTRACT_VIOLATION_CODE, `Serving contract violated (ADR-039): ${message}`);

/** `charStart`/`charEnd` comptent des points de code Unicode dans le `content` du parent */
export interface RetrievedChunk {
  readonly chunkId: string;
  /** Clé du document parent dans `documents` (MongoDB) */
  readonly identifier: string;
  readonly charStart: number;
  readonly charEnd: number;
  readonly score: number;
  readonly documentType: DocumentType;
  /** La nature juridique (`LOI`, `ARRET`…), quand la source en donne une utile */
  readonly nature?: string;
}

export interface StoredDocument {
  readonly identifier: string;
  readonly title: string;
  readonly content: string;
}

export interface Passage {
  readonly chunk: RetrievedChunk;
  readonly document: StoredDocument;
  readonly text: string;
  /** Offsets UTF-16 de `text` dans `document.content` */
  readonly highlightStart: number;
  readonly highlightEnd: number;
}

/** Sa longueur dépend du modèle configuré */
export type EmbeddingVector = number[];
