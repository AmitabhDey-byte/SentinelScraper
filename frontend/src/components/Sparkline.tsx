type SparklineProps = {
  values: (number | null)[];
  positive?: boolean;
};

export function Sparkline({ values, positive = false }: SparklineProps) {
  const clean = values.filter((value): value is number => value !== null);
  if (clean.length < 2) {
    return <span className="sparkline-empty">—</span>;
  }

  const min = Math.min(...clean);
  const max = Math.max(...clean);
  const range = max - min || 1;
  const points = clean
    .map((value, index) => {
      const x = (index / (clean.length - 1)) * 72;
      const y = 22 - ((value - min) / range) * 18;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg className={`sparkline ${positive ? "sparkline-positive" : ""}`} viewBox="0 0 72 24" role="img" aria-label="Price history sparkline">
      <polyline points={points} fill="none" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

