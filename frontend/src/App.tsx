import { useEffect, useState } from "react";
import { buildDownloadUrl, checkHealth, generateModel } from "./api/client";
import { Layout } from "./components/Layout";
import { BudgetPage } from "./pages/BudgetPage";
import { CreditCashflowPage } from "./pages/CreditCashflowPage";
import { DashboardPage } from "./pages/DashboardPage";
import { DscrPage } from "./pages/DscrPage";
import { GprPage } from "./pages/GprPage";
import { ImprovementPlanPage } from "./pages/ImprovementPlanPage";
import { NewProjectPage } from "./pages/NewProjectPage";
import { OptimizationPage } from "./pages/OptimizationPage";
import { ProjectsHistoryPage } from "./pages/ProjectsHistoryPage";
import { SalesPage } from "./pages/SalesPage";
import { ScenariosPage } from "./pages/ScenariosPage";
import type { GeneratedProject, PageKey, ProjectInput } from "./types";

function App() {
  const [activePage, setActivePage] = useState<PageKey>("dashboard");
  const [project, setProject] = useState<GeneratedProject | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendStatus, setBackendStatus] = useState("проверяю соединение");

  useEffect(() => {
    checkHealth()
      .then(() => setBackendStatus("backend доступен"))
      .catch(() => setBackendStatus("backend недоступен"));
  }, []);

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

  return (
    <Layout activePage={activePage} onNavigate={setActivePage} projectName={project?.summary.project_name}>
      <div className={`backend-status ${backendStatus.includes("недоступен") ? "bad" : "good"}`}>{backendStatus}</div>
      {project ? (
        <div className="download-strip">
          <span>Excel-модель готова: {project.excel_filename}</span>
          <a className="primary-link" href={buildDownloadUrl(project.download_url)}>
            Скачать Excel
          </a>
        </div>
      ) : null}

      {activePage === "dashboard" && <DashboardPage project={project} onNavigate={setActivePage} />}
      {activePage === "new" && <NewProjectPage onGenerate={handleGenerate} loading={loading} error={error} />}
      {activePage === "budget" && <BudgetPage project={project} />}
      {activePage === "gpr" && <GprPage project={project} />}
      {activePage === "sales" && <SalesPage project={project} />}
      {activePage === "credit" && <CreditCashflowPage project={project} />}
      {activePage === "dscr" && <DscrPage project={project} />}
      {activePage === "scenarios" && <ScenariosPage project={project} />}
      {activePage === "optimization" && <OptimizationPage project={project} />}
      {activePage === "improvement" && <ImprovementPlanPage project={project} />}
      {activePage === "history" && (
        <ProjectsHistoryPage
          onLoadProject={(loadedProject) => {
            setProject(loadedProject);
            setActivePage("dashboard");
          }}
        />
      )}
    </Layout>
  );
}

export default App;
