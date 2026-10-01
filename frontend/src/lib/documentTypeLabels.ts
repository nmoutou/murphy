import type { DocumentType } from '@murphy/contract/messages';

/** A label per document type: a type added to the contract fails the build until named here */
const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  article: 'Article',
  section: 'Section',
  texte: 'Texte',
  decision: 'Décision',
};

const NATURE_SEPARATOR = ' · ';

/** The type of a source as shown to the user: `Article`, `Texte · LOI`, `Décision · QPC` */
export function describeDocumentType(documentType: DocumentType, nature?: string): string {
  const label = DOCUMENT_TYPE_LABELS[documentType];
  return nature ? `${label}${NATURE_SEPARATOR}${nature}` : label;
}
