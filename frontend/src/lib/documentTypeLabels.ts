import type { DocumentType } from '@murphy/contract/messages';

/** Un type ajouté au contrat casse le build tant qu'il n'est pas nommé ici */
const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  article: 'Article',
  section: 'Section',
  texte: 'Texte',
  decision: 'Décision',
};

const NATURE_SEPARATOR = ' · ';

/** Tel qu'affiché : `Article`, `Texte · LOI`, `Décision · QPC` */
export function describeDocumentType(documentType: DocumentType, nature?: string): string {
  const label = DOCUMENT_TYPE_LABELS[documentType];
  return nature ? `${label}${NATURE_SEPARATOR}${nature}` : label;
}
