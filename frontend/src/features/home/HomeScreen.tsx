'use client';

import Logo from '@/components/icons/Logo';
import SearchBar from '@/components/ui/SearchBar';
import { useSearchStore } from '@/stores/searchStore';

export default function HomeScreen() {
  const submit = useSearchStore((state) => state.submit);

  return (
    <main className="flex flex-1 flex-col items-center justify-center bg-primary">
      <div className="px-16 pb-8">
        <Logo />
      </div>
      <SearchBar variant="centered" onSubmit={submit} />
    </main>
  );
}
