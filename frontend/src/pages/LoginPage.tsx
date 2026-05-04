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
      </section>
    </main>
  );
}
