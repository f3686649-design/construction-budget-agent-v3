import { Area, AreaChart, Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../components/ChartCard";
import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { GeneratedProject } from "../types";
import { formatPercent, formatRub, toNumber } from "../utils/format";

export function GprPage({ project }: { project: GeneratedProject | null }) {
  if (!project) {
    return <div className="empty-state">Сначала сформируйте финансовую модель, чтобы увидеть ГПР.</div>;
  }

  const rows = project.gpr.map((row, index) => {
    const amount = toNumber(row.amount ?? row["Сумма"]);
    const accumulated = toNumber(row.accumulated ?? row["Накопительно"]);
    return {
      month: row.month ?? index + 1,
      amount,
      accumulated,
      readiness_value: toNumber(project.budget.total_budget) ? accumulated / toNumber(project.budget.total_budget) : 0,
      readiness: formatPercent(toNumber(project.budget.total_budget) ? accumulated / toNumber(project.budget.total_budget) : 0)
    };
  });
  const peak = rows.reduce((max, row) => (row.amount > max.amount ? row : max), rows[0] ?? { month: 0, amount: 0 });
  const average = rows.length ? rows.reduce((sum, row) => sum + row.amount, 0) / rows.length : 0;

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard title="Срок строительства" value={`${rows.length} мес.`} />
        <MetricCard title="Пиковый месяц CAPEX" value={`Месяц ${peak.month}`} subtitle={formatRub(peak.amount)} tone="yellow" />
        <MetricCard title="Средний CAPEX в месяц" value={formatRub(average)} />
        <MetricCard title="Готовность к финалу" value={formatPercent(rows.at(-1)?.readiness_value ?? 0)} tone="green" />
      </section>

      <div className="grid two">
        <ChartCard title="CAPEX по месяцам" subtitle="Помесячное освоение бюджета">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(value) => `${Math.round(Number(value) / 1_000_000)} млн`} />
              <Tooltip formatter={(value) => formatRub(value)} labelFormatter={(label) => `Месяц ${label}`} />
              <Bar dataKey="amount" fill="#315c72" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Накопленный CAPEX" subtitle="S-curve готовности проекта">
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(value) => `${Math.round(Number(value) / 1_000_000)} млн`} />
              <Tooltip formatter={(value) => formatRub(value)} labelFormatter={(label) => `Месяц ${label}`} />
              <Area type="monotone" dataKey="accumulated" stroke="#2f6f6d" fill="#d9ece5" />
            </AreaChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <section className="panel">
        <div className="card-heading">
          <h2>Этапы работ и помесячный ГПР</h2>
          <p>Для React-кабинета отображается помесячный график освоения CAPEX.</p>
        </div>
        <DataTable rows={rows} columns={["month", "amount", "accumulated", "readiness"]} labels={{ readiness: "% готовности" }} />
      </section>
    </div>
  );
}
