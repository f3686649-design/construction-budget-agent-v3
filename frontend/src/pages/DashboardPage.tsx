import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { MetricCard } from "../components/MetricCard";
import { ChartCard } from "../components/ChartCard";
import type { GeneratedProject, PageKey } from "../types";
import { formatPercent, formatRub, statusByDscr, statusByMargin, toNumber } from "../utils/format";

interface DashboardPageProps {
  project: GeneratedProject | null;
  onNavigate: (page: PageKey) => void;
}

export function DashboardPage({ project, onNavigate }: DashboardPageProps) {
  if (!project) {
    return (
      <section className="empty-state hero-empty">
        <p className="eyebrow">Старт работы</p>
        <h2>Создайте новый расчёт во вкладке «Новый расчёт».</h2>
        <p>После расчёта здесь появятся бюджет, выручка, прибыль, кредит, DSCR и ключевые риски проекта.</p>
        <button className="primary-button" type="button" onClick={() => onNavigate("new")}>
          Перейти к новому расчёту
        </button>
      </section>
    );
  }

  const summary = project.summary;
  const budgetByChapters = (project.detailed_budget.chapter_totals ?? []).map((row) => ({
    name: String(row["Глава"] ?? row["chapter"] ?? "Глава"),
    value: toNumber(row["Сумма"] ?? row["amount"])
  }));

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard title="Итоговый бюджет" value={formatRub(summary.total_budget)} />
        <MetricCard title="СМР" value={formatRub(project.budget.cmr)} />
        <MetricCard title="Выручка" value={formatRub(summary.revenue)} tone="green" />
        <MetricCard title="Прибыль" value={formatRub(summary.profit)} tone={statusByMargin(summary.margin)} />
        <MetricCard title="Маржа" value={formatPercent(summary.margin)} tone={statusByMargin(summary.margin)} />
        <MetricCard title="Пик кредита" value={formatRub(summary.max_credit_balance)} />
        <MetricCard title="Собственные средства" value={formatRub(summary.total_equity_required)} tone="yellow" />
        <MetricCard title="Minimum DSCR" value={summary.minimum_dscr ? String(summary.minimum_dscr) : "нет данных"} tone={statusByDscr(summary.minimum_dscr)} />
      </section>

      <div className="grid two">
        <ChartCard title="Бюджет по главам" subtitle="Сводная структура затрат проекта">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={budgetByChapters}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis tickFormatter={(value) => `${Math.round(Number(value) / 1_000_000)} млн`} />
              <Tooltip formatter={(value) => formatRub(value)} />
              <Bar dataKey="value" fill="#2f6f6d" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Ключевые выводы" subtitle="Что стоит проверить в первую очередь">
          <div className="risk-list">
            {project.risks.slice(0, 5).map((risk, index) => (
              <div className="risk-item" key={index}>
                <span className={`risk-dot ${String(risk.level ?? risk["Уровень"] ?? "").toLowerCase()}`} />
                <p>{String(risk.message ?? risk["Риск"] ?? risk["Комментарий"] ?? "Проверьте риск проекта.")}</p>
              </div>
            ))}
            {!project.risks.length ? <p className="muted">Критичных рисков не найдено.</p> : null}
          </div>
        </ChartCard>
      </div>
    </div>
  );
}
