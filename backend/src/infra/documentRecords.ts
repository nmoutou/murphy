/** Un enregistrement de `documents` (MongoDB) vérifié contre le contrat de service (ADR-015) */

import type { StoredDocument } from '../types/rag';
import type { ExplainedDocument, MetadataValue } from '../types/explanation';
import { documentTypeSchema } from '@murphy/contract/search';
import { contractViolation } from '../types/rag';

/** Donnée externe, vérifiée avant usage */
export type DocumentRecord = Readonly<Record<string, unknown>>;

const isContentLength = (value: unknown): value is number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0;

/**
 * @throws RagError `CONTRACT_VIOLATION` si un champ du contrat n'est pas une chaîne, ou
 * `content_length` pas un entier positif ou nul
 */
export const toStoredDocument = (record: DocumentRecord): StoredDocument => {
  const { identifier, title, content, content_length: contentLength } = record;
  const isValid = typeof identifier === 'string' && typeof title === 'string' && typeof content === 'string';
  if (!isValid) {
    throw contractViolation(`MongoDB document ${String(identifier)} lacks identifier, title or content`);
  }
  if (!isContentLength(contentLength)) {
    throw contractViolation(`MongoDB document ${identifier} lacks a valid content_length: re-ingest the corpus`);
  }
  return { identifier, title, content, contentLength };
};

const readStatus = (record: DocumentRecord): unknown => {
  const { metadata } = record;
  return typeof metadata === 'object' && metadata !== null && 'statut' in metadata ? metadata.statut : undefined;
};

/**
 * @throws RagError `CONTRACT_VIOLATION` si un champ du contrat, statut compris, n'est pas une chaîne
 */
export const toSearchedDocument = (record: DocumentRecord): StoredDocument => {
  const document = toStoredDocument(record);
  const status = readStatus(record);
  if (status === undefined) return document;
  if (typeof status !== 'string') {
    throw contractViolation(`MongoDB document ${document.identifier} has a non-string metadata.statut`);
  }
  return { ...document, status };
};

const METADATA_FIELD = 'metadata';

const isStringList = (value: unknown): value is readonly string[] =>
  Array.isArray(value) && value.every((entry) => typeof entry === 'string');

const isMetadataValue = (value: unknown): value is MetadataValue =>
  typeof value === 'string' || isStringList(value);

/** La projection ne lit que les métadonnées de la liste blanche : le reste ne quitte pas Mongo */
export const toExplainedProjection = (metadataKeys: readonly string[]): Record<string, number> => ({
  _id: 0,
  identifier: 1,
  title: 1,
  content: 1,
  content_length: 1,
  document_type: 1,
  nature: 1,
  parent_text_title: 1,
  ...Object.fromEntries(metadataKeys.map((key) => [`${METADATA_FIELD}.${key}`, 1])),
});

const readMetadata = (identifier: string, metadata: unknown): Record<string, MetadataValue> => {
  if (typeof metadata !== 'object' || metadata === null) return {};
  const entries = Object.entries(metadata);
  const invalid = entries.find(([, value]) => !isMetadataValue(value));
  if (invalid) {
    throw contractViolation(`MongoDB document ${identifier} has a metadata.${invalid[0]} that is neither a string nor a list of strings`);
  }
  return Object.fromEntries(entries);
};

/**
 * @throws RagError `CONTRACT_VIOLATION` si un champ du contrat manque ou n'a pas son type
 */
export const toExplainedDocument = (record: DocumentRecord): ExplainedDocument => {
  const { identifier, title, content } = toStoredDocument(record);
  const documentType = documentTypeSchema.safeParse(record.document_type);
  const { nature, parent_text_title: parentTextTitles = [] } = record;
  const isValid = documentType.success && (nature === undefined || nature === null || typeof nature === 'string')
    && isStringList(parentTextTitles);
  if (!isValid) {
    throw contractViolation(`MongoDB document ${identifier} has an invalid document_type, nature or parent_text_title`);
  }
  return {
    identifier,
    title,
    content,
    documentType: documentType.data,
    nature: nature ?? undefined,
    parentTextTitles,
    metadata: readMetadata(identifier, record[METADATA_FIELD]),
  };
};
