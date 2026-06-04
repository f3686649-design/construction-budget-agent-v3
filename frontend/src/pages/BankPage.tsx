import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ChartCard } from "../components/ChartCard";
import { DataTable } from "../components/DataTable";
import { MetricCard } from "../components/MetricCard";
import type { GeneratedProject } from "../types";
import { formatPercent, formatRub, toNumber } from "../utils/format";

interface BankPageProps {
  project: GeneratedProject | null;
}

const TONE_BY_LEVEL: Record<string, "green" | "yellow" | "red" | "blue"> = {
  ok: "green",
  warning: "yellow",
  critical: "red"
};

export function BankPage({ project }: BankPageProps) {
  if (!project) {
    return (
      <section className="empty-state">
        <p>Создайте новый расчёт, чтобы увидеть оценку банковского финансирования.</p>
      </section>
    );
  }

  const bank = project.bank_approval ?? {};
  const escrow = project.escrow_financing ?? {};
  const tone = TONE_BY_LEVEL[String(bank.verdict_level ?? "")] ?? "blue";
  const criteria = (bank.criteria ?? []) as Array<Record<string, unknown>>;
  const recommendations = (bank.recommendations ?? []) as string[];
  const schedule = (escrow.schedule ?? []) as Array<Record<string, unknown>>;
  const chartData = schedule.map((row) => ({
    month: row.month,
    debt: toNumber(row.debt_balance),
    escrow: toNumber(row.escrow_balance)
  }));

  return (
    <div className="page-stack">
      {bank.verdict ? (
        <section className={`verdict-banner tone-${tone}`}>
          <span className="verdict-title">Банковское проектное финансирование · эскроу 214-ФЗ</span>
          <p>{String(bank.verdict)}</p>
          <small>
            Критериев пройдено: {String(bank.passed_count ?? "—")} из {criteria.length} · стресс-тесты: цена −10%,
            себестоимость +10%
          </small>
        </section>
      ) : null}

      <section className="metric-grid">
        <MetricCard
          title="Собственное участие"
          value={formatPercent(escrow.equity_share)}
          subtitle={`${formatRub(escrow.equity_pool)} из бюджета`}
        />
        <MetricCard
          title="LLCR"
          value={escrow.llcr != null ? String(escrow.llcr) : "нет долга"}
          tone={escrow.llcr != null && toNumber(escrow.llcr) < 1.25 ? "red" : "green"}
        />
        <MetricCard
          title="Покрытие эскроу на вводе"
          value={escrow.escrow_coverage_at_delivery != null ? formatPercent(escrow.escrow_coverage_at_delivery) : "нет долга"}
          tone={
            escrow.escrow_coverage_at_delivery != null && toNumber(escrow.escrow_coverage_at_delivery) < 1
              ? "yellow"
              : "green"
          }
        />
        <MetricCard title="Пиковый долг" value={formatRub(escrow.max_debt)} subtitle={`месяц ${String(escrow.max_debt_month ?? "—")}`} />
        <MetricCard title="Проценты (эскроу-модель)" value={formatRub(escrow.total_interest)} subtitle="капитализируются в долг" />
        <MetricCard
          title="Прибыль (эскроу-модель)"
          value={formatRub(escrow.profit)}
          subtitle={`маржа ${formatPercent(escrow.margin)}`}
          tone={toNumber(escrow.profit) <= 0 ? "red" : "green"}
        />
      </section>

      <ChartCard title="Долг и эскроу по месяцам" subtitle="Раскрытие эскроу на вводе гасит долг">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="month" />
            <YAxis tickFormatter={(value) => `${Math.round(Number(value) / 1_000_000)} млн`} />
            <Tooltip formatter={(value) => formatRub(value)} />
            <Legend />
            <Line type="monotone" dataKey="debt" name="Долг" stroke="#a43d3d" strokeWidth={2} dot={false} />
            <Line type="monotone" dataKey="escrow" name="Эскроу" stroke="#2f6f6d" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard title="Критерии банка" subtitle="Пороговые требования проектного финансирования">
        <DataTable
          rows={criteria}
          columns={["name", "threshold", "actual", "status", "comment"]}
          labels={{
            name: "Критерий",
            threshold: "Порог",
            actual: "Факт",
            status: "Статус",
            comment: "Комментарий"
          }}
        />
      </ChartCard>

      {recommendations.length ? (
        <ChartCard title="Что нужно исправить" subtitle="Рекомендации для прохождения банка">
          <div className="risk-list">
            {recommendations.map((item, index) => (
              <div className="risk-item" key={index}>
                <span className="risk-dot high" />
                <p>{item}</p>
              </div>
            ))}
          </div>
        </ChartCard>
      ) : null}

      <ChartCard title="График эскроу-финансирования" subtitle="Помесячный расчёт долга, эскроу и процентов">
        <DataTable
          rows={schedule}
          columns={[
            "month",
            "construction_cost",
            "equity_payment",
            "drawdown",
            "interest",
            "escrow_inflow",
            "escrow_balance",
            "escrow_release",
            "direct_receipts",
            "repayment",
            "debt_balance",
            "escrow_coverage"
          ]}
          labels={{
            month: "Месяц",
            construction_cost: "Затраты",
            equity_payment: "Из собственных",
            drawdown: "Выборка кредита",
            interest: "Проценты",
            escrow_inflow: "На эскроу",
            escrow_balance: "Остаток эскроу",
            escrow_release: "Раскрытие",
            direct_receipts: "Прямые поступления",
            repayment: "Погашение",
            debt_balance: "Долг",
            escrow_coverage: "Покрытие"
          }}
        />
      </ChartCard>
    </div>
  );
}
