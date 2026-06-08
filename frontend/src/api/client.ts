import type { AuthSession, AuthUser, GeneratedProject, ProjectHistoryItem, ProjectInput, AiStatus, AiConclusion, AiChatMessage, AiChatResponse, BillingInfo, PaymentResult, AdminUser } from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "/api";
const AUTH_STORAGE_KEY = "construction_budget_agent_auth";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const session = getStoredAuth();
  const headers = new Headers(options?.headers);
  headers.set("Content-Type", "application/json");
  if (session?.access_token) {
    headers.set("Authorization", `Bearer ${session.access_token}`);
  }
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
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

export async function login(loginValue: string, password: string): Promise<AuthSession> {
  const session = await request<AuthSession>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ login: loginValue, password })
  });
  saveAuthSession(session);
  return session;
}

export async function register(loginValue: string, password: string): Promise<AuthSession> {
  const session = await request<AuthSession>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ login: loginValue, password })
  });
  saveAuthSession(session);
  return session;
}

export async function getMe(): Promise<AuthUser> {
  return request("/auth/me");
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

export async function getBilling(): Promise<BillingInfo> {
  return request<BillingInfo>("/billing");
}

export async function createPayment(plan: string, returnUrl?: string): Promise<PaymentResult> {
  return request<PaymentResult>("/billing/create-payment", {
    method: "POST",
    body: JSON.stringify({ plan, return_url: returnUrl })
  });
}

export async function listUsers(): Promise<AdminUser[]> {
  return request<AdminUser[]>("/admin/users");
}

export async function createUser(payload: {
  login: string;
  password: string;
  role: string;
  plan?: string;
  months?: number;
}): Promise<AdminUser> {
  return request<AdminUser>("/admin/users", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getAiStatus(): Promise<AiStatus> {
  return request<AiStatus>("/ai/status");
}

export async function getAiConclusion(projectId: string): Promise<AiConclusion> {
  return request<AiConclusion>(`/projects/${projectId}/ai-conclusion`);
}

export async function aiChat(
  projectId: string,
  question: string,
  history: AiChatMessage[]
): Promise<AiChatResponse> {
  return request<AiChatResponse>(`/projects/${projectId}/ai-chat`, {
    method: "POST",
    body: JSON.stringify({ question, history })
  });
}

export async function generateAiConclusion(projectId: string): Promise<AiConclusion> {
  return request<AiConclusion>(`/projects/${projectId}/ai-conclusion`, { method: "POST" });
}

export async function getProject(projectId: string): Promise<GeneratedProject> {
  return request(`/projects/${projectId}`);
}

export function buildDownloadUrl(path: string): string {
  if (path.startsWith("http")) {
    return path;
  }
  const baseUrl = API_BASE_URL.replace(/\/$/, "");
  if (path.startsWith("/api/") && baseUrl.endsWith("/api")) {
    return `${baseUrl}${path.slice(4)}`;
  }
  return `${baseUrl}${path.startsWith("/") ? path : `/${path}`}`;
}

export async function downloadExcel(path: string, filename: string): Promise<void> {
  const session = getStoredAuth();
  const headers: HeadersInit = session?.access_token ? { Authorization: `Bearer ${session.access_token}` } : {};
  const response = await fetch(buildDownloadUrl(path), { headers });
  if (!response.ok) {
    let message = "Не удалось скачать Excel-файл. Проверьте авторизацию и попробуйте ещё раз.";
    try {
      const payload = await response.json();
      if (typeof payload.detail === "string") {
        message = payload.detail;
      }
    } catch {
      message = "Не удалось скачать Excel-файл. Проверьте авторизацию и попробуйте ещё раз.";
    }
    throw new Error(message);
  }
  const blob = await response.blob();
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}

export function saveAuthSession(session: AuthSession): void {
  localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session));
}

export function getStoredAuth(): AuthSession | null {
  const raw = localStorage.getItem(AUTH_STORAGE_KEY);
  if (!raw) {
    return null;
  }
  try {
    return JSON.parse(raw) as AuthSession;
  } catch {
    localStorage.removeItem(AUTH_STORAGE_KEY);
    return null;
  }
}

export function clearAuthSession(): void {
  localStorage.removeItem(AUTH_STORAGE_KEY);
}
