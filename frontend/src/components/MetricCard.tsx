interface MetricCardProps {
  title: string;
  value: string;
  subtitle?: string;
  tone?: "green" | "yellow" | "red" | "blue";
}

export function MetricCard({ title, value, subtitle, tone = "blue" }: MetricCardProps) {
  return (
    <article className={`metric-card tone-${tone}`}>
      <span>{title}</span>
      <strong>{value}</strong>
      {subtitle ? <small>{subtitle}</small> : null}
    </article>
  );
}
