export type FieldType = "text" | "url" | "secret" | "number" | "bool" | "select";

export interface FieldSpec {
  key: string;
  label: string;
  type: FieldType;
  required: boolean;
  default: unknown;
  help: string | null;
  placeholder: string | null;
  options: { value: string; label: string }[] | null;
}

export interface IntegrationType {
  kind: string;
  label: string;
  description: string;
  multiple: boolean;
  fields: FieldSpec[];
}

export interface TestResult {
  ok: boolean;
  message: string;
  details: { label: string; value: string }[];
}

export interface Integration {
  id: number;
  kind: string;
  name: string;
  enabled: boolean;
  config: Record<string, unknown>;
  secrets_set: Record<string, boolean>;
  last_test: (TestResult & { at: string }) | null;
}

export interface ServiceStatus {
  key: "home_assistant" | "grafana" | "mqtt" | "tailscale";
  label: string;
  state: "ok" | "error" | "unconfigured" | "unknown";
  message: string | null;
  checked_at: string | null;
}

export interface SetupState {
  admin_created: boolean;
  setup_complete: boolean;
  authenticated: boolean;
}

export interface IntegrationPayload {
  name: string;
  enabled: boolean;
  config: Record<string, unknown>;
  secrets: Record<string, string>;
}
