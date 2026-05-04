import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../components/ChartCard";
import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { GeneratedProject } from "../types";
import { formatArea, formatRub, toNumber } from "../utils/format";

export function SalesPage({ project }: { project: GeneratedProject | null }) {
  if (!project) {
    return <div className="empty-state">Сначала сформируйте финансовую модель, чтобы увидеть план продаж.</div>;
  }

  const rows = project.sales.map((row, index) => ({
    month: row.month ?? index + 1,
    sold_area: toNumber(row.sold_area),
    revenue: toNumber(row.revenue)
  }));
  const totalArea = rows.reduce((sum, row) => sum + row.sold_area, 0);
  const totalRevenue = rows.reduce((sum, row) => sum + row.revenue, 0);

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard title="Продаваемая площадь" value={formatArea(project.tep.sellable_area)} />
        <MetricCard title="Продано по плану" value={formatArea(totalArea)} tone="green" />
        <MetricCard title="Выручка проекта" value={formatRub(totalRevenue)} />
        <MetricCard title="Цена продажи м²" value={formatRub(project.tep.sale_price_per_m2)} />
      </section>

      <div className="grid two">
        <ChartCard title="Продажи по месяцам" subtitle="Помесячная реализация NSA">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(value) => `${Math.round(Number(value))} м²`} />
              <Tooltip formatter={(value) => formatArea(value)} labelFormatter={(label) => `Месяц ${label}`} />
              <Bar dataKey="sold_area" fill="#d18f45" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Выручка по месяцам" subtitle="Поступления от продаж">
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={rows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(value) => `${Math.round(Number(value) / 1_000_000)} млн`} />
              <Tooltip formatter={(value) => formatRub(value)} labelFormatter={(label) => `Месяц ${label}`} />
              <Line type="monotone" dataKey="revenue" stroke="#2f6f6d" strokeWidth={3} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <section className="panel">
        <div className="card-heading">
          <h2>Помесячный план продаж</h2>
          <p>Площадь продаж и выручка по каждому месяцу.</p>
        </div>
        <DataTable rows={rows} columns={["month", "sold_area", "revenue"]} />
      </section>
    </div>
  );
}
