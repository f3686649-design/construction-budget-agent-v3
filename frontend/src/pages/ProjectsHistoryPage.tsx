import { useEffect, useState } from "react";
import { getProject, getProjects } from "../api/client";
import { DataTable } from "../components/DataTable";
import type { GeneratedProject, ProjectHistoryItem } from "../types";
import { formatPercent, formatRub } from "../utils/format";

interface ProjectsHistoryPageProps {
  onLoadProject: (project: GeneratedProject) => void;
  onDownload: (path: string, filename: string) => Promise<void>;
}

export function ProjectsHistoryPage({ onLoadProject, onDownload }: ProjectsHistoryPageProps) {
  const [rows, setRows] = useState<ProjectHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getProjects()
      .then(setRows)
      .catch((requestError: Error) => setError(requestError.message))
      .finally(() => setLoading(false));
  }, []);

  const loadProject = async (projectId: string) => {
    setError(null);
    try {
      const project = await getProject(projectId);
      onLoadProject(project);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Не удалось открыть проект.");
    }
  };

  return (
    <div className="page-stack">
      <section className="form-hero">
        <div>
          <p className="eyebrow">История</p>
          <h2>История проектов</h2>
          <p>Список расчётов, сохранённых backend API в папке проектов.</p>
        </div>
        <button className="secondary-button" type="button" onClick={() => window.location.reload()}>
          Обновить список
        </button>
      </section>

      {loading ? <div className="empty-state compact">Загружаю историю проектов...</div> : null}
      {error ? <div className="error-banner">{error}</div> : null}

      <section className="panel">
        <div className="history-list">
          {rows.map((row) => (
            <article className="history-card" key={row.project_id}>
              <div>
                <span>{new Date(row.calculated_at).toLocaleString("ru-RU")}</span>
                <strong>{row.project_name || "Без названия"}</strong>
                <p>{row.city || "Город не указан"}</p>
              </div>
              <div className="history-metrics">
                <span>Бюджет: {formatRub(row.total_budget)}</span>
                <span>Выручка: {formatRub(row.revenue)}</span>
                <span>Прибыль: {formatRub(row.profit)}</span>
                <span>Маржа: {formatPercent(row.margin)}</span>
                <span>DSCR: {row.minimum_dscr ?? "нет данных"}</span>
              </div>
              <div className="history-actions">
                <button className="secondary-button" type="button" onClick={() => loadProject(row.project_id)}>
                  Открыть
                </button>
                {row.download_url && row.excel_filename ? (
                  <button className="primary-link" type="button" onClick={() => onDownload(row.download_url as string, row.excel_filename as string)}>
                    Скачать Excel
                  </button>
                ) : null}
              </div>
            </article>
          ))}
        </div>
        {!rows.length && !loading ? <DataTable rows={[]} emptyText="История проектов пока пуста." /> : null}
      </section>
    </div>
  );
}
