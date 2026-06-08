import { useState, type FormEvent } from "react";

interface LoginPageProps {
  onLogin: (login: string, password: string) => Promise<void>;
  loading: boolean;
  error: string | null;
  backendStatus: string;
}

export function LoginPage({ onLogin, loading, error, backendStatus }: LoginPageProps) {
  const [login, setLogin] = useState("");
  const [password, setPassword] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    await onLogin(login, password);
  };

  return (
    <main className="login-page">
      <section className="login-card">
        <div>
          <p className="eyebrow">Construction Budget Agent v3</p>
          <h1>Вход в кабинет девелоперской модели</h1>
          <p className="muted">Введите логин и пароль, выданные администратором. Без авторизации расчёты и история проектов недоступны.</p>
        </div>

        <form className="login-form" onSubmit={submit}>
          <label className="field">
            <span>Логин</span>
            <input value={login} autoComplete="username" required onChange={(event) => setLogin(event.target.value)} />
          </label>

          <label className="field">
            <span>Пароль</span>
            <input type="password" value={password} autoComplete="current-password" required onChange={(event) => setPassword(event.target.value)} />
          </label>

          {error ? <div className="error-banner">{error}</div> : null}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Выполняю вход..." : "Войти"}
          </button>
        </form>

        <div className={`backend-status ${backendStatus.includes("недоступен") ? "bad" : "good"}`}>{backendStatus}</div>

        <footer className="login-public-foot" style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid #e2e8f4", textAlign: "center", fontSize: 13, color: "#5b6b88", lineHeight: 1.7 }}>
          <div style={{ marginBottom: 6 }}>
            <a href="/tarify.html" style={{ color: "#2f6df0", margin: "0 8px" }}>Тарифы</a>
            <a href="/oferta.html" style={{ color: "#2f6df0", margin: "0 8px" }}>Оферта</a>
            <a href="/kontakty.html" style={{ color: "#2f6df0", margin: "0 8px" }}>Контакты и реквизиты</a>
          </div>
          <div>Онлайн-сервис финансового моделирования девелоперских проектов</div>
          <div>Самозанятый Захаров М. А. · ИНН 143528106506 · ikkkis@mail.ru</div>
        </footer>
      </section>
    </main>
  );
}
