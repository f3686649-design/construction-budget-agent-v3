import { useEffect, useState } from "react";
import { createPayment, getBilling } from "../api/client";
import { ChartCard } from "../components/ChartCard";
import { MetricCard } from "../components/MetricCard";
import type { BillingInfo, BillingPlan } from "../types";

export function BillingPage() {
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [payingPlan, setPayingPlan] = useState<string | null>(null);
  const [manualInfo, setManualInfo] = useState<string | null>(null);

  const load = () => {
    getBilling()
      .then((data) => {
        setBilling(data);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : "Не удалось загрузить тариф."));
  };

  useEffect(() => {
    load();
  }, []);

  const handlePay = async (plan: BillingPlan) => {
    setPayingPlan(plan.code);
    setManualInfo(null);
    setError(null);
    try {
      const result = await createPayment(plan.code, window.location.href);
      if (result.status === "created" && result.confirmation_url) {
        window.location.href = String(result.confirmation_url);
      } else if (result.status === "manual") {
        setManualInfo(String(result.instructions ?? "Свяжитесь с администратором для выставления счёта."));
      } else {
        setError(String(result.error ?? "Не удалось создать платёж."));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать платёж.");
    } finally {
      setPayingPlan(null);
    }
  };

  if (!billing) {
    return (
      <section className="empty-state">
        <p>{error ?? "Загружаю информацию о тарифе…"}</p>
      </section>
    );
  }

  const remaining = billing.remaining ?? { generate: 0, ai: 0 };
  const usage = billing.usage ?? { generate: 0, ai: 0 };
  const planActive = billing.active;

  return (
    <div className="page-stack">
      <section className={`verdict-banner ${planActive ? "tone-green" : "tone-yellow"}`}>
        <span className="verdict-title">Тариф и оплата</span>
        <p>
          Текущий тариф: «{billing.plan_name}»
          {billing.paid_until ? ` · оплачен до ${billing.paid_until}` : ""}
          {!planActive ? " · срок оплаты истёк — действуют квоты триала" : ""}
        </p>
        <small>Месяц учёта: {billing.month} · квоты обновляются 1-го числа</small>
      </section>

      <section className="metric-grid">
        <MetricCard
          title="Расчёты модели"
          value={`${usage.generate} из ${billing.generate_quota}`}
          subtitle={`осталось ${remaining.generate}`}
          tone={remaining.generate > 0 ? "green" : "red"}
        />
        <MetricCard
          title="ИИ-вызовы (заключения и чат)"
          value={`${usage.ai} из ${billing.ai_quota}`}
          subtitle={`осталось ${remaining.ai}`}
          tone={remaining.ai > 0 ? "green" : "red"}
        />
      </section>

      {error ? <div className="error-banner">{error}</div> : null}
      {manualInfo ? (
        <section className="verdict-banner tone-blue">
          <span className="verdict-title">Оплата по счёту</span>
          <p>{manualInfo}</p>
        </section>
      ) : null}

      <ChartCard title="Тарифы" subtitle="Оплата помесячная; корпоративный тариф — по договору">
        <div className="plans-grid">
          {(billing.plans ?? []).map((plan) => (
            <article key={plan.code} className={`plan-card ${billing.plan === plan.code ? "current" : ""}`}>
              <h4>{plan.name}</h4>
              <strong>{plan.price_rub > 0 ? `${plan.price_rub.toLocaleString("ru-RU")} ₽/мес` : "Бесплатно"}</strong>
              <p>{plan.description}</p>
              <small>
                {plan.generate_quota.toLocaleString("ru-RU")} расчётов · {plan.ai_quota.toLocaleString("ru-RU")} ИИ-вызовов
              </small>
              {billing.plan === plan.code && planActive ? (
                <span className="plan-badge">Текущий тариф</span>
              ) : plan.purchasable ? (
                <button
                  className="primary-button"
                  type="button"
                  disabled={payingPlan !== null}
                  onClick={() => handlePay(plan)}
                >
                  {payingPlan === plan.code ? "Создаю платёж…" : "Оплатить"}
                </button>
              ) : plan.code === "corporate" ? (
                <span className="muted">По договору</span>
              ) : null}
            </article>
          ))}
        </div>
      </ChartCard>
    </div>
  );
}
