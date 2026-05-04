import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { AnyRecord, GeneratedProject } from "../types";
import { formatArea, formatRub } from "../utils/format";

export function OptimizationPage({ project }: { project: GeneratedProject | null }) {
  if (!project) {
    return <div className="empty-state">Сначала сформируйте финансовую модель, чтобы увидеть оптимизацию.</div>;
  }

  const optimization = project.optimization;
  const recommendations = Array.isArray(optimization.recommendations) ? optimization.recommendations : [];

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard title="Требуемое снижение бюджета" value={formatRub(optimization.required_budget_reduction_for_market_price)} tone="yellow" />
        <MetricCard title="Целевая СМР за м²" value={formatRub(optimization.required_cmr_cost_per_m2_for_market_price)} />
        <MetricCard title="Нужная продаваемая площадь" value={formatArea(optimization.required_sellable_area_for_market_price)} />
        <MetricCard title="Цена для целевой маржи" value={formatRub(optimization.required_sale_price_for_target_margin)} tone="green" />
      </section>

      <section className="panel accent-panel">
        <div className="card-heading">
          <h2>Что нужно для прохождения проекта по рынку</h2>
          <p>Агент сравнивает текущую экономику с рыночным ориентиром и целевой маржей.</p>
        </div>
        <div className="insight-grid">
          <Insight label="Разница к рынку" value={formatRub(optimization.gap_to_market_price)} />
          <Insight label="Рыночный ориентир" value={formatRub(project.tep.market_price_per_m2)} />
          <Insight label="Рекомендованная цена" value={formatRub(project.tep.recommended_price_per_m2)} />
        </div>
      </section>

      <section className="panel">
        <div className="card-heading">
          <h2>Рекомендации агента</h2>
          <p>Практические направления оптимизации бюджета, продукта и цены.</p>
        </div>
        {recommendations.length ? (
          <ul className="action-list">
            {recommendations.map((item, index) => (
              <li key={index}>{String(item)}</li>
            ))}
          </ul>
        ) : (
          <DataTable rows={[optimization as AnyRecord]} />
        )}
      </section>
    </div>
  );
}

function Insight({ label, value }: { label: string; value: string }) {
  return (
    <div className="insight">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
