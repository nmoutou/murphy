/**
 * L'ingestion compte les offsets en points de code (`str` Python), JavaScript en unités
 * UTF-16. La conversion se fait ici, une seule fois : rien en aval, client compris, n'a
 * à connaître la différence.
 */

import type { FoundDocument, Passage, PassageRef, RetrievedDocument, StoredDocument } from '../types/rag';
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

const cutPassage = (ref: PassageRef, document: StoredDocument): Passage => {
  const range = toUtf16Range(document.content, ref.charStart, ref.charEnd);
  if (!range) {
    throw contractViolation(
      `chunk ${ref.chunkId} offsets [${ref.charStart}, ${ref.charEnd}) fall outside ` +
        `the content of ${document.identifier}`
    );
  }
  return {
    ref,
    text: document.content.slice(range.start, range.end),
    highlightStart: range.start,
    highlightEnd: range.end,
  };
};

/**
 * Garde l'ordre de classement des documents et de leurs passages
 * @throws RagError `CONTRACT_VIOLATION` si un document manque à MongoDB ou si les offsets
 * d'un passage sortent de son contenu
 */
export const assembleDocuments = (
  retrieved: readonly RetrievedDocument[],
  storedDocuments: readonly StoredDocument[]
): FoundDocument[] => {
  const documentsByIdentifier = new Map(storedDocuments.map((document) => [document.identifier, document]));
  return retrieved.map(({ identifier, documentType, nature, passages }) => {
    const document = documentsByIdentifier.get(identifier);
    if (!document) {
      throw contractViolation(`OpenSearch document ${identifier} has no counterpart in MongoDB`);
    }
    return { document, documentType, nature, passages: passages.map((ref) => cutPassage(ref, document)) };
  });
};
