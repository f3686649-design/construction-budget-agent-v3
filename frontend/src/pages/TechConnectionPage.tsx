import { ChartCard } from "../components/ChartCard";
import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { GeneratedProject } from "../types";
import { formatRub } from "../utils/format";

interface TechConnectionPageProps {
  project: GeneratedProject | null;
}

const TONE_BY_LEVEL: Record<string, "green" | "yellow" | "red" | "blue"> = {
  ok: "green",
  warning: "yellow",
  critical: "red"
};

export function TechConnectionPage({ project }: TechConnectionPageProps) {
  if (!project) {
    return (
      <section className="empty-state">
        <p>Создайте новый расчёт, чтобы увидеть оценку технического присоединения.</p>
      </section>
    );
  }

  const tech = project.tech_connection ?? {};
  const tone = TONE_BY_LEVEL[String(tech.verdict_level ?? "")] ?? "blue";
  const items = (tech.items ?? []) as Array<Record<string, unknown>>;
  const loads = (tech.loads ?? {}) as Record<string, unknown>;

  return (
    <div className="page-stack">
      {tech.verdict ? (
        <section className={`verdict-banner tone-${tone}`}>
          <span className="verdict-title">Техническое присоединение · ТУ</span>
          <p>{String(tech.verdict)}</p>
          <small>
            {String(tech.cost_source ?? "")} · квартир: {String(tech.apartments ?? "—")} (
            {String(tech.apartments_source ?? "")})
          </small>
        </section>
      ) : null}

      <section className="metric-grid">
        <MetricCard title="Плата за ТП итого" value={formatRub(tech.total_cost)} tone={tone} />
        <MetricCard
          title="Заложено в бюджете"
          value={formatRub(tech.budget_allocation)}
          subtitle="статья «Наружные сети»"
        />
        <MetricCard
          title="Дефицит"
          value={formatRub(tech.deficit)}
          tone={Number(tech.deficit ?? 0) > 0 ? "red" : "green"}
        />
        <MetricCard
          title="Электрическая мощность"
          value={`${String(loads.power_kw ?? "—")} кВт`}
        />
        <MetricCard title="Тепловая нагрузка" value={`${String(loads.heat_gcal_h ?? "—")} Гкал/ч`} />
        <MetricCard
          title="Сроки ТП vs стройка"
          value={`${String(tech.max_lead_time_months ?? "—")} / ${String(tech.construction_months ?? "—")} мес`}
          tone={(tech.schedule_issues as unknown[] | undefined)?.length ? "yellow" : "green"}
          subtitle="макс. срок мероприятий / срок стройки"
        />
      </section>

      <ChartCard title="Ресурсы и стоимость присоединения" subtitle="Нагрузки по нормативам, ставки — региональные допущения (уточнить по фактическим ТУ)">
        <DataTable
          rows={items}
          columns={["resource", "load", "unit", "rate", "cost", "basis", "lead_time_months", "deadline_ok"]}
          labels={{
            resource: "Ресурс",
            load: "Нагрузка",
            unit: "Ед.",
            rate: "Ставка, ₽/ед.",
            cost: "Стоимость, ₽",
            basis: "База расчёта",
            lead_time_months: "Срок ТП, мес",
            deadline_ok: "Вписывается в стройку"
          }}
        />
      </ChartCard>
    </div>
  );
}
