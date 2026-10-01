'use client';

import { useEffect } from 'react';

interface ErrorPageProps {
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
}

/** Error Boundary de la page : un échec de rendu affiche ceci plutôt qu'une page blanche */
export default function ErrorPage({ error, reset }: ErrorPageProps) {
  useEffect(() => {
    console.error('Page rendering failed:', error);
  }, [error]);

  return (
    <main className="min-h-screen w-full flex flex-col justify-center items-center gap-6 p-8 bg-primary text-tertiary">
      <h1 className="text-lg font-semibold">Une erreur est survenue</h1>
      <p>L&apos;application n&apos;a pas pu s&apos;afficher. Vous pouvez réessayer.</p>
      <button
        type="button"
        onClick={reset}
        className="rounded-full bg-quaternary px-4 py-1 text-secondary hover:opacity-80"
      >
        Réessayer
      </button>
    </main>
  );
}
