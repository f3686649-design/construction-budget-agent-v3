import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../components/ChartCard";
import { DataTable } from "../components/DataTable";
import type { AnyRecord, GeneratedProject } from "../types";
import { formatPercent, formatRub, statusByDscr, statusByMargin, toNumber } from "../utils/format";

const SCENARIO_NAMES: Record<string, string> = {
  base: "Базовый",
  optimistic: "Оптимистичный",
  stress: "Стресс"
};

export function ScenariosPage({ project }: { project: GeneratedProject | null }) {
  if (!project) {
    return <div className="empty-state">Сначала сформируйте финансовую модель, чтобы увидеть сценарии.</div>;
  }

  const rows: AnyRecord[] = project.scenarios.map((row) => ({
    ...row,
    scenario_name: SCENARIO_NAMES[String(row.scenario ?? row.scenario_code)] ?? String(row.scenario ?? "Сценарий"),
    margin_status: marginLabel(row.margin_after_interest),
    dscr_status: dscrLabel(row.minimum_dscr_after_sales_start)
  }));
  const chartRows = rows.map((row) => ({
    name: row.scenario_name,
    profit: toNumber(row.profit_after_interest),
    margin: toNumber(row.margin_after_interest) * 100
  }));

  return (
    <div className="page-stack">
      <div className="scenario-grid">
        {rows.map((row) => (
          <article className={`scenario-card tone-${statusByMargin(row.margin_after_interest)}`} key={String(row.scenario_name)}>
            <span>{String(row.scenario_name)}</span>
            <strong>{formatRub(row.profit_after_interest)}</strong>
            <p>Маржа: {formatPercent(row.margin_after_interest)}</p>
            <p>DSCR: {String(row.minimum_dscr_after_sales_start ?? "нет данных")}</p>
          </article>
        ))}
      </div>

      <div className="grid two">
        <ChartCard title="Прибыль по сценариям" subtitle="После процентов">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis tickFormatter={(value) => `${Math.round(Number(value) / 1_000_000)} млн`} />
              <Tooltip formatter={(value) => formatRub(value)} />
              <Bar dataKey="profit" fill="#2f6f6d" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard title="Маржа по сценариям" subtitle="Цветовая оценка: плохо, средне, хорошо">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartRows}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis tickFormatter={(value) => `${value}%`} />
              <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
              <Bar dataKey="margin" fill="#d18f45" radius={[8, 8, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      </div>

      <section className="panel">
        <div className="card-heading">
          <h2>Таблица сценариев</h2>
          <p>Базовый, оптимистичный и стресс-сценарий с оценкой маржи и DSCR.</p>
        </div>
        <DataTable
          rows={rows as AnyRecord[]}
          columns={[
            "scenario_name",
            "revenue",
            "total_budget",
            "profit_after_interest",
            "margin_after_interest",
            "max_credit_balance",
            "total_equity_required",
            "minimum_dscr_after_sales_start",
            "months_below_1_2",
            "margin_status",
            "dscr_status"
          ]}
          labels={{ scenario_name: "Сценарий", margin_status: "Оценка маржи", dscr_status: "Оценка DSCR" }}
        />
      </section>
    </div>
  );
}

function marginLabel(value: unknown): string {
  const status = statusByMargin(value);
  if (status === "green") return "хорошо";
  if (status === "yellow") return "средне";
  return "плохо";
}

function dscrLabel(value: unknown): string {
  return statusByDscr(value) === "red" ? "риск" : "норма";
}
