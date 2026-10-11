import type { DocumentType } from '@murphy/contract/search';

/** Partielle : une nature absente prend l'icône de son type */
const NATURE_ICONS: Partial<Record<string, string>> = {
  CODE: 'folder',
};

/** Un type ajouté au contrat casse le build tant qu'il n'a pas d'icône */
const TYPE_ICONS: Record<DocumentType, string> = {
  article: 'doc',
  section: 'folder',
  texte: 'edit',
  decision: 'window',
};

export const selectDocumentIcon = (documentType: DocumentType, nature?: string): string =>
  (nature ? NATURE_ICONS[nature] : undefined) ?? TYPE_ICONS[documentType];
