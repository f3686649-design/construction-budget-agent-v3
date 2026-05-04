import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { GeneratedProject } from "../types";
import { formatRub } from "../utils/format";

export function BudgetPage({ project }: { project: GeneratedProject | null }) {
  if (!project) {
    return <EmptyPage text="Сначала сформируйте финансовую модель, чтобы увидеть бюджет." />;
  }

  const items = project.detailed_budget.items ?? [];
  const chapters = project.detailed_budget.chapter_totals ?? [];

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard title="Итоговый бюджет" value={formatRub(project.budget.total_budget)} />
        <MetricCard title="СМР" value={formatRub(project.budget.cmr)} />
        <MetricCard title="Проектирование" value={formatRub(project.budget.design)} />
        <MetricCard title="Резерв" value={formatRub(project.budget.reserve)} tone="yellow" />
      </section>

      <section className="panel">
        <div className="card-heading">
          <h2>Итоги по главам</h2>
          <p>Сводная структура бюджета по укрупнённым главам.</p>
        </div>
        <DataTable rows={chapters} />
      </section>

      <section className="panel">
        <div className="card-heading">
          <h2>Детальный бюджет</h2>
          <p>Статьи, ставки, суммы и разбивка на материалы, работы, механизмы и накладные.</p>
        </div>
        <DataTable rows={items} />
      </section>
    </div>
  );
}

function EmptyPage({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}
