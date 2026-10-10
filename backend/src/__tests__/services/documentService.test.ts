import { readDocument } from '../../services/documentService';
import { getInfraClients } from '../../infra/clients';
import { RagError } from '../../types/rag';

jest.mock('../../infra/clients', () => {
  const clients = { mongo: { fetchDocument: jest.fn() } };
  return { getInfraClients: () => clients };
});

const DOCUMENT = { identifier: 'LEGIARTI000006419304', title: 'Code civil, art. 2224', content: 'Article 2224. Cinq ans.' };

const { mongo } = getInfraClients();

describe('readDocument', () => {
  it('serves the identity, title and text of the document', async () => {
    jest.mocked(mongo.fetchDocument).mockResolvedValue(DOCUMENT);

    await expect(readDocument(DOCUMENT.identifier)).resolves.toEqual(DOCUMENT);
    expect(mongo.fetchDocument).toHaveBeenCalledWith(DOCUMENT.identifier);
  });

  it('reports an unknown identifier as DOCUMENT_NOT_FOUND', async () => {
    jest.mocked(mongo.fetchDocument).mockResolvedValue(undefined);

    const reading = readDocument('LEGIARTI0');

    await expect(reading).rejects.toBeInstanceOf(RagError);
    await expect(reading).rejects.toMatchObject({ code: 'DOCUMENT_NOT_FOUND' });
  });
});
