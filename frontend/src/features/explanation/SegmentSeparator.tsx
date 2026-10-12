/** La sélection a changé : le LLM ne voit plus rien de ce qui précède */
export default function SegmentSeparator() {
  return (
    <li role="separator" className="flex items-center gap-3 text-xs opacity-70">
      <span className="h-px flex-1 bg-secondary" />
      Nouvelle sélection
      <span className="h-px flex-1 bg-secondary" />
    </li>
  );
}
