import type { ReactNode } from "react";
import type { NavigationItem, PageKey } from "../types";

interface LayoutProps {
  activePage: PageKey;
  onNavigate: (page: PageKey) => void;
  children: ReactNode;
  projectName?: string;
  userName?: string;
  userRole?: string;
  onLogout: () => void;
}

const NAVIGATION: NavigationItem[] = [
  { key: "dashboard", label: "Главная" },
  { key: "new", label: "Новый расчёт" },
  { key: "budget", label: "Бюджет" },
  { key: "gpr", label: "ГПР" },
  { key: "sales", label: "Продажи" },
  { key: "credit", label: "Кредит и ДДС" },
  { key: "dscr", label: "DSCR" },
  { key: "scenarios", label: "Сценарии" },
  { key: "optimization", label: "Оптимизация" },
  { key: "improvement", label: "План улучшений" },
  { key: "history", label: "История проектов" }
];

export function Layout({ activePage, onNavigate, children, projectName, userName, userRole, onLogout }: LayoutProps) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">CB</span>
          <div>
            <strong>Construction Budget Agent</strong>
            <small>v3 кабинет девелопера</small>
          </div>
        </div>

        <nav className="nav-list" aria-label="Основная навигация">
          {NAVIGATION.map((item) => (
            <button
              key={item.key}
              className={item.key === activePage ? "nav-item active" : "nav-item"}
              type="button"
              onClick={() => onNavigate(item.key)}
            >
              {item.label}
            </button>
          ))}
        </nav>

        <div className="sidebar-note">
          <span>Текущий проект</span>
          <strong>{projectName || "Расчёт ещё не создан"}</strong>
        </div>

        <div className="user-box">
          <span>Пользователь</span>
          <strong>{userName || "неизвестно"}</strong>
          <small>Роль: {userRole || "user"}</small>
          <button className="logout-button" type="button" onClick={onLogout}>
            Выйти
          </button>
        </div>
      </aside>

      <main className="content">
        <div className="topbar">
          <div>
            <p className="eyebrow">ИИ-агент девелоперской модели</p>
            <h1>Бюджет, ГПР, продажи, кредит, ДДС и оптимизация</h1>
          </div>
          <div className="status-pill">Backend: http://localhost:8000</div>
        </div>
        {children}
      </main>
    </div>
  );
}
