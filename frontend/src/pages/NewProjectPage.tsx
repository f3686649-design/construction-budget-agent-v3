import { useState, type FormEvent, type ReactNode } from "react";
import type { ProjectInput } from "../types";

interface NewProjectPageProps {
  onGenerate: (input: ProjectInput) => Promise<void>;
  loading: boolean;
  error: string | null;
}

const DEFAULT_INPUT: ProjectInput = {
  project_name: "Новый девелоперский проект",
  city: "Якутск",
  object_type: "Жилой дом",
  object_class: "комфорт",
  total_area: 10_795.3,
  sellable_area: 7_860.32,
  floors: 9,
  foundation_type: "сваи",
  foundation_optimization_mode: "оптимизированный",
  has_underground_part: false,
  sellable_finish_level: "черновая",
  external_networks_included: true,
  gas_only_cooking: true,
  construction_months: 18,
  sales_months: 24,
  credit_share: 0.7,
  credit_rate: 0.18
};

export function NewProjectPage({ onGenerate, loading, error }: NewProjectPageProps) {
  const [form, setForm] = useState<ProjectInput>(DEFAULT_INPUT);

  const setValue = (name: keyof ProjectInput, value: string | number | boolean | undefined) => {
    setForm((current) => ({ ...current, [name]: value }));
  };

  const numberValue = (name: keyof ProjectInput, value: string) => {
    setValue(name, value === "" ? undefined : Number(value));
  };

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await onGenerate(form);
  };

  return (
    <form className="page-stack" onSubmit={submit}>
      <section className="form-hero">
        <div>
          <p className="eyebrow">Новый расчёт</p>
          <h2>Сформировать финансовую модель проекта</h2>
          <p>Заполните ключевые параметры. Поля ручных корректировок можно оставить пустыми: агент применит нормативы и допущения MVP.</p>
        </div>
        <button className="primary-button" type="submit" disabled={loading}>
          {loading ? "Расчёт выполняется..." : "Сформировать финансовую модель"}
        </button>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <FormSection title="1. Основные параметры">
        <TextField label="Название проекта" value={form.project_name} onChange={(value) => setValue("project_name", value)} />
        <TextField label="Город" value={form.city} onChange={(value) => setValue("city", value)} />
        <SelectField label="Тип объекта" value={form.object_type} options={["Жилой дом", "Апартаменты", "Коммерция"]} onChange={(value) => setValue("object_type", value)} />
        <SelectField label="Класс объекта" value={form.object_class} options={["эконом", "комфорт", "бизнес", "премиум"]} onChange={(value) => setValue("object_class", value)} />
        <NumberField label="Площадь участка, м²" value={form.land_area} onChange={(value) => numberValue("land_area", value)} />
        <NumberField label="Стоимость земли, ₽" value={form.land_cost} onChange={(value) => numberValue("land_cost", value)} />
      </FormSection>

      <FormSection title="2. Площади и продукт">
        <NumberField label="Общая площадь, м²" value={form.total_area} onChange={(value) => numberValue("total_area", value)} required />
        <NumberField label="Продаваемая площадь, м²" value={form.sellable_area} onChange={(value) => numberValue("sellable_area", value)} required />
        <NumberField label="Этажность" value={form.floors} onChange={(value) => numberValue("floors", value)} required />
        <NumberField label="Количество квартир, необязательно" value={form.apartments_count} onChange={(value) => numberValue("apartments_count", value)} />
        <SelectField label="Уровень отделки реализуемых помещений" value={form.sellable_finish_level} options={["без отделки", "черновая", "white box", "чистовая"]} onChange={(value) => setValue("sellable_finish_level", value)} />
        <NumberField label="Цена продажи м², необязательно" value={form.sale_price_per_m2} onChange={(value) => numberValue("sale_price_per_m2", value)} />
      </FormSection>

      <FormSection title="3. Строительство">
        <SelectField label="Тип фундамента" value={form.foundation_type} options={["сваи", "плита", "лента", "подземная часть"]} onChange={(value) => setValue("foundation_type", value)} />
        <SelectField label="Режим расчёта свайного основания" value={form.foundation_optimization_mode} options={["оптимизированный", "нормативный"]} onChange={(value) => setValue("foundation_optimization_mode", value)} />
        <ToggleField label="Есть подземная часть?" checked={Boolean(form.has_underground_part)} onChange={(value) => setValue("has_underground_part", value)} />
        <ToggleField label="Наружные сети включены?" checked={Boolean(form.external_networks_included)} onChange={(value) => setValue("external_networks_included", value)} />
        <NumberField label="Плата за техприсоединение по ТУ, ₽ (необязательно)" value={form.tp_total_cost_override} onChange={(value) => numberValue("tp_total_cost_override", value)} />
        <ToggleField label="Газ только пищеприготовление?" checked={Boolean(form.gas_only_cooking)} onChange={(value) => setValue("gas_only_cooking", value)} />
        <NumberField label="Срок строительства, мес." value={form.construction_months} onChange={(value) => numberValue("construction_months", value)} />
        <NumberField label="Срок продаж, мес." value={form.sales_months} onChange={(value) => numberValue("sales_months", value)} />
      </FormSection>

      <FormSection title="4. Ручные корректировки бюджета">
        <NumberField label="Цена генподряда м²" value={form.gp_contract_price_per_m2} onChange={(value) => numberValue("gp_contract_price_per_m2", value)} />
        <NumberField label="Стоимость строительства м²" value={form.construction_cost_per_m2} onChange={(value) => numberValue("construction_cost_per_m2", value)} />
        <NumberField label="Проектирование, ₽" value={form.design_cost_override} onChange={(value) => numberValue("design_cost_override", value)} />
        <NumberField label="Подготовительные работы, ₽" value={form.preparation_cost_override} onChange={(value) => numberValue("preparation_cost_override", value)} />
        <NumberField label="Ставка надземных несущих конструкций, ₽/м²" value={form.above_ground_structures_rate_override} onChange={(value) => numberValue("above_ground_structures_rate_override", value)} />
        <NumberField label="Ставка ограждающих конструкций / стен / кровли, ₽/м²" value={form.envelope_roof_walls_rate_override} onChange={(value) => numberValue("envelope_roof_walls_rate_override", value)} />
        <NumberField label="Ставка отделки реализуемых помещений, ₽/м² NSA" value={form.sellable_finish_rate_override} onChange={(value) => numberValue("sellable_finish_rate_override", value)} />
      </FormSection>

      <FormSection title="5. Сваи">
        <NumberField label="Ставка свайного основания, ₽/м²" value={form.pile_foundation_rate_override} onChange={(value) => numberValue("pile_foundation_rate_override", value)} />
        <NumberField label="Сумма свайного основания, ₽" value={form.pile_foundation_cost_override} onChange={(value) => numberValue("pile_foundation_cost_override", value)} />
        <NumberField label="Количество свай" value={form.pile_count} onChange={(value) => numberValue("pile_count", value)} />
        <NumberField label="Стоимость одной сваи, ₽" value={form.pile_unit_cost} onChange={(value) => numberValue("pile_unit_cost", value)} />
        <NumberField label="Ростверк / оголовки, ₽/м²" value={form.grillage_rate_override} onChange={(value) => numberValue("grillage_rate_override", value)} />
      </FormSection>

      <FormSection title="6. Инженерия">
        <NumberField label="Сантехнические системы, ₽/м²" value={form.plumbing_rate_override} onChange={(value) => numberValue("plumbing_rate_override", value)} />
        <NumberField label="Отопление / ИТП, ₽/м²" value={form.heating_rate_override} onChange={(value) => numberValue("heating_rate_override", value)} />
        <NumberField label="Электроснабжение, ₽/м²" value={form.electrical_rate_override} onChange={(value) => numberValue("electrical_rate_override", value)} />
        <NumberField label="Слаботочные системы, ₽/м²" value={form.low_voltage_rate_override} onChange={(value) => numberValue("low_voltage_rate_override", value)} />
        <NumberField label="Вентиляция / дымоудаление, ₽/м²" value={form.ventilation_rate_override} onChange={(value) => numberValue("ventilation_rate_override", value)} />
      </FormSection>

      <FormSection title="7. Финансирование">
        <NumberField label="Доля кредита" value={form.credit_share} step="0.01" onChange={(value) => numberValue("credit_share", value)} />
        <NumberField label="Ставка кредита" value={form.credit_rate} step="0.01" onChange={(value) => numberValue("credit_rate", value)} />
      </FormSection>
    </form>
  );
}

function FormSection({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="form-section">
      <h3>{title}</h3>
      <div className="form-grid">{children}</div>
    </section>
  );
}

function TextField({ label, value, onChange }: { label: string; value?: string; onChange: (value: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <input value={value ?? ""} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function NumberField({
  label,
  value,
  onChange,
  required,
  step = "any"
}: {
  label: string;
  value?: number;
  onChange: (value: string) => void;
  required?: boolean;
  step?: string;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <input type="number" step={step} value={value ?? ""} required={required} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function SelectField({ label, value, options, onChange }: { label: string; value?: string; options: string[]; onChange: (value: string) => void }) {
  return (
    <label className="field">
      <span>{label}</span>
      <select value={value ?? options[0]} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option key={option} value={option}>
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}

function ToggleField({ label, checked, onChange }: { label: string; checked: boolean; onChange: (value: boolean) => void }) {
  return (
    <label className="toggle-field">
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <span>{label}</span>
    </label>
  );
}
