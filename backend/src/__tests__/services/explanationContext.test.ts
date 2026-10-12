import type { ExplainedDocument } from '../../types/explanation';
import { EXPLAINED_METADATA_KEYS, renderDocuments } from '../../services/explanationContext';

const ARTICLE: ExplainedDocument = {
  identifier: 'LEGIARTI1',
  title: 'Article L2122-22',
  content: 'Le maire peut, par délégation du conseil municipal…',
  documentType: 'article',
  parentTextTitles: ['Code général des collectivités territoriales'],
  metadata: { statut: 'ABROGE', versions_a_venir: ['2030-01-01', '2031-01-01'] },
};

const DECISION: ExplainedDocument = {
  identifier: 'JURITEXT2',
  title: 'Cour de cassation, 6 mars 2008',
  content: 'LA COUR…',
  documentType: 'decision',
  nature: 'ARRET',
  parentTextTitles: [],
  metadata: { juridiction: 'Cour de cassation', president: 'M. X', avocats: 'SCP Y', statut: 'VIGUEUR' },
};

describe('renderDocuments', () => {
  it('numbers the documents in the order of the selection, from [1]', () => {
    const rendered = renderDocuments([DECISION, ARTICLE]);

    expect(rendered.indexOf('[1] Cour de cassation')).toBeGreaterThanOrEqual(0);
    expect(rendered.indexOf('[2] Article L2122-22')).toBeGreaterThan(rendered.indexOf('[1]'));
  });

  it('labels the metadata in French, joins a list, and gives the parent text and the full text', () => {
    const rendered = renderDocuments([ARTICLE]);

    expect(rendered).toBe([
      '[1] Article L2122-22',
      'Type : Article',
      'Texte parent : Code général des collectivités territoriales',
      'Statut de vigueur : ABROGE',
      'Versions à venir : 2030-01-01, 2031-01-01',
      '',
      'Le maire peut, par délégation du conseil municipal…',
    ].join('\n'));
  });

  it('never passes on the identity of the judges or the lawyers, nor a key outside its source list', () => {
    const rendered = renderDocuments([DECISION]);

    expect(rendered).toContain('Nature : ARRET');
    expect(rendered).toContain('Juridiction : Cour de cassation');
    expect(rendered).not.toContain('M. X');
    expect(rendered).not.toContain('SCP Y');
    expect(rendered).not.toContain('Statut de vigueur');
  });
});

describe('EXPLAINED_METADATA_KEYS', () => {
  it('names the whitelist of both sources and none of the excluded keys', () => {
    expect(EXPLAINED_METADATA_KEYS).toEqual(expect.arrayContaining(['statut', 'date_debut', 'juridiction', 'ecli']));
    for (const excluded of ['president', 'rapporteur', 'rapporteur_public', 'avocats', 'ancien_id', 'origine']) {
      expect(EXPLAINED_METADATA_KEYS).not.toContain(excluded);
    }
  });
});
