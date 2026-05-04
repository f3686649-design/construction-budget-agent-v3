export function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const parsed = Number(value.replace(/\s/g, "").replace(",", "."));
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

export function formatNumber(value: unknown, digits = 0): string {
  return toNumber(value).toLocaleString("ru-RU", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits
  });
}

export function formatRub(value: unknown): string {
  return `${formatNumber(value)} ₽`;
}

export function formatPercent(value: unknown): string {
  return `${formatNumber(toNumber(value) * 100, 1)}%`;
}

export function formatArea(value: unknown): string {
  return `${formatNumber(value)} м²`;
}

export function statusByMargin(margin: unknown): "green" | "yellow" | "red" {
  const value = toNumber(margin);
  if (value > 0.15) {
    return "green";
  }
  if (value >= 0.08) {
    return "yellow";
  }
  return "red";
}

export function statusByDscr(dscr: unknown): "green" | "yellow" | "red" {
  const value = toNumber(dscr);
  if (!value || value < 1.2) {
    return "red";
  }
  if (value < 1.4) {
    return "yellow";
  }
  return "green";
}
