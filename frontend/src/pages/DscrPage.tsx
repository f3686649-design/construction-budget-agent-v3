import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../components/ChartCard";
import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { GeneratedProject } from "../types";
import { formatRub, statusByDscr, toNumber } from "../utils/format";

export function DscrPage({ project }: { project: GeneratedProject | null }) {
  if (!project) {
    return <div className="empty-state">Сначала сформируйте финансовую модель, чтобы увидеть DSCR.</div>;
  }

  const rows = (project.dscr.schedule ?? []).map((row, index) => ({
    month: row.month ?? index + 1,
    sales_receipts: toNumber(row.sales_receipts),
    debt_service: toNumber(row.debt_service),
    dscr: row.dscr === null || row.dscr === undefined ? null : toNumber(row.dscr)
  }));

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard title="Minimum DSCR" value={String(project.dscr.minimum_dscr_after_sales_start ?? "нет данных")} tone={statusByDscr(project.dscr.minimum_dscr_after_sales_start)} />
        <MetricCard title="Месяцев ниже 1.2" value={String(project.dscr.months_below_1_2 ?? 0)} tone={(project.dscr.months_below_1_2 ?? 0) > 0 ? "red" : "green"} />
        <MetricCard title="Долговой сервис" value={formatRub(rows.reduce((sum, row) => sum + row.debt_service, 0))} />
        <MetricCard title="Поступления от продаж" value={formatRub(rows.reduce((sum, row) => sum + row.sales_receipts, 0))} />
      </section>

      <ChartCard title="DSCR по месяцам" subtitle="Порог 1.2 выделен красной линией">
        <ResponsiveContainer width="100%" height={340}>
          <LineChart data={rows}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis domain={[0, "auto"]} />
            <Tooltip labelFormatter={(label) => `Месяц ${label}`} />
            <ReferenceLine y={1.2} stroke="#a43d3d" strokeDasharray="6 6" />
            <Line type="monotone" dataKey="dscr" stroke="#2f6f6d" strokeWidth={3} connectNulls dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <section className="panel">
        <div className="card-heading">
          <h2>Расчёт DSCR</h2>
          <p>Показываются только месячные данные, полученные от backend-модели.</p>
        </div>
        <DataTable rows={rows} />
      </section>
    </div>
  );
}
