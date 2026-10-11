'use client';

import HomeScreen from '@/features/home/HomeScreen';
import ErrorDialog from '@/features/errors/ErrorDialog';
import { useSearchStore } from '@/stores/searchStore';
import Workspace from './Workspace';

/** Deux états d'un même écran : la question ne passe jamais par l'URL */
export default function SearchScreen() {
  // Même en échec, la première recherche ouvre l'espace de travail
  const hasSearched = useSearchStore((state) => state.status !== 'idle');

  return (
    <>
      {hasSearched ? <Workspace /> : <HomeScreen />}
      <ErrorDialog />
    </>
  );
}
