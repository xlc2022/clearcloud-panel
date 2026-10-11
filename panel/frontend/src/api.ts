import type { Integration, IntegrationPayload, IntegrationType, ServiceStatus, SetupState, TestResult } from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

let onUnauthorized: () => void = () => {};
export function setUnauthorizedHandler(fn: () => void) {
  onUnauthorized = fn;
}

async function request<T>(method: string, path: string, body?: unknown, opts: { skip401?: boolean } = {}): Promise<T> {
  const init: RequestInit = { method, credentials: "same-origin", headers: {} };
  if (body !== undefined || method !== "GET") {
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
    if (body !== undefined) init.body = JSON.stringify(body);
  }
  let res: Response;
  try {
    res = await fetch(path, init);
  } catch {
    throw new ApiError(0, "Cannot reach the panel backend.");
  }
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const j = await res.json();
      if (typeof j?.detail === "string") detail = j.detail;
      else if (Array.isArray(j?.detail) && j.detail[0]?.msg) detail = String(j.detail[0].msg);
    } catch {
      /* not JSON */
    }
    if (res.status === 401 && !opts.skip401) onUnauthorized();
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  setupState: () => request<SetupState>("GET", "/api/setup/state", undefined, { skip401: true }),
  createAdmin: (password: string) => request<void>("POST", "/api/setup/admin", { password }, { skip401: true }),
  completeSetup: () => request<void>("POST", "/api/setup/complete", {}),
  login: (password: string) => request<void>("POST", "/api/auth/login", { password }, { skip401: true }),
  logout: () => request<void>("POST", "/api/auth/logout", {}, { skip401: true }),
  types: () => request<IntegrationType[]>("GET", "/api/integration-types"),
  list: () => request<Integration[]>("GET", "/api/integrations"),
  create: (kind: string, p: IntegrationPayload) => request<Integration>("POST", "/api/integrations", { kind, ...p }),
  update: (id: number, p: IntegrationPayload) => request<Integration>("PUT", `/api/integrations/${id}`, p),
  remove: (id: number) => request<void>("DELETE", `/api/integrations/${id}`),
  testDraft: (kind: string, config: Record<string, unknown>, secrets: Record<string, string>, id?: number) =>
    request<TestResult>("POST", "/api/integrations/test", { kind, config, secrets, ...(id !== undefined ? { id } : {}) }),
  testStored: (id: number) => request<TestResult>("POST", `/api/integrations/${id}/test`, {}),
  status: () => request<{ services: ServiceStatus[] }>("GET", "/api/status"),
};
