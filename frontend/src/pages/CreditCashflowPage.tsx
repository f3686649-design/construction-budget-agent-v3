import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../components/ChartCard";
import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { GeneratedProject } from "../types";
import { formatRub, toNumber } from "../utils/format";

export function CreditCashflowPage({ project }: { project: GeneratedProject | null }) {
  if (!project) {
    return <div className="empty-state">Сначала сформируйте финансовую модель, чтобы увидеть кредит и ДДС.</div>;
  }

  const creditRows = (project.credit.schedule ?? []).map((row, index) => ({
    month: row.month ?? index + 1,
    drawdown: toNumber(row.drawdown ?? row.credit_drawdown),
    repayment: toNumber(row.repayment),
    interest: toNumber(row.interest),
    closing_balance: toNumber(row.closing_balance)
  }));
  const cashflowRows = project.cashflow.map((row, index) => ({
    month: row.month ?? index + 1,
    sales_receipts: toNumber(row.sales_receipts),
    operating_cashflow_before_financing: toNumber(row.operating_cashflow_before_financing),
    equity_required: toNumber(row.equity_required),
    cumulative_equity_required: toNumber(row.cumulative_equity_required),
    cash_balance_after_financing: toNumber(row.cash_balance_after_financing)
  }));

  return (
    <div className="page-stack">
      <section className="metric-grid">
        <MetricCard title="Пик кредита" value={formatRub(project.credit.max_balance)} />
        <MetricCard title="Начисленные проценты" value={formatRub(project.credit.total_interest)} tone="yellow" />
        <MetricCard title="Собственные средства" value={formatRub(project.economics.total_equity_required)} />
        <MetricCard title="Финальный остаток долга" value={formatRub(creditRows.at(-1)?.closing_balance ?? 0)} tone="green" />
      </section>

      <div className="grid two">
        <ChartCard title="Кредитный график" subtitle="Выборка, проценты, погашение и остаток кредита">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={creditRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(value) => `${Math.round(Number(value) / 1_000_000)} млн`} />
              <Tooltip formatter={(value) => formatRub(value)} labelFormatter={(label) => `Месяц ${label}`} />
              <Bar dataKey="drawdown" fill="#315c72" />
              <Bar dataKey="repayment" fill="#d18f45" />
              <Line dataKey="closing_balance" stroke="#a43d3d" strokeWidth={3} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Потребность в собственных средствах" subtitle="Equity gap после кредитного покрытия">
          <ResponsiveContainer width="100%" height={300}>
            <ComposedChart data={cashflowRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(value) => `${Math.round(Number(value) / 1_000_000)} млн`} />
              <Tooltip formatter={(value) => formatRub(value)} labelFormatter={(label) => `Месяц ${label}`} />
              <Bar dataKey="equity_required" fill="#d18f45" />
              <Line dataKey="cumulative_equity_required" stroke="#2f6f6d" strokeWidth={3} dot={false} />
            </ComposedChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <section className="panel">
        <div className="card-heading">
          <h2>ДДС по месяцам</h2>
          <p>Поступления, операционный поток, собственные средства и остаток после финансирования.</p>
        </div>
        <DataTable rows={cashflowRows} />
      </section>
    </div>
  );
}
