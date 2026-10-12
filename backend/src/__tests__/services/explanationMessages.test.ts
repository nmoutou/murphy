import { countCodePoints, mergeConsecutiveUserMessages } from '../../services/explanationMessages';

describe('mergeConsecutiveUserMessages', () => {
  it('merges a question left without an answer into the next one', () => {
    const merged = mergeConsecutiveUserMessages([
      { role: 'user', content: 'Résume.' },
      { role: 'assistant', content: 'Voici.' },
      { role: 'user', content: 'Première ?' },
      { role: 'user', content: 'Seconde ?' },
    ]);

    expect(merged).toEqual([
      { role: 'user', content: 'Résume.' },
      { role: 'assistant', content: 'Voici.' },
      { role: 'user', content: 'Première ?\n\nSeconde ?' },
    ]);
  });

  it('leaves an alternating conversation as is', () => {
    const messages = [{ role: 'user', content: 'a' }, { role: 'assistant', content: 'b' }] as const;

    expect(mergeConsecutiveUserMessages(messages)).toEqual(messages);
  });
});

describe('countCodePoints', () => {
  it('counts an astral character once, as the ingestion does', () => {
    expect(countCodePoints('Arrêté 📜')).toBe(8);
  });
});
