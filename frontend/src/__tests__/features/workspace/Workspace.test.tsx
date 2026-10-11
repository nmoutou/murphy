import { describe, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { DockviewApi } from 'dockview-react';
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

const narrowScreen = () => {
  const narrowQuery = window.matchMedia('(max-width: 0px)');
  vi.spyOn(window, 'matchMedia').mockReturnValue({ ...narrowQuery, matches: true });
};

describe('Workspace', () => {
  it('opens Résultats, Graphe and Explication in one group, Résultats active', () => {
    const { groupCount } = renderWorkspace();

    expect(groupCount()).toBe(1);
    for (const title of ['Résultats', 'Graphe', 'Explication']) {
      expect(closeButton(title)).toBeInTheDocument();
    }
    expect(screen.getByRole('region', { name: 'Résultats' })).toHaveClass('dv-active-group');
  });

  it('gives each tab its full title as a tooltip', () => {
    renderWorkspace();

    expect(closeButton('Explication').closest('[title]')).toHaveAttribute('title', 'Explication');
  });

  it('moves the active tab into a new group on the right when splitting', async () => {
    const addGroup = vi.spyOn(DockviewApi.prototype, 'addGroup');
    const { groupCount } = renderWorkspace();

    await userEvent.click(screen.getByRole('button', { name: 'Scinder' }));

    expect(groupCount()).toBe(2);
    expect(addGroup).toHaveBeenCalledWith(expect.objectContaining({ direction: 'right' }));
    expect(screen.getByRole('region', { name: 'Résultats' })).toHaveClass('dv-active-group');
    expect(screen.getAllByRole('button', { name: 'Scinder' })).toHaveLength(2);
  });

  it('splits below on a narrow screen', async () => {
    const addGroup = vi.spyOn(DockviewApi.prototype, 'addGroup');
    narrowScreen();
    renderWorkspace();

    await userEvent.click(screen.getByRole('button', { name: 'Scinder' }));

    expect(addGroup).toHaveBeenCalledWith(expect.objectContaining({ direction: 'below' }));
  });

  it('cannot split a group with a single tab', async () => {
    renderWorkspace();

    await closeTabs('Graphe', 'Explication');

    expect(screen.getByRole('button', { name: 'Scinder' })).toBeDisabled();
  });

  it('reopens a closed fixed tab from the group menu', async () => {
    renderWorkspace();
    await closeTabs('Graphe');

    await userEvent.click(screen.getByRole('button', { name: 'Rouvrir un onglet' }));
    await userEvent.click(screen.getByRole('button', { name: 'Graphe' }));

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

    await closeTabs('Résultats', 'Graphe', 'Explication');
    const watermark = screen.getByText(/Aucun onglet ouvert/).parentElement;
    if (!watermark) throw new Error('The watermark has no container');
    await userEvent.click(within(watermark).getByRole('button', { name: 'Résultats' }));

    expect(queryCloseButton('Résultats')).toBeInTheDocument();
  });
});
