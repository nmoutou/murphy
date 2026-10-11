interface InForceDotProps {
  readonly isInForce?: boolean;
}

/** Sans statut, comme pour une décision, ni pastille ni emplacement : le titre s'aligne sur l'extrait */
export default function InForceDot({ isInForce }: InForceDotProps) {
  if (isInForce === undefined) return null;
  const label = isInForce ? 'En vigueur' : 'Pas en vigueur';
  const color = isInForce ? 'bg-in-force' : 'bg-not-in-force';

  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      className={`size-2 shrink-0 rounded-full ${color}`}
    />
  );
}
