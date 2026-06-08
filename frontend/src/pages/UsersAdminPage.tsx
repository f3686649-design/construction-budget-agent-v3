import { useEffect, useState, type FormEvent } from "react";
import { createUser, listUsers } from "../api/client";
import type { AdminUser } from "../types";

const PLAN_OPTIONS = [
  { code: "trial", name: "Триал (бесплатно)" },
  { code: "start", name: "Старт — 15 000 ₽/мес" },
  { code: "team", name: "Команда — 29 900 ₽/мес" },
  { code: "corporate", name: "Корпоративный" }
];

const cell: React.CSSProperties = { padding: "8px 10px", borderBottom: "1px solid #eef2f9" };
const head: React.CSSProperties = { textAlign: "left", padding: "8px 10px", borderBottom: "1px solid #e2e8f4", color: "#5b6b88", fontWeight: 600 };

export function UsersAdminPage() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);

  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("user");
  const [plan, setPlan] = useState("start");
  const [months, setMonths] = useState(1);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const refresh = async () => {
    setLoading(true);
    setListError(null);
    try {
      setUsers(await listUsers());
    } catch (error) {
      setListError(error instanceof Error ? error.message : "Не удалось загрузить пользователей.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void refresh();
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setFormError(null);
    setSuccess(null);
    try {
      const created = await createUser({ login, password, role, plan, months });
      setSuccess(`Пользователь «${created.login}» создан. Тариф: ${created.plan_name || created.plan}. Передайте логин и пароль клиенту.`);
      setLogin("");
      setPassword("");
      setRole("user");
      setPlan("start");
      setMonths(1);
      await refresh();
    } catch (error) {
      setFormError(error instanceof Error ? error.message : "Не удалось создать пользователя.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="users-admin">
      <section className="card" style={{ marginBottom: 20 }}>
        <h2 style={{ marginTop: 0 }}>Новый клиентский аккаунт</h2>
        <p className="muted">
          Создайте логин и пароль для клиента и сразу назначьте тариф. Пароль показывается только здесь — передайте его клиенту лично.
        </p>
        <form onSubmit={submit} style={{ display: "grid", gap: 14, maxWidth: 520 }}>
          <label className="field">
            <span>Логин</span>
            <input value={login} required onChange={(e) => setLogin(e.target.value)} placeholder="например, ivan.developer" />
          </label>
          <label className="field">
            <span>Пароль</span>
            <input value={password} required minLength={6} onChange={(e) => setPassword(e.target.value)} placeholder="не короче 6 символов" />
          </label>
          <label className="field">
            <span>Роль</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}>
              <option value="user">Клиент (user)</option>
              <option value="admin">Администратор (admin)</option>
            </select>
          </label>
          <label className="field">
            <span>Тариф</span>
            <select value={plan} onChange={(e) => setPlan(e.target.value)}>
              {PLAN_OPTIONS.map((p) => (
                <option key={p.code} value={p.code}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Срок, месяцев</span>
            <input
              type="number"
              min={1}
              value={months}
              onChange={(e) => setMonths(Math.max(1, Number(e.target.value) || 1))}
            />
          </label>
          {formError ? <div className="error-banner">{formError}</div> : null}
          {success ? (
            <div style={{ background: "#e7f6ec", color: "#1b7a3d", padding: "10px 14px", borderRadius: 10 }}>{success}</div>
          ) : null}
          <button className="primary-button" type="submit" disabled={submitting}>
            {submitting ? "Создаю..." : "Создать пользователя"}
          </button>
        </form>
      </section>

      <section className="card">
        <h2 style={{ marginTop: 0 }}>Пользователи</h2>
        {loading ? <p className="muted">Загрузка...</p> : null}
        {listError ? <div className="error-banner">{listError}</div> : null}
        {!loading && !listError ? (
          <div style={{ overflowX: "auto" }}>
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr>
                  <th style={head}>Логин</th>
                  <th style={head}>Роль</th>
                  <th style={head}>Тариф</th>
                  <th style={head}>Оплачен до</th>
                  <th style={head}>Активен</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.login}>
                    <td style={cell}>{u.login}</td>
                    <td style={cell}>{u.role}</td>
                    <td style={cell}>{u.plan_name || u.plan || "—"}</td>
                    <td style={cell}>{u.paid_until || "—"}</td>
                    <td style={cell}>{u.active ? "да" : "нет"}</td>
                  </tr>
                ))}
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ padding: "10px", color: "#5b6b88" }}>
                      Пока нет пользователей.
                    </td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>
        ) : null}
      </section>
    </div>
  );
}
