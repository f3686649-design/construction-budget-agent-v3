import { useEffect, useState } from "react";
import { checkHealth, clearAuthSession, downloadExcel, generateModel, getMe, getStoredAuth, login } from "./api/client";
import { Layout } from "./components/Layout";
import { AiConclusionPage } from "./pages/AiConclusionPage";
import { BankPage } from "./pages/BankPage";
import { BillingPage } from "./pages/BillingPage";
import { BudgetPage } from "./pages/BudgetPage";
import { CreditCashflowPage } from "./pages/CreditCashflowPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DscrPage } from "./pages/DscrPage";
import { GprPage } from "./pages/GprPage";
import { ImprovementPlanPage } from "./pages/ImprovementPlanPage";
import { LoginPage } from "./pages/LoginPage";
import { NewProjectPage } from "./pages/NewProjectPage";
import { OptimizationPage } from "./pages/OptimizationPage";
import { ProjectsHistoryPage } from "./pages/ProjectsHistoryPage";
import { SalesPage } from "./pages/SalesPage";
import { ScenariosPage } from "./pages/ScenariosPage";
import { TechConnectionPage } from "./pages/TechConnectionPage";
import type { AuthSession, GeneratedProject, PageKey, ProjectInput } from "./types";

function App() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [project, setProject] = useState<GeneratedProject | null>(null);
  const [loading, setLoading] = useState(false);
  const [authLoading, setAuthLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [auth, setAuth] = useState<AuthSession | null>(() => getStoredAuth());
  const [backendStatus, setBackendStatus] = useState("проверяю соединение");

  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus("backend доступен"))
      .catch(() => setBackendStatus("backend недоступен"));
  }, []);

  useEffect(() => {
    if (!auth) {
      return;
    }
    getMe()
      .then((user) => setAuth((current) => (current ? { ...current, user } : current)))
      .catch(() => {
        clearAuthSession();
        setAuth(null);
      });
  }, []);

  const handleLogin = async (loginValue: string, password: string) => {
    setAuthLoading(true);
    setAuthError(null);
    try {
      const session = await login(loginValue, password);
      setAuth(session);
    } catch (requestError) {
      setAuthError(requestError instanceof Error ? requestError.message : "Не удалось войти в кабинет.");
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    clearAuthSession();
    setAuth(null);
    setProject(null);
    setActivePage("dashboard");
  };

  const handleGenerate = async (input: ProjectInput) => {
    setLoading(true);
    setError(null);
    try {
      const result = await generateModel(input);
      setProject(result);
      setActivePage("dashboard");
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось сформировать финансовую модель.");
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = async () => {
    if (!project) {
      return;
    }
    try {
      await downloadExcel(project.download_url, project.excel_filename);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось скачать Excel-файл.");
    }
  };

  if (!auth) {
    return <LoginPage onLogin={handleLogin} loading={authLoading} error={authError} backendStatus={backendStatus} />;
  }

  return (
    <Layout
      activePage={activePage}
      onNavigate={setActivePage}
      navStatus={{
        bank: project?.bank_approval?.verdict_level as string | undefined,
        tech: project?.tech_connection?.verdict_level as string | undefined
      }}
      projectName={project?.summary.project_name}
      userName={auth.user.login}
      userRole={auth.user.role}
      onLogout={handleLogout}
    >
      <div className={`backend-status ${backendStatus.includes("недоступен") ? "bad" : "good"}`}>{backendStatus}</div>
      {project ? (
        <div className="download-strip">
          <span>Excel-модель готова: {project.excel_filename}</span>
          <button className="primary-link" type="button" onClick={handleDownload}>
            Скачать Excel
          </button>
        </div>
      ) : null}

      {activePage === "dashboard" && <DashboardPage project={project} onNavigate={setActivePage} />}
      {activePage === "new" && <NewProjectPage onGenerate={handleGenerate} loading={loading} error={error} />}
      {activePage === "budget" && <BudgetPage project={project} />}
      {activePage === "gpr" && <GprPage project={project} />}
      {activePage === "sales" && <SalesPage project={project} />}
      {activePage === "credit" && <CreditCashflowPage project={project} />}
      {activePage === "bank" && <BankPage project={project} />}
      {activePage === "tech" && <TechConnectionPage project={project} />}
      {activePage === "ai" && <AiConclusionPage project={project} />}
      {activePage === "dscr" && <DscrPage project={project} />}
      {activePage === "scenarios" && <ScenariosPage project={project} />}
      {activePage === "optimization" && <OptimizationPage project={project} />}
      {activePage === "improvement" && <ImprovementPlanPage project={project} />}
      {activePage === "billing" && <BillingPage />}
      {activePage === "history" && (
        <ProjectsHistoryPage
          onLoadProject={(loadedProject) => {
            setProject(loadedProject);
            setActivePage("dashboard");
          }}
          onDownload={downloadExcel}
        />
      )}
    </Layout>
  );
}

export default App;
