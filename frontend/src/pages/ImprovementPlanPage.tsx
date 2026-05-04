import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { AnyRecord, GeneratedProject } from "../types";
import { formatRub } from "../utils/format";

export function ImprovementPlanPage({ project }: { project: GeneratedProject | null }) {
  if (!project) {
    return <div className="empty-state">Сначала сформируйте финансовую модель, чтобы увидеть план улучшений.</div>;
  }

  const plan = project.improvement_plan;
  const items = Array.isArray(plan.improvement_items) ? (plan.improvement_items as AnyRecord[]) : [];

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard title="Целевое снижение бюджета" value={formatRub(plan.target_budget_reduction)} tone="yellow" />
        <MetricCard title="Количество статей экономии" value={String(items.length)} />
        <MetricCard title="Приоритетных действий" value={String(Array.isArray(plan.priority_actions) ? plan.priority_actions.length : 0)} tone="green" />
      </section>

      <section className="panel">
        <div className="card-heading">
          <h2>Потенциал экономии по статьям</h2>
          <p>Статьи, потенциал, сложность, риск качества и приоритет.</p>
        </div>
        <DataTable rows={items} />
      </section>

      <div className="grid two">
        <TextBlock title="Планировочные улучшения" items={plan.planning_improvements} />
        <TextBlock title="Коммерческие улучшения" items={plan.sales_improvements} />
        <TextBlock title="Финансовые улучшения" items={plan.financing_improvements} />
        <TextBlock title="Приоритетные действия" items={plan.priority_actions} ordered />
      </div>
    </div>
  );
}

function TextBlock({ title, items, ordered = false }: { title: string; items: unknown; ordered?: boolean }) {
  const list = Array.isArray(items) ? items.map(String) : [];
  return (
    <section className="panel">
      <div className="card-heading">
        <h2>{title}</h2>
      </div>
      {list.length ? (
        ordered ? (
          <ol className="action-list">
            {list.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ol>
        ) : (
          <ul className="action-list">
            {list.map((item, index) => (
              <li key={index}>{item}</li>
            ))}
          </ul>
        )
      ) : (
        <p className="muted">Рекомендации не сформированы.</p>
      )}
    </section>
  );
}
