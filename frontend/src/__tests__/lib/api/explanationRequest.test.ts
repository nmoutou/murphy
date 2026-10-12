import { describe, expect, it } from 'vitest';
import type { ExplanationUIMessage } from '@/lib/api/explanationRequest';
import { startsSegment, toExplanationRequest } from '@/lib/api/explanationRequest';
import type { SelectionEntry } from '@/stores/selectionStore';

const entryOf = (identifier: string): SelectionEntry => ({
  identifier,
  title: `Titre ${identifier}`,
  documentType: 'article',
  contentLength: 10,
});

let nextId = 0;

const question = (text: string, ...identifiers: string[]): ExplanationUIMessage => ({
  id: `m${nextId++}`,
  role: 'user',
  parts: [{ type: 'text', text }],
  metadata: { sources: identifiers.map(entryOf) },
});

const answer = (text: string, isInterrupted?: boolean): ExplanationUIMessage => ({
  id: `m${nextId++}`,
  role: 'assistant',
  parts: text ? [{ type: 'text', text }] : [],
  metadata: isInterrupted ? { sources: [], isInterrupted } : undefined,
});

describe('toExplanationRequest', () => {
  it('sends the whole conversation while the selection does not change', () => {
    const messages = [
      question('Résume.', 'A', 'B'),
      answer('Voici [1].'),
      question('Et [2] ?', 'A', 'B'),
    ];

    expect(toExplanationRequest(messages)).toEqual({
      selection: ['A', 'B'],
      messages: [
        { role: 'user', content: 'Résume.' },
        { role: 'assistant', content: 'Voici [1].' },
        { role: 'user', content: 'Et [2] ?' },
      ],
    });
  });

  it('sends only the segment opened by the last change of selection', () => {
    const messages = [
      question('Résume.', 'A', 'B'),
      answer('Voici.'),
      question('Résume.', 'B'),
      answer('Celui-ci.'),
      question('Pourquoi ?', 'B'),
    ];

    expect(toExplanationRequest(messages)).toEqual({
      selection: ['B'],
      messages: [
        { role: 'user', content: 'Résume.' },
        { role: 'assistant', content: 'Celui-ci.' },
        { role: 'user', content: 'Pourquoi ?' },
      ],
    });
  });

  it('keeps an interrupted answer, drops an empty one, keeps a question left unanswered', () => {
    const messages = [
      question('Un', 'A'),
      answer('Début', true),
      question('Deux', 'A'),
      answer(''),
      question('Trois', 'A'),
    ];

    expect(toExplanationRequest(messages).messages).toEqual([
      { role: 'user', content: 'Un' },
      { role: 'assistant', content: 'Début' },
      { role: 'user', content: 'Deux' },
      { role: 'user', content: 'Trois' },
    ]);
  });
});

describe('startsSegment', () => {
  it('marks a question whose sources differ from the previous question, not the first one', () => {
    const messages = [
      question('a', 'A'),
      answer('b'),
      question('c', 'A'),
      question('d', 'B', 'A'),
      question('e', 'A', 'B'),
    ];

    expect(messages.map((_message, index) => startsSegment(messages, index))).toEqual([
      false,
      false,
      false,
      true,
      true,
    ]);
  });
});
