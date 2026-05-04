import type { GeneratedProject, ProjectHistoryItem, ProjectInput } from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    let message = "Не удалось выполнить запрос к серверу.";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      message = "Сервер вернул ошибку без описания.";
    }
    throw new Error(message);
  }

  return response.json() as Promise<T>;
}

export async function checkHealth(): Promise<{ status: string; app: string; version: string }> {
  return request("/health");
}

export async function generateModel(input: ProjectInput): Promise<GeneratedProject> {
  return request("/generate-model", {
    method: "POST",
    body: JSON.stringify(input)
  });
}

export async function getProjects(): Promise<ProjectHistoryItem[]> {
  return request("/projects");
}

export async function getProject(projectId: string): Promise<GeneratedProject> {
  return request(`/projects/${projectId}`);
}

export function buildDownloadUrl(path: string): string {
  if (path.startsWith("http")) {
    return path;
  }
  if (path.startsWith(API_BASE_URL)) {
    return path;
  }
  return `${API_BASE_URL}${path}`;
}
