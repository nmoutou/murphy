const PERCENT = 100;

const TRACK_STYLE =
  'h-2 w-full appearance-none overflow-hidden rounded-full bg-secondary [&::-webkit-meter-bar]:rounded-full [&::-webkit-meter-bar]:border-0 [&::-webkit-meter-bar]:bg-secondary';
const FILL_STYLE = {
  normal: '[&::-moz-meter-bar]:bg-tertiary [&::-webkit-meter-optimum-value]:bg-tertiary',
  over: '[&::-moz-meter-bar]:bg-not-in-force [&::-webkit-meter-optimum-value]:bg-not-in-force',
} as const;

interface BudgetGaugeProps {
  /** La somme des `contentLength` de la sélection */
  readonly used: number;
  readonly budget: number;
}

const describeUsage = (percent: number, isOver: boolean): string =>
  isOver
    ? `Budget dépassé (${percent} %) : retirez un document.`
    : `${percent} % du budget de lecture`;

/** Indicative : seul le serveur, qui compte aussi le prompt et la conversation, fait foi */
export default function BudgetGauge({ used, budget }: BudgetGaugeProps) {
  const percent = Math.round((used / budget) * PERCENT);
  const isOver = used > budget;
  const description = describeUsage(percent, isOver);

  return (
    <div className="flex flex-col gap-1">
      <meter
        aria-label="Budget de lecture"
        aria-valuetext={description}
        min={0}
        max={budget}
        value={Math.min(used, budget)}
        className={`${TRACK_STYLE} ${isOver ? FILL_STYLE.over : FILL_STYLE.normal}`}
      />
      <p className={`text-xs ${isOver ? 'text-not-in-force' : ''}`}>{description}</p>
    </div>
  );
}
