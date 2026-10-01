/**
 * L'ingestion compte les offsets en points de code (`str` Python), JavaScript en unités
 * UTF-16. La conversion se fait ici, une seule fois : rien en aval, client compris, n'a
 * à connaître la différence.
 */

import type { Passage, RetrievedChunk, StoredDocument } from '../types/rag';
import { contractViolation } from '../types/rag';

export interface Utf16Range {
  readonly start: number;
  readonly end: number;
}

/**
 * @returns `undefined` sauf si `0 ≤ charStart < charEnd ≤ nombre de points de code`
 */
export const toUtf16Range = (content: string, charStart: number, charEnd: number): Utf16Range | undefined => {
  if (charStart < 0 || charStart >= charEnd) return undefined;

  let codePoints = 0;
  let units = 0;
  let start: number | undefined;
  // `for…of` parcourt les points de code ; `character.length` vaut 2 pour une paire de substitution
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
 * Garde l'ordre de classement de `chunks`
 * @throws RagError `CONTRACT_VIOLATION` nommant le chunk si son parent manque ou si ses
 * offsets sortent du contenu du parent
 */
export const assemblePassages = (
  chunks: readonly RetrievedChunk[],
  documents: readonly StoredDocument[]
): Passage[] => {
  const documentsByIdentifier = new Map(documents.map((document) => [document.identifier, document]));
  return chunks.map((chunk) => {
    const document = documentsByIdentifier.get(chunk.identifier);
    if (!document) {
      throw contractViolation(`chunk ${chunk.chunkId} has no parent document ${chunk.identifier} in MongoDB`);
    }
    return cutPassage(chunk, document);
  });
};
