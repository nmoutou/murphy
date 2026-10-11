import { describe, expect, it } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Workspace from '@/features/workspace/Workspace';

const GROUP_SELECTOR = '.dv-groupview';

const closeButton = (title: string) =>
  screen.getByRole('button', { name: `Fermer l'onglet ${title}` });

const queryCloseButton = (title: string) =>
  screen.queryByRole('button', { name: `Fermer l'onglet ${title}` });

const renderWorkspace = () => {
  const { container } = render(<Workspace />);
  return { groupCount: () => container.querySelectorAll(GROUP_SELECTOR).length };
};

const closeTabs = async (...titles: string[]) => {
  for (const title of titles) await userEvent.click(closeButton(title));
};

describe('Workspace', () => {
  it('opens Recherche, Graphe and Résumé in one group, Recherche active', () => {
    const { groupCount } = renderWorkspace();

    expect(groupCount()).toBe(1);
    for (const title of ['Recherche', 'Graphe', 'Résumé']) {
      expect(closeButton(title)).toBeInTheDocument();
    }
    expect(screen.getByRole('region', { name: 'Recherche' })).toHaveClass('dv-active-group');
  });

  it('gives each tab its full title as a tooltip', () => {
    renderWorkspace();

    expect(closeButton('Résumé').closest('[title]')).toHaveAttribute('title', 'Résumé');
  });

  it('reopens a closed fixed tab from the group menu', async () => {
    renderWorkspace();
    await closeTabs('Graphe');

    await userEvent.click(screen.getByRole('button', { name: 'Rouvrir un onglet' }));
    await userEvent.click(screen.getByRole('button', { name: 'Ouvrir Graphe' }));

    expect(closeButton('Graphe')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Graphe' })).not.toBeInTheDocument();
  });

  it('says so when every fixed tab is open', async () => {
    renderWorkspace();

    await userEvent.click(screen.getByRole('button', { name: 'Rouvrir un onglet' }));

    expect(screen.getByText('Tous les onglets sont ouverts.')).toBeInTheDocument();
  });

  it('offers the closed tabs once the workspace is empty', async () => {
    renderWorkspace();

    await closeTabs('Recherche', 'Graphe', 'Résumé');
    const watermark = screen.getByText(/Aucun onglet ouvert/).parentElement;
    if (!watermark) throw new Error('The watermark has no container');
    await userEvent.click(within(watermark).getByRole('button', { name: 'Ouvrir Recherche' }));

    expect(queryCloseButton('Recherche')).toBeInTheDocument();
  });
});
