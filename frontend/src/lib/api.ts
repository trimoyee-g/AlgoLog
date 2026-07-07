import type {
  AttemptCreate,
  Overview,
  Problem,
  ProblemFilters,
  ProblemUpdate,
  SimilarProblem,
} from "./types";
import { supabase } from "./supabase";

const BASE_URL = import.meta.env.VITE_BACKEND_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const { headers, ...rest } = options;
  // Every endpoint is now per-user, so always attach the Supabase JWT.
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const resp = await fetch(`${BASE_URL}${path}`, {
    ...rest,
    headers: {
      ...(rest.body ? { "Content-Type": "application/json" } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...headers,
    },
  });

  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body = await resp.json();
      detail = body.detail || detail;
    } catch {
      // response wasn't JSON - keep statusText
    }
    throw new ApiError(resp.status, detail);
  }

  if (resp.status === 204) return undefined as T;
  return resp.json();
}

export function getOverview() {
  return request<Overview>("/api/stats/overview");
}

export function listProblems(filters: ProblemFilters = {}) {
  const params = new URLSearchParams();
  if (filters.min_rating) params.set("min_rating", String(filters.min_rating));
  if (filters.solved_self !== undefined)
    params.set("solved_self", String(filters.solved_self));
  if (filters.platform) params.set("platform", filters.platform);
  if (filters.tag) params.set("tag", filters.tag);
  const qs = params.toString();
  return request<Problem[]>(`/api/problems${qs ? `?${qs}` : ""}`);
}

export function addAttempt(payload: AttemptCreate) {
  return request<{ problem_id: number; attempt_id: number }>("/api/attempts", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function updateProblem(id: number, payload: ProblemUpdate) {
  return request<Problem>(`/api/problems/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function deleteProblem(id: number) {
  return request<void>(`/api/problems/${id}`, {
    method: "DELETE",
  });
}

export function getSimilar(problemId: number, limit = 5) {
  return request<SimilarProblem[]>(
    `/api/problems/${problemId}/similar?limit=${limit}`
  );
}

export function sendDigestNow() {
  return request<{ narrative?: string }>("/api/stats/digest/send-now", {
    method: "POST",
  });
}
