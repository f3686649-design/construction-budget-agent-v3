import { useState, type FormEvent } from "react";
import { resendVerification } from "../api/client";

interface LoginPageProps {
  onLogin: (login: string, password: string) => Promise<void>;
  onRegister: (login: string, email: string, password: string) => Promise<{ pending: boolean; email?: string }>;
  loading: boolean;
  error: string | null;
  backendStatus: string;
}

function urlNotice(): string | null {
  if (typeof window === "undefined") {
    return null;
  }
  const params = new URLSearchParams(window.location.search);
  if (params.get("verified") === "1") {
    return "Email подтверждён. Войдите в кабинет.";
  }
  if (params.get("verify") === "invalid") {
    return "Ссылка подтверждения недействительна или истекла. Запросите письмо повторно.";
  }
  return null;
}

export function LoginPage({ onLogin, onRegister, loading, error, backendStatus }: LoginPageProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [login, setLogin] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [localError, setLocalError] = useState<string | null>(null);
  const [pendingEmail, setPendingEmail] = useState<string | null>(null);
  const [resendMsg, setResendMsg] = useState<string | null>(null);
  const [notice] = useState<string | null>(urlNotice());

  const isRegister = mode === "register";

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setLocalError(null);
    if (isRegister) {
      if (password.length < 6) {
        setLocalError("Пароль должен быть не короче 6 символов.");
        return;
      }
      if (password !== confirm) {
        setLocalError("Пароли не совпадают.");
        return;
      }
      const result = await onRegister(login, email, password);
      if (result.pending) {
        setPendingEmail(result.email || email);
      }
    } else {
      await onLogin(login, password);
    }
  };

  const resend = async () => {
    setResendMsg(null);
    try {
      await resendVerification(login);
      setResendMsg("Письмо отправлено повторно. Проверьте почту, включая папку «Спам».");
    } catch {
      setResendMsg("Не удалось отправить письмо. Попробуйте позже.");
    }
  };

  if (pendingEmail) {
    return (
      <main className="login-page">
        <section className="login-card">
          <div>
            <p className="eyebrow">Construction Budget Agent v3</p>
            <h1>Подтвердите email</h1>
            <p className="muted">
              Мы отправили письмо со ссылкой на <b>{pendingEmail}</b>. Перейдите по ссылке, затем войдите.
              Если письма нет — проверьте папку «Спам».
            </p>
          </div>
          <button className="primary-button" type="button" onClick={resend}>
            Отправить письмо повторно
          </button>
          {resendMsg ? <div className="muted" style={{ marginTop: 10 }}>{resendMsg}</div> : null}
          <button
            type="button"
            onClick={() => {
              setPendingEmail(null);
              setMode("login");
            }}
            style={{ background: "none", border: "none", color: "#2f6df0", cursor: "pointer", marginTop: 14, fontSize: 14, padding: 0 }}
          >
            Вернуться ко входу
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div>
          <p className="eyebrow">Construction Budget Agent v3</p>
          <h1>{isRegister ? "Регистрация в кабинете" : "Вход в кабинет девелоперской модели"}</h1>
          <p className="muted">
            {isRegister
              ? "Создайте аккаунт — сразу доступен бесплатный тариф: 1 расчёт в месяц. Платный тариф подключается в разделе «Тариф»."
              : "Введите логин и пароль. Нет аккаунта — зарегистрируйтесь."}
          </p>
        </div>

        {notice ? (
          <div style={{ background: "#eaf1ff", color: "#1b3a6b", padding: "10px 14px", borderRadius: 10, marginBottom: 6 }}>{notice}</div>
        ) : null}

        <form className="login-form" onSubmit={submit}>
          <label className="field">
            <span>Логин</span>
            <input value={login} autoComplete="username" required onChange={(event) => setLogin(event.target.value)} />
          </label>

          {isRegister ? (
            <label className="field">
              <span>Email</span>
              <input type="email" value={email} autoComplete="email" required onChange={(event) => setEmail(event.target.value)} />
            </label>
          ) : null}

          <label className="field">
            <span>Пароль</span>
            <input
              type="password"
              value={password}
              autoComplete={isRegister ? "new-password" : "current-password"}
              required
              onChange={(event) => setPassword(event.target.value)}
            />
          </label>

          {isRegister ? (
            <label className="field">
              <span>Повторите пароль</span>
              <input
                type="password"
                value={confirm}
                autoComplete="new-password"
                required
                onChange={(event) => setConfirm(event.target.value)}
              />
            </label>
          ) : null}

          {error ? <div className="error-banner">{error}</div> : null}
          {localError ? <div className="error-banner">{localError}</div> : null}

          <button className="primary-button" type="submit" disabled={loading}>
            {loading ? "Подождите..." : isRegister ? "Зарегистрироваться" : "Войти"}
          </button>
        </form>

        <button
          type="button"
          onClick={() => {
            setMode(isRegister ? "login" : "register");
            setLocalError(null);
            setConfirm("");
          }}
          style={{ background: "none", border: "none", color: "#2f6df0", cursor: "pointer", marginTop: 12, fontSize: 14, padding: 0 }}
        >
          {isRegister ? "Уже есть аккаунт? Войти" : "Нет аккаунта? Зарегистрироваться"}
        </button>

        {isRegister ? (
          <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>
            Регистрируясь, вы принимаете{" "}
            <a href="/oferta.html" target="_blank" rel="noreferrer">
              публичную оферту
            </a>
            .
          </p>
        ) : null}

        <div className={`backend-status ${backendStatus.includes("недоступен") ? "bad" : "good"}`}>{backendStatus}</div>

        <footer
          className="login-public-foot"
          style={{ marginTop: 20, paddingTop: 16, borderTop: "1px solid #e2e8f4", textAlign: "center", fontSize: 13, color: "#5b6b88", lineHeight: 1.7 }}
        >
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
