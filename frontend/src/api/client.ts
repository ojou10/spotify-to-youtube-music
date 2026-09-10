import type { ApiErrorBody } from "./types";

export class ApiError extends Error {
  readonly code: string;
  constructor(public readonly response: ApiErrorBody["error"], public readonly status: number) {
    super(response.message);
    this.code = response.code;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`/api${path}`, { ...init, headers: { "Content-Type": "application/json", ...init.headers } });
  } catch {
    throw new Error("The local backend could not be reached.");
  }
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const error = (body as ApiErrorBody | null)?.error ?? { code: "request_failed", message: "The request failed.", action: null, field_errors: null };
    throw new ApiError(error, response.status);
  }
  return body as T;
}

export const api = {
  get: <T>(path: string, signal?: AbortSignal) => request<T>(path, { signal }),
  post: <T>(path: string, data: unknown) => request<T>(path, { method: "POST", body: JSON.stringify(data) }),
  put: <T>(path: string, data: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(data) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
