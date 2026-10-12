/**
 * Ce que le LLM lit d'un document de la sélection (ADR-033 §7) : son repère, son
 * identité, les métadonnées d'une liste blanche, libellées en français, et son texte.
 */

import type { DocumentType } from '@murphy/contract/search';
import type { ExplainedDocument, MetadataValue } from '../types/explanation';

type MetadataLabels = Readonly<Record<string, string>>;

/** Le statut de vigueur en tête : résumer un texte abrogé sans le dire induirait en erreur */
const LEGISLATION_METADATA: MetadataLabels = {
  statut: 'Statut de vigueur',
  date_debut: "Date d'entrée en vigueur",
  date_fin: 'Date de fin de vigueur',
  versions_a_venir: 'Versions à venir',
  date_texte: 'Date du texte',
  date_publication: 'Date de publication',
  nor: 'NOR',
  titre_full: 'Titre complet',
};

/** Ni `president`, ni `rapporteur`, ni `rapporteur_public`, ni `avocats` (loi n° 2019-222, art. 33) */
const CASE_LAW_METADATA: MetadataLabels = {
  juridiction: 'Juridiction',
  formation: 'Formation',
  date_decision: 'Date de la décision',
  numero: 'Numéro',
  ecli: 'ECLI',
  solution: 'Solution',
  type_recours: 'Type de recours',
  date_decision_attaquee: 'Date de la décision attaquée',
};

const DOCUMENT_TYPE_LABELS: Readonly<Record<DocumentType, string>> = {
  article: 'Article',
  section: 'Section',
  texte: 'Texte',
  decision: 'Décision de justice',
};

const LIST_SEPARATOR = ', ';
const LINE_SEPARATOR = '\n';
const DOCUMENT_SEPARATOR = '\n\n---\n\n';

const metadataLabelsOf = (documentType: DocumentType): MetadataLabels =>
  documentType === 'decision' ? CASE_LAW_METADATA : LEGISLATION_METADATA;

/** Les clés à lire dans Mongo : la liste blanche des deux sources */
export const EXPLAINED_METADATA_KEYS: readonly string[] = [
  ...Object.keys(LEGISLATION_METADATA),
  ...Object.keys(CASE_LAW_METADATA),
];

const formatValue = (value: MetadataValue): string =>
  typeof value === 'string' ? value : value.join(LIST_SEPARATOR);

/** Une clé hors de la liste de sa source n'est pas transmise, même lue par erreur */
const metadataLines = ({ documentType, metadata }: ExplainedDocument): string[] =>
  Object.entries(metadataLabelsOf(documentType)).flatMap(([key, label]) => {
    const value = metadata[key];
    return value === undefined ? [] : [`${label} : ${formatValue(value)}`];
  });

const headerLines = (document: ExplainedDocument): string[] => [
  `Type : ${DOCUMENT_TYPE_LABELS[document.documentType]}`,
  ...(document.nature ? [`Nature : ${document.nature}`] : []),
  ...(document.parentTextTitles.length > 0
    ? [`Texte parent : ${document.parentTextTitles.join(LIST_SEPARATOR)}`]
    : []),
];

/** `[n]` est la position du document dans la sélection, à partir de 1 */
const renderDocument = (document: ExplainedDocument, index: number): string =>
  [
    `[${index + 1}] ${document.title}`,
    ...headerLines(document),
    ...metadataLines(document),
    '',
    document.content,
  ].join(LINE_SEPARATOR);

export const renderDocuments = (documents: readonly ExplainedDocument[]): string =>
  documents.map(renderDocument).join(DOCUMENT_SEPARATOR);
