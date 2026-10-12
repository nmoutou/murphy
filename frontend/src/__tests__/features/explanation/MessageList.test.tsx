import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MessageList from '@/features/explanation/MessageList';
import type { ExplanationUIMessage } from '@/lib/api/explanationRequest';
import type { SelectionEntry } from '@/stores/selectionStore';

const entryOf = (identifier: string): SelectionEntry => ({
  identifier,
  title: `Titre ${identifier}`,
  documentType: 'article',
  isInForce: true,
  contentLength: 10,
});

const question = (id: string, text: string, ...identifiers: string[]): ExplanationUIMessage => ({
  id,
  role: 'user',
  parts: [{ type: 'text', text }],
  metadata: { sources: identifiers.map(entryOf) },
});

const answer = (id: string, text: string, isInterrupted = false): ExplanationUIMessage => ({
  id,
  role: 'assistant',
  parts: [{ type: 'text', text }],
  metadata: isInterrupted ? { sources: [], isInterrupted } : undefined,
});

const renderList = (messages: ExplanationUIMessage[]) => {
  const onOpenDocument = vi.fn();
  render(<MessageList messages={messages} onOpenDocument={onOpenDocument} />);
  return { onOpenDocument };
};

describe('MessageList', () => {
  it('lists the sources of a question as they were, in their order', async () => {
    renderList([question('q1', 'Résume.', 'A', 'B')]);

    await userEvent.click(screen.getByText('Sources (2)'));

    const sources = screen.getByText('Sources (2)').closest('details');
    if (!sources) throw new Error('No sources disclosure');
    expect(
      within(sources)
        .getAllByRole('listitem')
        .map((item) => item.textContent),
    ).toEqual(['1Titre A', '2Titre B']);
  });

  it('renders the answer in Markdown', () => {
    renderList([question('q1', 'Résume.', 'A'), answer('a1', '**Important** : un *texte*.')]);

    expect(screen.getByText('Important').tagName).toBe('STRONG');
  });

  it('opens the document of a reference, the n-th source of the question', async () => {
    const { onOpenDocument } = renderList([
      question('q1', 'Résume.', 'A', 'B'),
      answer('a1', 'Le second texte [2] le dit.'),
    ]);

    await userEvent.click(screen.getByRole('button', { name: '[2]' }));

    expect(onOpenDocument).toHaveBeenCalledExactlyOnceWith(entryOf('B'));
  });

  it('leaves a reference without a source as plain text', () => {
    renderList([question('q1', 'Résume.', 'A'), answer('a1', 'Voir [3].')]);

    expect(screen.queryByRole('button', { name: '[3]' })).not.toBeInTheDocument();
    expect(screen.getByText('Voir [3].')).toBeInTheDocument();
  });

  it('never makes another link of the answer clickable', () => {
    renderList([question('q1', 'Résume.', 'A'), answer('a1', '[ici](https://x.test)')]);

    expect(screen.queryByRole('link')).not.toBeInTheDocument();
    expect(screen.getByText('ici')).toBeInTheDocument();
  });

  it('marks an interrupted answer', () => {
    renderList([question('q1', 'Résume.', 'A'), answer('a1', 'Début', true)]);

    expect(screen.getByText('Réponse interrompue.')).toBeInTheDocument();
  });

  it('separates the questions asked on another selection', () => {
    renderList([
      question('q1', 'Résume.', 'A'),
      answer('a1', 'Voici.'),
      question('q2', 'Et lui ?', 'A'),
      question('q3', 'Résume.', 'A', 'B'),
    ]);

    expect(screen.getAllByRole('separator')).toHaveLength(1);
    const items = screen.getByRole('list', { name: 'Conversation' }).children;
    expect(items[3]).toHaveAttribute('role', 'separator');
  });
});
