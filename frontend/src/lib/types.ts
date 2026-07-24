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
  rating: number;
  solved_self: boolean;
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

/** `/api/stats/recommend` — the ranked pick, with the reason the backend already builds. */
export type Priority = "high" | "medium" | "low";

export interface Recommendation {
  problem_id: number;
  problem: string;
  url: string;
  tags: string | null;
  reason: string;
  priority: Priority;
  overdue_days: number;
  due: string;
}

export interface ReviewItem {
  id: number;
  url: string;
  title: string;
  platform: Platform;
  priority: Priority;
  tags: string | null;
  interval_days: number;
  ease: number;
  repetitions: number;
  last_review: string;
  due: string;
  overdue_days: number;
}

/**
 * Map an SM-2 recall quality (0-5) onto the (rating, solved_self) signal the
 * backend already stores, so a review is just another logged attempt.
 * All fails (q<3) reset scheduling to 1 day, so 0/1/2 collapse — losslessly,
 * since the scheduler treats them identically.
 */
export function reviewSignal(quality: number): { rating: number; solved_self: boolean } {
  if (quality < 3) return { rating: 4, solved_self: false }; // failed recall -> resurface soon
  if (quality === 3) return { rating: 5, solved_self: true }; // barely got it
  if (quality === 4) return { rating: 3, solved_self: true }; // solid, a little effort
  return { rating: 1, solved_self: true }; // perfect recall
}

/** Derived, computed client-side from the problems list - not stored anywhere. */
export function latestAttempt(p: Problem): Attempt | null {
  if (!p.attempts.length) return null;
  return p.attempts.reduce((a, b) =>
    new Date(a.created_at) > new Date(b.created_at) ? a : b
  );
}
