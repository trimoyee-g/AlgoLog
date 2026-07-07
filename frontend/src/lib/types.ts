export type Platform = "leetcode" | "codeforces" | "codechef" | "atcoder" | "gfg" | "other";

export const PLATFORMS: Platform[] = [
  "leetcode",
  "codeforces",
  "codechef",
  "atcoder",
  "gfg",
  "other",
];

export const PLATFORM_LABELS: Record<Platform, string> = {
  leetcode: "LeetCode",
  codeforces: "Codeforces",
  codechef: "CodeChef",
  atcoder: "AtCoder",
  gfg: "GFG",
  other: "Other",
};

export interface Attempt {
  id: number;
  rating: number;
  solved_self: boolean;
  time_taken_minutes: number | null;
  notes: string | null;
  created_at: string;
}

export interface Problem {
  id: number;
  url: string;
  title: string;
  platform: Platform;
  official_difficulty: string | null;
  tags: string | null;
  created_at: string;
  attempts: Attempt[];
}

export interface SimilarProblem {
  id: number;
  url: string;
  title: string;
  platform: Platform;
  tags: string | null;
  latest_rating: number | null;
  latest_solved_self: boolean | null;
  similarity: number;
}

export interface Overview {
  total_problems: number;
  total_attempts: number;
  solved_self_count: number;
  hard_rated_count: number;
}

export interface AttemptCreate {
  url: string;
  title: string;
  platform: Platform;
  official_difficulty?: string | null;
  tags?: string | null;
  description_snippet?: string | null;
  rating: number;
  solved_self: boolean;
  time_taken_minutes?: number | null;
  notes?: string | null;
}

export interface ProblemUpdate {
  url?: string;
  title?: string;
  platform?: Platform;
  tags?: string | null;
  rating?: number;
  solved_self?: boolean;
}

export interface ProblemFilters {
  min_rating?: number;
  solved_self?: boolean;
  platform?: Platform;
  tag?: string;
}

/** Derived, computed client-side from the problems list - not stored anywhere. */
export function latestAttempt(p: Problem): Attempt | null {
  if (!p.attempts.length) return null;
  return p.attempts.reduce((a, b) =>
    new Date(a.created_at) > new Date(b.created_at) ? a : b
  );
}
