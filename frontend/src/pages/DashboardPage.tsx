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
  const land = project.land_valuation;
  const bank = project.bank_approval;
  const tech = project.tech_connection;
  const landToneByLevel: Record<string, "green" | "yellow" | "red" | "blue"> = {
    ok: "green",
    warning: "yellow",
    critical: "red",
    info: "blue"
  };
  const landTone = landToneByLevel[String(land?.verdict_level ?? "")] ?? "blue";
  const verdictCards: Array<{
    key: string;
    title: string;
    level: string;
    text: string;
    page?: PageKey;
  }> = [
    {
      key: "land",
      title: "Земля · остаточный метод",
      level: String(land?.verdict_level ?? ""),
      text: String(land?.verdict ?? "Нет данных.")
    },
    {
      key: "bank",
      title: "Банк · проектное финансирование",
      level: String(bank?.verdict_level ?? ""),
      text: String(bank?.verdict ?? "Нет данных."),
      page: "bank"
    },
    {
      key: "tech",
      title: "Техприсоединение · ТУ",
      level: String(tech?.verdict_level ?? ""),
      text: String(tech?.verdict ?? "Нет данных."),
      page: "tech"
    }
  ];
  const budgetByChapters = (project.detailed_budget.chapter_totals ?? []).map((row) => ({
    name: String(row["Глава"] ?? row["chapter"] ?? "Глава"),
    value: toNumber(row["Сумма"] ?? row["amount"])
  }));

  return (
    <div className="page-stack">
      <section className="verdicts-grid">
        {verdictCards.map((card) => (
          <article key={card.key} className={`verdict-card tone-${landToneByLevel[card.level] ?? "blue"}`}>
            <span className="verdict-title">{card.title}</span>
            <p>{card.text}</p>
            {card.page ? (
              <button className="verdict-link" type="button" onClick={() => onNavigate(card.page as PageKey)}>
                Подробнее →
              </button>
            ) : (
              <small>
                Макс. цена: {formatRub(land?.max_land_price)} · безубыточная: {formatRub(land?.break_even_land_price)}
              </small>
            )}
          </article>
        ))}
      </section>
      <section className="metric-grid">
        <MetricCard title="Итоговый бюджет" value={formatRub(summary.total_budget)} />
        <MetricCard title="СМР" value={formatRub(project.budget.cmr)} />
        <MetricCard title="Выручка" value={formatRub(summary.revenue)} tone="green" />
        <MetricCard title="Прибыль" value={formatRub(summary.profit)} tone={statusByMargin(summary.margin)} />
        <MetricCard title="Маржа" value={formatPercent(summary.margin)} tone={statusByMargin(summary.margin)} />
        <MetricCard title="Пик кредита" value={formatRub(summary.max_credit_balance)} />
        <MetricCard title="Собственные средства" value={formatRub(summary.total_equity_required)} tone="yellow" />
        <MetricCard title="Minimum DSCR" value={summary.minimum_dscr ? String(summary.minimum_dscr) : "нет данных"} tone={statusByDscr(summary.minimum_dscr)} />
        {land?.max_land_price !== undefined ? (
          <MetricCard
            title="Макс. цена земли"
            value={formatRub(land.max_land_price)}
            subtitle={land.safety_reserve != null ? `Запас ${formatPercent(land.safety_reserve)}` : "Целевая маржа 15%"}
            tone={landTone}
          />
        ) : null}
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
