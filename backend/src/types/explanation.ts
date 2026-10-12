import type { DocumentType } from '@murphy/contract/search';

/** Une métadonnée de la liste blanche : une valeur, ou plusieurs (des dates) */
export type MetadataValue = string | readonly string[];

/** Un document de la sélection, relu dans Mongo : jamais le texte envoyé par le client */
export interface ExplainedDocument {
  readonly identifier: string;
  readonly title: string;
  readonly content: string;
  readonly documentType: DocumentType;
  readonly nature?: string;
  /** Les titres du texte parent, un par période, souvent un seul */
  readonly parentTextTitles: readonly string[];
  /** Les seules clés de la liste blanche, quand le document les porte */
  readonly metadata: Readonly<Record<string, MetadataValue>>;
}
