/**
 * Passages
 * Joins each retrieved chunk to its parent document and cuts its text out (ADR-039 §1).
 * The ingestion counts offsets in Unicode code points (Python `str`); JavaScript strings
 * count UTF-16 units. The conversion happens here, once, so that nothing downstream,
 * the client included, has to know about the difference.
 */

import type { Passage, RetrievedChunk, StoredDocument } from '../types/rag';
import { contractViolation, serializeDocumentKey } from '../types/rag';

export interface Utf16Range {
  readonly start: number;
  readonly end: number;
}

/**
 * Converts code point offsets into UTF-16 offsets of the same string
 * @returns `undefined` unless `0 ≤ charStart < charEnd ≤ code point count`
 */
export const toUtf16Range = (content: string, charStart: number, charEnd: number): Utf16Range | undefined => {
  if (charStart < 0 || charStart >= charEnd) return undefined;

  let codePoints = 0;
  let units = 0;
  let start: number | undefined;
  // `for…of` walks code points; `character.length` is 2 for a surrogate pair
  for (const character of content) {
    if (codePoints === charStart) start = units;
    if (codePoints === charEnd) break;
    units += character.length;
    codePoints += 1;
  }
  const hasReachedEnd = codePoints === charEnd;
  return start !== undefined && hasReachedEnd ? { start, end: units } : undefined;
};

const cutPassage = (chunk: RetrievedChunk, document: StoredDocument): Passage => {
  const range = toUtf16Range(document.content, chunk.charStart, chunk.charEnd);
  if (!range) {
    throw contractViolation(
      `chunk ${chunk.chunkId} offsets [${chunk.charStart}, ${chunk.charEnd}) fall outside ` +
        `the content of ${chunk.identifier}`
    );
  }
  return {
    chunk,
    document,
    text: document.content.slice(range.start, range.end),
    highlightStart: range.start,
    highlightEnd: range.end,
  };
};

/**
 * Keeps the ranking order of `chunks`
 * @throws RagError `CONTRACT_VIOLATION` naming the chunk when its parent document is
 * missing or its offsets fall outside the parent's content
 */
export const assemblePassages = (
  chunks: readonly RetrievedChunk[],
  documents: readonly StoredDocument[]
): Passage[] => {
  const documentsByKey = new Map(documents.map((document) => [serializeDocumentKey(document), document]));
  return chunks.map((chunk) => {
    const document = documentsByKey.get(serializeDocumentKey(chunk));
    if (!document) {
      throw contractViolation(`chunk ${chunk.chunkId} has no parent document ${chunk.identifier} in MongoDB`);
    }
    return cutPassage(chunk, document);
  });
};
