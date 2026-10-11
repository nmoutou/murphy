import type { DocumentType } from '@murphy/contract/search';

/** L'étape en échec, pour les logs : le client n'en reçoit que le code (ADR-030 §4) */
export type RagStage = 'request' | 'embedding' | 'retrieval';

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
 * `TimeoutError` (`AbortSignal.timeout`, client OpenSearch), `MongoNetworkTimeoutError`,
 * `MongoOperationTimeoutError`
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

const CONTRACT_VIOLATION_CODE = 'CONTRACT_VIOLATION';

/**
 * Les bases ne respectent pas le contrat de service (ADR-015). Jamais ignoré en silence :
 * un passage mal découpé est pire qu'une erreur visible.
 */
export const contractViolation = (message: string): RagError =>
  new RagError('retrieval', CONTRACT_VIOLATION_CODE, `Serving contract violated (ADR-015): ${message}`);

/** Un passage dans l'index : `charStart`/`charEnd` comptent des points de code Unicode dans le `content` du document */
export interface PassageRef {
  readonly chunkId: string;
  readonly charStart: number;
  readonly charEnd: number;
}

/** Un document de la recherche hybride, tel qu'OpenSearch le rend */
export interface SearchHit {
  /** Clé du document dans `documents` (MongoDB) */
  readonly identifier: string;
  readonly documentType: DocumentType;
  /** La nature juridique (`LOI`, `ARRET`…), quand la source en donne une utile */
  readonly nature?: string;
  /** Les passages trouvés par la sous-requête lexicale, du plus pertinent au moins pertinent */
  readonly lexicalPassages: readonly PassageRef[];
  /** Les passages les plus proches de la question, du plus proche au moins proche */
  readonly vectorPassages: readonly PassageRef[];
}

/** Un document classé et ses passages, classés eux aussi */
export interface RetrievedDocument {
  readonly identifier: string;
  readonly documentType: DocumentType;
  readonly nature?: string;
  readonly passages: readonly PassageRef[];
}

export interface StoredDocument {
  readonly identifier: string;
  readonly title: string;
  readonly content: string;
  /** L'`ETAT` de la DILA (`VIGUEUR`, `ABROGE`…), lu par la seule recherche ; absent d'une décision */
  readonly status?: string;
}

/** Les rangs d'une page dans le classement fusionné */
export interface ResultWindow {
  readonly from: number;
  readonly size: number;
}

export interface Passage {
  readonly ref: PassageRef;
  readonly text: string;
  /** Offsets UTF-16 de `text` dans le `content` du document */
  readonly highlightStart: number;
  readonly highlightEnd: number;
}

/** Un document classé, lu dans Mongo, et ses passages découpés */
export interface FoundDocument {
  readonly document: StoredDocument;
  readonly documentType: DocumentType;
  readonly nature?: string;
  readonly passages: readonly Passage[];
}

/** Sa longueur dépend du modèle configuré */
export type EmbeddingVector = number[];
