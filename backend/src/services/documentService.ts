import type { DocumentContent } from '@murphy/contract/search';
import { getInfraClients } from '../infra/clients';
import { RagError } from '../types/rag';

/**
 * Le texte entier d'un document, servi à la demande (ADR-031 §1)
 * @throws RagError `DOCUMENT_NOT_FOUND` si aucun document ne porte cet identifiant
 */
export const readDocument = async (identifier: string): Promise<DocumentContent> => {
  const document = await getInfraClients().mongo.fetchDocument(identifier);
  if (!document) {
    throw new RagError('request', 'DOCUMENT_NOT_FOUND', `No document has the identifier ${identifier}`);
  }
  return document;
};
