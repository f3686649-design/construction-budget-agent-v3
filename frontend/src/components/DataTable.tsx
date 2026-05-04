import type { AnyRecord } from "../types";

interface DataTableProps {
  rows?: AnyRecord[];
  columns?: string[];
  labels?: Record<string, string>;
  emptyText?: string;
  maxRows?: number;
}

const DEFAULT_LABELS: Record<string, string> = {
  month: "Месяц",
  amount: "Сумма",
  accumulated: "Накопительно",
  sold_area: "Проданная площадь",
  revenue: "Выручка",
  sales_receipts: "Поступления от продаж",
  construction_costs: "Затраты строительства",
  land_cost: "Земля",
  other_costs: "Прочие расходы",
  operating_cashflow_before_financing: "Операционный поток до финансирования",
  equity_required: "Собственные средства",
  cumulative_equity_required: "Собственные средства накопительно",
  credit_drawdown: "Выборка кредита",
  drawdown: "Выборка кредита",
  interest: "Проценты",
  repayment: "Погашение",
  closing_balance: "Остаток кредита",
  cash_balance_after_financing: "Денежный баланс после финансирования",
  dscr: "DSCR",
  debt_service: "Долговой сервис",
  scenario: "Сценарий",
  scenario_code: "Код сценария",
  total_budget: "Итоговый бюджет",
  profit_after_interest: "Прибыль после процентов",
  margin_after_interest: "Маржа после процентов",
  max_credit_balance: "Максимальный кредит",
  total_equity_required: "Собственные средства",
  minimum_dscr_after_sales_start: "Minimum DSCR",
  months_below_1_2: "Месяцев DSCR ниже 1.2"
};

function stringifyValue(value: unknown): string {
  if (value === null || value === undefined) {
    return "";
  }
  if (typeof value === "number") {
    return Number.isInteger(value)
      ? value.toLocaleString("ru-RU")
      : value.toLocaleString("ru-RU", { maximumFractionDigits: 2 });
  }
  if (typeof value === "boolean") {
    return value ? "Да" : "Нет";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

export function DataTable({ rows = [], columns, labels = {}, emptyText = "Нет данных для отображения.", maxRows }: DataTableProps) {
  const visibleRows = maxRows ? rows.slice(0, maxRows) : rows;
  const resolvedColumns = columns ?? Array.from(new Set(visibleRows.flatMap((row) => Object.keys(row))));

  if (!visibleRows.length) {
    return <div className="empty-state compact">{emptyText}</div>;
  }

  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            {resolvedColumns.map((column) => (
              <th key={column}>{labels[column] ?? DEFAULT_LABELS[column] ?? column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {visibleRows.map((row, index) => (
            <tr key={index}>
              {resolvedColumns.map((column) => (
                <td key={column}>{stringifyValue(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
